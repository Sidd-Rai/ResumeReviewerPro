"""
Analysis Engine - Clean 4-call pipeline for resume analysis.
Uses modular agent service (service-agnostic) with built-in prompt caching.
Consolidates all analysis into structured AnalysisResult.
"""

import json
import re
import streamlit as st
from typing import Tuple

from src.config.settings import (
    GEMINI_API_KEY,
    PARSER_MODEL,
    CRITIC_MODEL,
    EDITOR_MODEL,
    SCORE_WEIGHTS_NEW,
    RESUME_QUALITY_WEIGHTS,
    JD_VALIDITY_PENALTY,
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

from src.analysis.analysis_result import (
    KeywordExtraction,
    SectionCompleteness,
    ResumeContentAnalysis,
    ResumeVsJobMatch,
    KeywordMatch,
    BulletImprovement,
    RewriteSuggestions,
    ATSWarnings,
    FormattingIssue,
    ImpactAssessment,
    ComprehensiveFeedback,
    MatchFit,
    Scores,
    ScoreBreakdown,
    AnalysisResult,
)


class AnalysisEngine:
    """
    Modular resume analysis engine using 4-call pipeline with prompt caching:
    1. Parser: Resume + Job Description
    2. Critic: Original Resume Analysis
    3. Editor: Resume Improvements
    4. Critic: Edited Resume Verification
    
    Prompt caching is handled automatically by GeminiAgentService.
    """
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing or unconfigured.")
        
        self.agent_service = GeminiAgentService(
            api_key=GEMINI_API_KEY,
            parser_model=PARSER_MODEL,
            critic_model=CRITIC_MODEL,
            editor_model=EDITOR_MODEL
        )
    
    @staticmethod
    def _validate_job_description(job_description: str) -> Tuple[bool, str, float]:
        """
        Validates job description legitimacy.
        Returns: (is_valid, reason, quality_score)
        """
        if not job_description or len(job_description.strip()) < MIN_JOB_DESCRIPTION_LENGTH:
            return False, "Job description too short", 0.0
        
        word_count = len(job_description.split())
        if word_count < MIN_JOB_DESCRIPTION_WORDS:
            return False, "Insufficient content (minimum 10 words required)", 0.0
        
        # Check for obvious nonsense patterns
        nonsense_patterns = [
            r"you are rejected",
            r"no job",
            r"bruh",
            r"lol",
            r"haha",
            r"test",
            r"dummy",
            r"fake",
            r"xxx+",
            r"zzz+",
        ]
        
        text_lower = job_description.lower()
        nonsense_score = sum(1 for pattern in nonsense_patterns if re.search(pattern, text_lower))
        
        if nonsense_score >= 2:
            return False, "Job description appears to be nonsense/test content", 0.1
        
        # Check minimum professional content
        job_keywords = [
            "experience", "skills", "responsibilities", "required", "qualifications",
            "role", "position", "team", "project", "develop", "manage", "lead",
            "deadline", "collaborate", "analysis", "technical", "software", "data"
        ]
        
        keyword_matches = sum(1 for kw in job_keywords if kw in text_lower)
        
        if keyword_matches < 2:
            return False, "No recognizable job content (missing typical job description elements)", 0.2
        
        # Quality score based on length and content
        quality_score = min(100.0, 20 + (word_count / 10) + (keyword_matches * 10))
        
        return True, "Valid job description", quality_score
    
    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Safely parse JSON from response, handling markdown and trailing text."""
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
            
            raise ValueError(f"Could not parse JSON from response: {text[:200]}")
    
    def analyze_resume(
        self,
        resume_text: str,
        job_description: str = "",
        job_title: str = "Target Role"
    ) -> AnalysisResult:
        """
        Execute 4-call analysis pipeline with prompt caching.
        
        Call 1: Parser - Structure resume and job description
        Call 2: Critic - Analyze original resume
        Call 3: Editor - Generate improvements
        Call 4: Critic - Verify improvements
        
        Prompt caching saves tokens on system instructions across calls.
        """
        
        # ====================================================================
        # VALIDATION
        # ====================================================================
        jd_is_valid = True
        jd_quality_score = 100.0
        jd_validation_reason = "No job description provided"
        
        if job_description:
            jd_is_valid, jd_validation_reason, jd_quality_score = self._validate_job_description(job_description)
            if not jd_is_valid:
                st.warning(f"⚠️ Job Description Issue: {jd_validation_reason}")
        
        # ====================================================================
        # CALL 1: PARSER - Extract and structure resume + job description
        # ====================================================================
        status = st.status("📋 Phase 1/4: Parsing resume structure...", expanded=True)
        
        try:
            # Parse resume
            parser_prompt = PARSER_PARSE_RESUME_PROMPT.format(resume_text=resume_text)
            parser_response = self.agent_service.parser_parse(parser_prompt)
            parsed_resume = self._parse_json_response(parser_response.text)
            
            # Parse job description if provided
            parsed_jd = {}
            if job_description:
                jd_prompt = PARSER_PARSE_JOB_DESCRIPTION_PROMPT.format(
                    job_description=job_description
                )
                jd_response = self.agent_service.parser_parse(jd_prompt)
                parsed_jd = self._parse_json_response(jd_response.text)
            
            status.update(label="✅ Phase 1: Parsing complete", state="complete")
        except Exception as e:
            status.update(label="❌ Phase 1: Parsing failed", state="error")
            raise ValueError(f"Parser error: {str(e)}")
        
        # ====================================================================
        # CALL 2: CRITIC - Audit original resume
        # ====================================================================
        status = st.status("🧐 Phase 2/4: Analyzing resume quality...", expanded=True)
        
        try:
            critic_prompt = CRITIC_AUDIT_ORIGINAL_PROMPT.format(
                parsed_resume=json.dumps(parsed_resume, indent=2),
                job_description=job_description if job_description else "No job description provided"
            )
            critic_response = self.agent_service.critic_audit_original(critic_prompt)
            original_analysis = self._parse_json_response(critic_response.text)
            
            status.update(label="✅ Phase 2: Analysis complete", state="complete")
        except Exception as e:
            status.update(label="❌ Phase 2: Analysis failed", state="error")
            raise ValueError(f"Critic analysis error: {str(e)}")
        
        # ====================================================================
        # CALL 3: EDITOR - Generate improvements
        # ====================================================================
        status = st.status("✏️ Phase 3/4: Generating improvements...", expanded=True)
        
        try:
            editor_prompt = EDITOR_REWRITE_PROMPT.format(
                original_resume=json.dumps(parsed_resume, indent=2),
                critic_feedback=json.dumps(original_analysis, indent=2),
                weak_statements=json.dumps(original_analysis.get("weak_statements", []))
            )
            editor_response = self.agent_service.editor_rewrite(editor_prompt)
            edited_resume = self._parse_json_response(editor_response.text)
            
            status.update(label="✅ Phase 3: Improvements generated", state="complete")
        except Exception as e:
            status.update(label="❌ Phase 3: Generation failed", state="error")
            raise ValueError(f"Editor error: {str(e)}")
        
        # ====================================================================
        # CALL 4: CRITIC - Verify improvements
        # ====================================================================
        status = st.status("🔄 Phase 4/4: Verifying improvements...", expanded=True)
        
        try:
            final_prompt = CRITIC_AUDIT_EDITED_PROMPT.format(
                original_resume=json.dumps(parsed_resume, indent=2),
                edited_resume=json.dumps(edited_resume, indent=2),
                improvements=json.dumps(edited_resume.get("bullet_improvements", []), indent=2)
            )
            final_response = self.agent_service.critic_audit_edited(final_prompt)
            final_analysis = self._parse_json_response(final_response.text)
            
            status.update(label="✅ Phase 4: Verification complete", state="complete")
        except Exception as e:
            status.update(label="❌ Phase 4: Verification failed", state="error")
            raise ValueError(f"Final verification error: {str(e)}")
        
        # ====================================================================
        # BUILD ANALYSIS RESULT
        # ====================================================================
        status = st.status("🔨 Building final report...", expanded=True)
        
        try:
            # Section completeness
            section_completeness = SectionCompleteness(
                summary=bool(parsed_resume.get("summary")),
                experience=bool(parsed_resume.get("experience")),
                skills=bool(parsed_resume.get("skills")),
                education=bool(parsed_resume.get("education")),
                projects=bool(parsed_resume.get("projects"))
            )
            
            # Content analysis
            content_analysis = ResumeContentAnalysis(
                identified_skills=parsed_resume.get("skills", []),
                experience_strength="Evaluated by critic",
                achievement_density=original_analysis.get("scores", {}).get("impact", 0),
                keyword_richness=original_analysis.get("scores", {}).get("skills", 0),
                section_completeness=section_completeness,
                missing_sections=parsed_resume.get("missing_sections", []),
                action_verb_usage=original_analysis.get("scores", {}).get("style", 0)
            )
            
            # Resume vs Job Match
            resume_vs_job = ResumeVsJobMatch(
                skill_matches=KeywordMatch(
                    matched=parsed_jd.get("required_skills", [])[:5],
                    missing=parsed_jd.get("required_skills", [])[-3:] if len(parsed_jd.get("required_skills", [])) > 5 else []
                ),
                tool_matches=KeywordMatch(
                    matched=parsed_jd.get("tools_technologies", [])[:3],
                    missing=parsed_jd.get("tools_technologies", [])[3:] if len(parsed_jd.get("tools_technologies", [])) > 3 else []
                ),
                keyword_density=original_analysis.get("ats_safety_score", 50),
                ats_safety_score=original_analysis.get("ats_safety_score", 50),
                critical_missing_keywords=original_analysis.get("keyword_gaps", [])[:5],
                strength_areas=original_analysis.get("strengths", []),
                improvement_areas=original_analysis.get("weak_statements", [])[:3]
            )
            
            # Rewrite suggestions
            rewrite_suggestions = RewriteSuggestions(
                summary_rewrite=edited_resume.get("summary"),
                bullet_improvements=[
                    BulletImprovement(
                        original=imp.get("original", ""),
                        improved=imp.get("improved", ""),
                        section="Experience",
                        reasoning=imp.get("reason", "")
                    )
                    for imp in edited_resume.get("bullet_improvements", [])[:5]
                ],
                keywords_to_add=parsed_jd.get("required_skills", [])[:5],
                structure_improvements=[],
                quick_wins=[]
            )
            
            # ATS Warnings
            ats_warnings = ATSWarnings(
                formatting_issues=[],
                keyword_gaps=original_analysis.get("keyword_gaps", []),
                readability_score=8,
                ats_pass_probability=original_analysis.get("ats_safety_score", 50),
                critical_fixes=original_analysis.get("critical_issues", [])[:3],
                nice_to_haves=[]
            )
            
            # Impact Assessment
            impact_assessment = ImpactAssessment(
                impact_score=original_analysis.get("scores", {}).get("impact", 0),
                clarity_score=original_analysis.get("scores", {}).get("style", 0),
                professionalism_score=original_analysis.get("scores", {}).get("style", 0),
                quantification_level="medium",
                achievement_statements=original_analysis.get("strengths", []),
                weak_statements=original_analysis.get("weak_statements", [])[:3],
                recommendations=[],
                overall_impression=original_analysis.get("overall_impression", "Decent resume with areas for improvement")
            )
            
            # Calculate weighted scores
            original_scores = original_analysis.get("scores", {})
            final_scores = final_analysis.get("scores", {})
            
            ats_match = max(0, min(100, original_scores.get("impact", 50)))
            keyword_density = max(0, min(100, original_scores.get("skills", 50)))
            impact_quality = max(0, min(100, original_scores.get("impact", 50)))
            clarity = max(0, min(100, original_scores.get("style", 50)))
            structure = max(0, min(100, original_scores.get("brevity", 50)))
            
            overall = int(
                ats_match * SCORE_WEIGHTS_NEW["ats_score"] +
                keyword_density * SCORE_WEIGHTS_NEW["keyword_density"] +
                impact_quality * SCORE_WEIGHTS_NEW["resume_quality"]
            )
            
            # Apply JD validity penalty if needed
            if not jd_is_valid:
                penalty = JD_VALIDITY_PENALTY["invalid_jd_multiplier"]
                ats_match = int(ats_match * penalty)
                keyword_density = int(keyword_density * penalty)
                overall = int(overall * penalty)
            
            scores = Scores(
                ats_match=ats_match,
                keyword_density=keyword_density,
                impact_quality=impact_quality,
                clarity=clarity,
                structure=structure,
                overall=overall
            )
            
            score_breakdown = ScoreBreakdown(
                ats_match=f"ATS score: {ats_match}/100",
                keyword_density=f"Keyword coverage: {keyword_density}%",
                impact_quality=f"Impact score: {impact_quality}/100",
                clarity=f"Clarity score: {clarity}/100",
                structure=f"Structure score: {structure}/100"
            )
            
            # Comprehensive feedback
            match_rating = "Excellent" if overall >= 85 else "Good" if overall >= 70 else "Fair" if overall >= 50 else "Poor"
            
            comprehensive_feedback = ComprehensiveFeedback(
                executive_summary=f"Resume shows {match_rating.lower()} potential with overall score of {overall}/100.",
                match_fit=MatchFit(
                    rating=match_rating,
                    explanation=f"Your resume aligns {match_rating.lower()} with the target role."
                ),
                top_3_strengths=original_analysis.get("strengths", [])[:3],
                top_3_improvements=original_analysis.get("weak_statements", [])[:3],
                immediate_actions=original_analysis.get("critical_issues", [])[:3],
                long_term_improvements=[],
                likelihood_of_ats_pass=original_analysis.get("ats_safety_score", 50),
                likelihood_of_human_review=overall
            )
            
            # Keyword extraction
            keyword_extraction = KeywordExtraction(
                required_skills=parsed_jd.get("required_skills", []),
                role_keywords=parsed_jd.get("role_keywords", []),
                industry_keywords=parsed_jd.get("industry_keywords", []),
                action_verbs=parsed_jd.get("action_verbs", []),
                tools_technologies=parsed_jd.get("tools_technologies", [])
            )
            
            # Build final result
            analysis_result = AnalysisResult(
                keyword_extraction=keyword_extraction,
                content_analysis=content_analysis,
                resume_vs_job=resume_vs_job,
                rewrite_suggestions=rewrite_suggestions,
                ats_warnings=ats_warnings,
                impact_assessment=impact_assessment,
                comprehensive_feedback=comprehensive_feedback,
                scores=scores,
                score_breakdown=score_breakdown
            )
            
            status.update(label="✅ Analysis complete!", state="complete")
            return analysis_result
        
        except Exception as e:
            status.update(label="❌ Report building failed", state="error")
            raise ValueError(f"Result building error: {str(e)}")