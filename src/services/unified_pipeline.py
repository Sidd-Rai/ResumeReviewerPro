"""
Unified Analysis Pipeline - Single execution of 4-call pipeline.
Returns both structured data and raw responses for reuse by multiple consumers.
Validates inputs upfront, deduplicates parsing, tracks metrics.
"""

import json
import re
from typing import Dict, Any, Tuple, Optional
from src.config.settings import (
    GEMINI_API_KEY,
    PARSER_MODEL,
    CRITIC_MODEL,
    EDITOR_MODEL,
    MIN_JOB_DESCRIPTION_LENGTH,
    MIN_JOB_DESCRIPTION_WORDS,
)
from src.services.agent_service import GeminiAgentService
from src.analysis.analysis_prompts import (
    PARSER_PARSE_RESUME_PROMPT,
    PARSER_PARSE_JOB_DESCRIPTION_PROMPT,
    CRITIC_AUDIT_ORIGINAL_PROMPT,
    EDITOR_REWRITE_PROMPT,
    CRITIC_AUDIT_EDITED_PROMPT,
)


class UnifiedAnalysisPipeline:
    """Single execution pipeline for resume analysis with metrics tracking."""
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing or unconfigured.")
        self.agent_service = GeminiAgentService(
            api_key=GEMINI_API_KEY,
            parser_model=PARSER_MODEL,
            critic_model=CRITIC_MODEL,
            editor_model=EDITOR_MODEL
        )
        self.metrics = {
            "cache_hits": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_tokens": 0,
        }
    
    @staticmethod
    def _validate_job_description(job_description: str) -> Tuple[bool, str, float]:
        """Validate job description upfront."""
        if not job_description or len(job_description.strip()) < MIN_JOB_DESCRIPTION_LENGTH:
            return False, "Job description too short", 0.0
        
        word_count = len(job_description.split())
        if word_count < MIN_JOB_DESCRIPTION_WORDS:
            return False, "Insufficient content (minimum 10 words required)", 0.0
        
        nonsense_patterns = [
            r"you are rejected", r"no job", r"bruh", r"lol", r"haha",
            r"test", r"dummy", r"fake", r"xxx+", r"zzz+",
        ]
        
        text_lower = job_description.lower()
        nonsense_score = sum(1 for pattern in nonsense_patterns if re.search(pattern, text_lower))
        
        if nonsense_score >= 2:
            return False, "Job description appears to be nonsense/test content", 0.1
        
        job_keywords = [
            "experience", "skills", "responsibilities", "required", "qualifications",
            "role", "position", "team", "project", "develop", "manage", "lead",
            "deadline", "collaborate", "analysis", "technical", "software", "data"
        ]
        
        keyword_matches = sum(1 for kw in job_keywords if kw in text_lower)
        
        if keyword_matches < 2:
            return False, "No recognizable job content", 0.2
        
        quality_score = min(100.0, 20 + (word_count / 10) + (keyword_matches * 10))
        return True, "Valid job description", quality_score
    
    @staticmethod
    def _parse_json(text: str) -> dict:
        """Unified JSON parsing with markdown and raw object extraction."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {}
    
    def _track_metrics(self, response):
        """Track token usage and cache hits."""
        if hasattr(response, 'input_tokens') and response.input_tokens:
            self.metrics["total_input_tokens"] += response.input_tokens
        if hasattr(response, 'output_tokens') and response.output_tokens:
            self.metrics["total_output_tokens"] += response.output_tokens
        if hasattr(response, 'cache_hit') and response.cache_hit:
            self.metrics["cache_hits"] += 1
        if hasattr(response, 'cache_creation_tokens') and response.cache_creation_tokens:
            self.metrics["total_cache_tokens"] += response.cache_creation_tokens
    
    def execute(
        self,
        resume_text: str,
        job_description: str = "",
        job_title: str = "Target Role"
    ) -> Dict[str, Any]:
        """
        Execute unified 4-call pipeline.
        Returns structured data with raw responses for reuse.
        """
        
        # Validate JD upfront
        jd_is_valid = True
        jd_validation_reason = "No job description provided"
        jd_quality_score = 100.0
        
        if job_description:
            jd_is_valid, jd_validation_reason, jd_quality_score = self._validate_job_description(job_description)
        
        # Call 1: Parse resume and JD
        parser_prompt = PARSER_PARSE_RESUME_PROMPT.format(resume_text=resume_text)
        parser_response = self.agent_service.parser_parse(parser_prompt)
        parsed_resume = self._parse_json(parser_response.text)
        self._track_metrics(parser_response)
        
        parsed_jd = {}
        if job_description:
            jd_prompt = PARSER_PARSE_JOB_DESCRIPTION_PROMPT.format(job_description=job_description)
            jd_response = self.agent_service.parser_parse(jd_prompt)
            parsed_jd = self._parse_json(jd_response.text)
            self._track_metrics(jd_response)
        
        # Call 2: Critic audit original
        critic_prompt = CRITIC_AUDIT_ORIGINAL_PROMPT.format(
            parsed_resume=json.dumps(parsed_resume, indent=2),
            job_description=job_description if job_description else "No job description provided"
        )
        critic_response = self.agent_service.critic_audit_original(critic_prompt)
        original_analysis = self._parse_json(critic_response.text)
        self._track_metrics(critic_response)
        
        # Call 3: Editor rewrite
        editor_prompt = EDITOR_REWRITE_PROMPT.format(
            original_resume=json.dumps(parsed_resume, indent=2),
            critic_feedback=json.dumps(original_analysis, indent=2),
            weak_statements=json.dumps(original_analysis.get("weak_statements", []))
        )
        editor_response = self.agent_service.editor_rewrite(editor_prompt)
        edited_resume = self._parse_json(editor_response.text)
        self._track_metrics(editor_response)
        
        # Call 4: Critic audit edited
        final_prompt = CRITIC_AUDIT_EDITED_PROMPT.format(
            original_resume=json.dumps(parsed_resume, indent=2),
            edited_resume=json.dumps(edited_resume, indent=2),
            improvements=json.dumps(edited_resume.get("bullet_improvements", []), indent=2)
        )
        final_response = self.agent_service.critic_audit_edited(final_prompt)
        final_analysis = self._parse_json(final_response.text)
        self._track_metrics(final_response)
        
        return {
            "parsed_resume": parsed_resume,
            "parsed_jd": parsed_jd,
            "original_analysis": original_analysis,
            "edited_resume": edited_resume,
            "final_analysis": final_analysis,
            "jd_validation": {
                "is_valid": jd_is_valid,
                "reason": jd_validation_reason,
                "quality_score": jd_quality_score,
            },
            "metrics": self.metrics,
            "raw_responses": {
                "parser": parser_response,
                "critic_original": critic_response,
                "editor": editor_response,
                "critic_edited": final_response,
            }
        }
