"""
OPTIMIZED Analysis Engine: Reduced calls to 2.

Call 1: UNIFIED_RESUME_ANALYSIS_PROMPT
  - Content Analysis
  - ATS Analysis
  - Impact Assessment

Call 2: UNIFIED_JOB_MATCHING_PROMPT (only if job_description provided)
  - Keyword Extraction
  - Resume vs Job Match
  - Rewrite Suggestions
  - Comprehensive Feedback
"""

import json
import re
import streamlit as st
from google import genai
from google.genai import types
from src.config.settings import PARSER_MODEL, SCORE_FACTOR_MULTIPLEERS
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
    """Orchestrates optimized resume analysis with minimal API calls."""
    
    def __init__(self):
        self.client = genai.Client()
        self.parser_model = PARSER_MODEL
    
    def _call_gemini_json(self, prompt: str, model: str = None) -> dict:
        """Call Gemini and parse JSON response robustly, ignoring trailing garbage."""
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
                    raise ValueError("No JSON object found in the response string.")
            except Exception as e:
                print(f"--- FAILED TO PARSE JSON ---\nRAW TEXT:\n{text}\n---------------------------")
                raise ValueError(f"Fatal JSON parsing error: {e}")        
    
    def _call_gemini_text(self, prompt: str, model: str = None) -> str:
        """Call Gemini and get text response."""
        if model is None:
            model = self.parser_model
            
        response = self.client.models.generate_content(
            model=model,
            contents=prompt
        )
        return response.text
    
    def analyze_resume(
        self,
        resume_text: str,
        job_description: str = "",
        job_title: str = "Target Role"
    ) -> AnalysisResult:
        """
        OPTIMIZED: Perform comprehensive resume analysis with 1-2 API calls.
        
        - Call 1: Resume-only analysis (content, ATS, impact)
        - Call 2 (optional): Job-matching analysis (only if job_description provided)
        """
        
        # ============================================================================
        # CALL 1: UNIFIED RESUME ANALYSIS (content, ATS, impact in ONE call)
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
        # CALL 2: UNIFIED JOB MATCHING ANALYSIS (only if job_description provided)
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
            
            # Extract nested keyword_extraction
            keywords_data = job_data.get("keyword_extraction", {})
            keyword_extraction = KeywordExtraction(
                required_skills=keywords_data.get("required_skills", []),
                role_keywords=keywords_data.get("role_keywords", []),
                industry_keywords=keywords_data.get("industry_keywords", []),
                action_verbs=keywords_data.get("action_verbs", []),
                tools_technologies=keywords_data.get("tools_technologies", [])
            )
            
            # Extract nested resume_vs_job_match
            match_data = job_data.get("resume_vs_job_match", {})
            resume_vs_job = ResumeVsJobMatch(
                skill_matches=KeywordMatch(**match_data.get("skill_matches", {"matched": [], "missing": []})),
                tool_matches=KeywordMatch(**match_data.get("tool_matches", {"matched": [], "missing": []})),
                keyword_density=match_data.get("keyword_density", 0),
                ats_safety_score=match_data.get("ats_safety_score", 0),
                critical_missing_keywords=match_data.get("critical_missing_keywords", []),
                strength_areas=match_data.get("strength_areas", []),
                improvement_areas=match_data.get("improvement_areas", [])
            )
            
            # Extract nested rewrite_suggestions
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
            
            # Extract nested comprehensive_feedback
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
        # SCORING (no API call, all local computation)
        # ============================================================================
        ats_score = resume_vs_job.ats_safety_score
        kw_density = resume_vs_job.keyword_density
        impact = impact_assessment.impact_score * 10
        clarity = impact_assessment.clarity_score * 10
        structure = 100 if not content_analysis.missing_sections else (100 - (len(content_analysis.missing_sections) * 15))
        
        overall_score = int(
            (ats_score * SCORE_FACTOR_MULTIPLEERS["ats_score_multiplier"]) + 
            (kw_density *  SCORE_FACTOR_MULTIPLEERS["kw_density_multiplier"]) + 
            (impact *  SCORE_FACTOR_MULTIPLEERS["impact_multiplier"]) + 
            (clarity *  SCORE_FACTOR_MULTIPLEERS["clarity_multiplier"]) + 
            (structure *  SCORE_FACTOR_MULTIPLEERS["structure_score_multiplier"])
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
            ats_match=f"Based strictly on job description overlap. Score: {ats_score}/100",
            keyword_density=f"Keyword presence calculated at {kw_density}%.",
            impact_quality=f"Action-Impact formatting graded at {impact}/100.",
            clarity=f"Readability and flow scored at {clarity}/100.",
            structure=f"Section completeness scored at {structure}/100."
        )
        
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