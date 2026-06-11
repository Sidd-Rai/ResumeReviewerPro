import json
import re
import streamlit as st
from google import genai
from google.genai import types
from src.config.settings import (
    PARSER_MODEL,
    SCORE_WEIGHTS_NEW,
    RESUME_QUALITY_WEIGHTS,
    JD_VALIDITY_PENALTY,
    MIN_JOB_DESCRIPTION_LENGTH,
    MIN_JOB_DESCRIPTION_WORDS
)
from src.analysis.analysis_prompts import (
    UNIFIED_RESUME_ANALYSIS_PROMPT,
    UNIFIED_JOB_MATCHING_PROMPT,
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
    """Orchestrates optimized resume analysis (Now has JD validation)."""
    
    def __init__(self):
        self.client = genai.Client()
        self.parser_model = PARSER_MODEL
    
    @staticmethod
    def _validate_job_description(job_description: str) -> tuple[bool, str, float]:
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
            r"xxx+",  # Repeated x's
            r"zzz+",  # Repeated z's
        ]
        
        text_lower = job_description.lower()
        nonsense_score = sum(1 for pattern in nonsense_patterns if re.search(pattern, text_lower))
        
        if nonsense_score >= 2:
            return False, "Job description appears to be nonsense/test content", 0.1
        
        # Check minimum professional content (should have some job-like keywords)
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
    
    def _call_gemini_json(self, prompt: str, model: str = None) -> dict:
        """Call Gemini and parse JSON response"""
        if model is None:
            model = self.parser_model
            
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        text = response.text
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    clean_json = match.group(0)
                    return json.loads(clean_json)
                else:
                    raise ValueError("No JSON object found in response.")
            except Exception as e:
                print(f"--- FAILED TO PARSE JSON ---\nRAW TEXT:\n{text}\n---------------------------")
                raise ValueError(f"Fatal JSON parsing error: {e}")
    
    def _apply_jd_validity_penalty(self, scores: dict, is_valid: bool, quality_score: float) -> dict:
        """Apply penalties to scores based on JD validity."""
        if not is_valid:
            penalty = JD_VALIDITY_PENALTY["invalid_jd_multiplier"]
            scores["ats_safety_score"] = min(scores["ats_safety_score"], int(15 * penalty))
            scores["keyword_density"] = min(scores["keyword_density"], int(15 * penalty))
            return scores
        
        if quality_score < 50:
            penalty = JD_VALIDITY_PENALTY["low_relevance_multiplier"]
            scores["ats_safety_score"] = int(scores["ats_safety_score"] * penalty)
            scores["keyword_density"] = int(scores["keyword_density"] * penalty)
        
        return scores
    
    def analyze_resume(
        self,
        resume_text: str,
        job_description: str = "",
        job_title: str = "Target Role"
    ) -> AnalysisResult:
        
        # ============================================================================
        # JOB DESCRIPTION VALIDATION
        # ============================================================================
        jd_is_valid = True
        jd_quality_score = 100.0
        jd_validation_reason = "No job description provided"
        
        if job_description:
            jd_is_valid, jd_validation_reason, jd_quality_score = self._validate_job_description(job_description)
            
            if not jd_is_valid:
                st.warning(f"⚠️ Job Description Issue: {jd_validation_reason}")
        
        # ============================================================================
        # CALL 1: UNIFIED RESUME ANALYSIS
        # ============================================================================
        st.status_placeholder = st.status("Analyzing resume structure, ATS compliance, and impact...", expanded=True)
        
        resume_analysis_prompt = UNIFIED_RESUME_ANALYSIS_PROMPT.format(
            resume_text=resume_text,
            job_title=job_title
        )
        resume_data = self._call_gemini_json(resume_analysis_prompt)
        
        # Extract nested content_analysis
        content_data = resume_data.get("content_analysis", {})
        section_completeness = SectionCompleteness(**content_data.get("section_completeness", {}))
        content_analysis = ResumeContentAnalysis(
            identified_skills=content_data.get("identified_skills", []),
            experience_strength=content_data.get("experience_strength", ""),
            achievement_density=content_data.get("achievement_density", ""),
            keyword_richness=content_data.get("keyword_richness", ""),
            section_completeness=section_completeness,
            missing_sections=content_data.get("missing_sections", []),
            action_verb_usage=content_data.get("action_verb_usage", "")
        )
        
        # Extract nested ats_analysis
        ats_data = resume_data.get("ats_analysis", {})
        formatting_issues = [
            FormattingIssue(**issue) for issue in ats_data.get("formatting_issues", [])
        ]
        ats_warnings = ATSWarnings(
            formatting_issues=formatting_issues,
            keyword_gaps=ats_data.get("keyword_gaps", []),
            readability_score=ats_data.get("readability_score", 0),
            ats_pass_probability=ats_data.get("ats_pass_probability", 0),
            critical_fixes=ats_data.get("critical_fixes", []),
            nice_to_haves=ats_data.get("nice_to_haves", [])
        )
        
        # Extract nested impact_assessment
        impact_data = resume_data.get("impact_assessment", {})
        impact_assessment = ImpactAssessment(
            impact_score=impact_data.get("impact_score", 0),
            clarity_score=impact_data.get("clarity_score", 0),
            professionalism_score=impact_data.get("professionalism_score", 0),
            quantification_level=impact_data.get("quantification_level", ""),
            achievement_statements=impact_data.get("achievement_statements", []),
            weak_statements=impact_data.get("weak_statements", []),
            recommendations=impact_data.get("recommendations", []),
            overall_impression=impact_data.get("overall_impression", "")
        )
        
        # Initialize job-dependent fields with defaults
        keyword_extraction = KeywordExtraction(
            required_skills=[], role_keywords=[], industry_keywords=[],
            action_verbs=[], tools_technologies=[]
        )
        resume_vs_job = ResumeVsJobMatch(
            skill_matches=KeywordMatch(matched=[], missing=[]),
            tool_matches=KeywordMatch(matched=[], missing=[]),
            keyword_density=0, ats_safety_score=0,
            critical_missing_keywords=[], strength_areas=[],
            improvement_areas=[]
        )
        rewrite_suggestions = RewriteSuggestions(
            summary_rewrite=None,
            bullet_improvements=[],
            keywords_to_add=[],
            structure_improvements=[],
            quick_wins=[]
        )
        comprehensive_feedback = ComprehensiveFeedback(
            executive_summary="",
            match_fit=MatchFit(rating="Fair", explanation=""),
            top_3_strengths=[],
            top_3_improvements=[],
            immediate_actions=[],
            long_term_improvements=[],
            likelihood_of_ats_pass=0,
            likelihood_of_human_review=0
        )
        
        # ============================================================================
        # CALL 2: JOB MATCHING ANALYSIS (only if job_description provided)
        # ============================================================================
        if job_description:
            st.status_placeholder.update(
                label="Matching resume against job description...",
                state="running"
            )
            
            job_matching_prompt = UNIFIED_JOB_MATCHING_PROMPT.format(
                resume_text=resume_text,
                job_description=job_description
            )
            job_data = self._call_gemini_json(job_matching_prompt)
            
            # Extract keyword_extraction
            keywords_data = job_data.get("keyword_extraction", {})
            keyword_extraction = KeywordExtraction(
                required_skills=keywords_data.get("required_skills", []),
                role_keywords=keywords_data.get("role_keywords", []),
                industry_keywords=keywords_data.get("industry_keywords", []),
                action_verbs=keywords_data.get("action_verbs", []),
                tools_technologies=keywords_data.get("tools_technologies", [])
            )
            
            # Extract resume_vs_job_match
            match_data = job_data.get("resume_vs_job_match", {})
            match_scores = {
                "ats_safety_score": match_data.get("ats_safety_score", 0),
                "keyword_density": match_data.get("keyword_density", 0)
            }
            
            # Apply JD validity penalty
            match_scores = self._apply_jd_validity_penalty(match_scores, jd_is_valid, jd_quality_score)
            
            resume_vs_job = ResumeVsJobMatch(
                skill_matches=KeywordMatch(**match_data.get("skill_matches", {"matched": [], "missing": []})),
                tool_matches=KeywordMatch(**match_data.get("tool_matches", {"matched": [], "missing": []})),
                keyword_density=match_scores["keyword_density"],
                ats_safety_score=match_scores["ats_safety_score"],
                critical_missing_keywords=match_data.get("critical_missing_keywords", []),
                strength_areas=match_data.get("strength_areas", []),
                improvement_areas=match_data.get("improvement_areas", [])
            )
            
            # Extract rewrite_suggestions
            rewrite_data = job_data.get("rewrite_suggestions", {})
            bullet_improvements = [
                BulletImprovement(**item) for item in rewrite_data.get("bullet_improvements", [])
            ]
            rewrite_suggestions = RewriteSuggestions(
                summary_rewrite=rewrite_data.get("summary_rewrite"),
                bullet_improvements=bullet_improvements,
                keywords_to_add=rewrite_data.get("keywords_to_add", []),
                structure_improvements=rewrite_data.get("structure_improvements", []),
                quick_wins=rewrite_data.get("quick_wins", [])
            )
            
            # Extract comprehensive_feedback
            feedback_data = job_data.get("comprehensive_feedback", {})
            comprehensive_feedback = ComprehensiveFeedback(
                executive_summary=feedback_data.get("executive_summary", ""),
                match_fit=MatchFit(**feedback_data.get("match_fit", {"rating": "Fair", "explanation": ""})),
                top_3_strengths=feedback_data.get("top_3_strengths", []),
                top_3_improvements=feedback_data.get("top_3_improvements", []),
                immediate_actions=feedback_data.get("immediate_actions", []),
                long_term_improvements=feedback_data.get("long_term_improvements", []),
                likelihood_of_ats_pass=feedback_data.get("likelihood_of_ats_pass", 0),
                likelihood_of_human_review=feedback_data.get("likelihood_of_human_review", 0)
            )
        
        st.status_placeholder.update(label="Calculating final scores...", state="running")
        
        # ============================================================================
        # SCORING (ROBUST with JD validity consideration)
        # ============================================================================
        # Resume quality components (normalized to 0-100)
        impact = impact_assessment.impact_score * 10
        clarity = impact_assessment.clarity_score * 10
        structure = 100 if not content_analysis.missing_sections else (100 - (len(content_analysis.missing_sections) * 15))
        
        # Resume quality composite score
        resume_quality = int(
            (impact * RESUME_QUALITY_WEIGHTS["impact"]) +
            (clarity * RESUME_QUALITY_WEIGHTS["clarity"]) +
            (structure * RESUME_QUALITY_WEIGHTS["structure"])
        )
        
        # Job match scores
        ats_score = resume_vs_job.ats_safety_score
        kw_density = resume_vs_job.keyword_density
        
        # Calculate overall score with new weights: 50% ATS + 30% KW + 20% resume quality
        overall_score = int(
            (ats_score * SCORE_WEIGHTS_NEW["ats_score"]) +
            (kw_density * SCORE_WEIGHTS_NEW["keyword_density"]) +
            (resume_quality * SCORE_WEIGHTS_NEW["resume_quality"])
        )
        
        scores = Scores(
            ats_match=ats_score,
            keyword_density=kw_density,
            impact_quality=impact,
            clarity=clarity,
            structure=structure,
            overall=overall_score
        )
        
        score_breakdown = ScoreBreakdown(
            ats_match=f"ATS/Keyword match with job description: {ats_score}/100",
            keyword_density=f"Keyword coverage: {kw_density}%",
            impact_quality=f"Achievement impact quality: {impact}/100",
            clarity=f"Resume readability: {clarity}/100",
            structure=f"Section organization: {structure}/100"
        )
        
        if not jd_is_valid:
            score_breakdown.ats_match += f" ⚠️ ({jd_validation_reason})"
        
        st.status_placeholder.update(label="Analysis Complete!", state="complete")

        return AnalysisResult(
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