"""
Gemini Multi-Agent Resume Service - Streamable pipeline for home page.
Uses analysis engine under the hood for the actual analysis.
Only provides streaming capability for UI feedback.
"""

import json
import re
from src.config.settings import GEMINI_API_KEY, PARSER_MODEL, CRITIC_MODEL, EDITOR_MODEL
# from src.services.agent_service import GeminiAgentService
from src.services.agent_service import GeminiAgentService
from src.analysis.analysis_prompts import (
    PARSER_PARSE_RESUME_PROMPT,
    PARSER_PARSE_JOB_DESCRIPTION_PROMPT,
    CRITIC_AUDIT_ORIGINAL_PROMPT,
    EDITOR_REWRITE_PROMPT,
    CRITIC_AUDIT_EDITED_PROMPT
)


class MultiAgentResumeService:
    """
    Streamable multi-agent pipeline for home page visualization.
    Provides real-time feedback on the agent workflow.
    """
    
    def __init__(self):
        self.agent_service = GeminiAgentService(
            api_key=GEMINI_API_KEY,
            parser_model=PARSER_MODEL,
            critic_model=CRITIC_MODEL,
            editor_model=EDITOR_MODEL
        )
    
    def stream_pipeline(self, raw_resume_text: str, job_description: str = ""):
        """
        Execute multi-agent pipeline and stream results.
        Yields text chunks for real-time UI updates.
        
        Pipeline:
        1. Parser: Structure resume
        2. Critic: Audit original
        3. Editor: Rewrite with improvements
        4. Critic: Audit improvements
        """
        
        yield_text = []
        
        try:
            # ================================================================
            # PHASE 1: PARSER - Structure resume and job description
            # ================================================================
            yield_text.append("🔍 **Phase 1: Parsing Resume**\n")
            yield_text.append("Structuring your resume into sections...\n\n")
            
            parser_prompt = PARSER_PARSE_RESUME_PROMPT.format(
                resume_text=raw_resume_text
            )
            parser_response = self.agent_service.parser_parse(parser_prompt)
            parsed_resume = self._safe_parse_json(parser_response.text)
            
            yield_text.append("✅ Resume parsed successfully\n")
            yield_text.append(f"Sections found: {', '.join(k for k in parsed_resume.keys() if k != 'missing_sections')}\n\n")
            
            # Parse job description if provided
            parsed_jd = {}
            if job_description:
                yield_text.append("🔍 **Analyzing Job Description**\n")
                jd_prompt = PARSER_PARSE_JOB_DESCRIPTION_PROMPT.format(
                    job_description=job_description
                )
                jd_response = self.agent_service.parser_parse(jd_prompt)
                parsed_jd = self._safe_parse_json(jd_response.text)
                yield_text.append("✅ Job description analyzed\n\n")
            
            # ================================================================
            # PHASE 2: CRITIC - Audit original resume
            # ================================================================
            yield_text.append("🧐 **Phase 2: Analyzing Quality**\n")
            yield_text.append("Running comprehensive quality audit...\n\n")
            
            critic_prompt = CRITIC_AUDIT_ORIGINAL_PROMPT.format(
                parsed_resume=json.dumps(parsed_resume, indent=2),
                job_description=job_description if job_description else "No job description provided"
            )
            critic_response = self.agent_service.critic_audit_original(critic_prompt)
            original_criticism = self._safe_parse_json(critic_response.text)
            
            if "scores" in original_criticism:
                scores = original_criticism["scores"]
                yield_text.append("📊 **Original Resume Scores:**\n")
                for metric, score in scores.items():
                    yield_text.append(f"  • {metric}: {score}/100\n")
                yield_text.append("\n")
            
            if "critical_issues" in original_criticism:
                issues = original_criticism["critical_issues"]
                if issues:
                    yield_text.append("⚠️ **Issues Found:**\n")
                    for issue in issues[:3]:
                        yield_text.append(f"  • {issue}\n")
                    yield_text.append("\n")
            
            # ================================================================
            # PHASE 3: EDITOR - Rewrite based on feedback
            # ================================================================
            yield_text.append("✏️ **Phase 3: Improving Resume**\n")
            yield_text.append("Rewriting with improvements...\n\n")
            
            editor_prompt = EDITOR_REWRITE_PROMPT.format(
                original_resume=json.dumps(parsed_resume, indent=2),
                critic_feedback=json.dumps(original_criticism, indent=2),
                weak_statements=json.dumps(
                    original_criticism.get("weak_statements", [])
                )
            )
            editor_response = self.agent_service.editor_rewrite(editor_prompt)
            edited_resume = self._safe_parse_json(editor_response.text)
            
            yield_text.append("✅ Resume improved\n\n")
            
            if "bullet_improvements" in edited_resume:
                improvements = edited_resume["bullet_improvements"]
                yield_text.append(f"📝 **{len(improvements)} Bullet Points Improved**\n\n")
            
            # ================================================================
            # PHASE 4: CRITIC - Verify improvements
            # ================================================================
            yield_text.append("🔄 **Phase 4: Verifying Improvements**\n")
            yield_text.append("Auditing changes...\n\n")
            
            final_critic_prompt = CRITIC_AUDIT_EDITED_PROMPT.format(
                original_resume=json.dumps(parsed_resume, indent=2),
                edited_resume=json.dumps(edited_resume, indent=2),
                improvements=json.dumps(
                    edited_resume.get("bullet_improvements", []),
                    indent=2
                )
            )
            final_critic_response = self.agent_service.critic_audit_edited(final_critic_prompt)
            final_scores = self._safe_parse_json(final_critic_response.text)
            
            if "scores" in final_scores:
                scores = final_scores["scores"]
                yield_text.append("📊 **Final Improved Scores:**\n")
                for metric, score in scores.items():
                    original_score = original_criticism.get("scores", {}).get(metric, 0)
                    improvement = score - original_score
                    improvement_sign = "+" if improvement > 0 else ""
                    yield_text.append(f"  • {metric}: {score}/100 ({improvement_sign}{improvement})\n")
                yield_text.append("\n")
            
            yield_text.append("✅ **Analysis Complete!**\n\n")
            yield_text.append("---\n")
            
            # Store agent responses for conversation history
            yield_text.append(f"```json\n{json.dumps(final_scores, indent=2)}\n```")
            
        except json.JSONDecodeError as e:
            yield_text.append(f"\n⚠️ JSON parsing error: {str(e)}\n")
        except Exception as e:
            yield_text.append(f"\n❌ Error in pipeline: {str(e)}\n")
        
        # Yield all accumulated text as one response
        full_text = "".join(yield_text)
        
        # Create a simple generator that yields the complete text
        class TextStream:
            def __init__(self, text):
                self.text = text
            
            def __iter__(self):
                yield self
        
        return TextStream(full_text)
    
    @staticmethod
    def _safe_parse_json(text: str) -> dict:
        """Safely parse JSON from response, handling markdown and formatting."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # Try to extract raw JSON object
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            
            # Return empty dict if parsing fails
            return {}
