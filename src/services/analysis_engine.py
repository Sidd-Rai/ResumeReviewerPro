"""
Analysis engine that orchestrates multi-prompt pipeline for resume analysis.
"""

import json
import re
import streamlit as st
from google import genai
from google.genai import types
from src.config.settings import PARSER_MODEL, CRITIC_MODEL, EDITOR_MODEL,SCORE_FACTOR_MULTIPLEERS
from src.prompts.analysis_prompts import (
    KEYWORD_EXTRACTION_PROMPT,
    RESUME_CONTENT_ANALYSIS_PROMPT,
    RESUME_VS_JOB_MATCH_PROMPT,
    REWRITE_SUGGESTIONS_PROMPT,
    ATS_WARNINGS_PROMPT,
    IMPACT_ASSESSMENT_PROMPT,
    COMPREHENSIVE_FEEDBACK_PROMPT,
)
from src.models.analysis_result import (
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
    """Orchestrates multi-prompt resume analysis."""
    
    def __init__(self):
        self.client = genai.Client()
        self.parser_model = PARSER_MODEL
        self.critic_model = CRITIC_MODEL
        self.editor_model = EDITOR_MODEL
    
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
        Perform comprehensive resume analysis.
        Returns AnalysisResult with all dimensions analyzed.
        """
        
        st.status_placeholder = st.status("Step 1/8: Extracting job keywords...", expanded=True)
        
        if job_description:
            keywords_prompt = KEYWORD_EXTRACTION_PROMPT.format(
                job_description=job_description
            )
            keywords_data = self._call_gemini_json(keywords_prompt)
            keyword_extraction = KeywordExtraction(**keywords_data)
        else:
            keyword_extraction = KeywordExtraction(
                required_skills=[], role_keywords=[], industry_keywords=[],
                action_verbs=[], tools_technologies=[]
            )
        
        st.status_placeholder.update(label="Step 2/8: Analyzing resume content...", state="running")
        
        content_prompt = RESUME_CONTENT_ANALYSIS_PROMPT.format(resume_text=resume_text)
        content_data = self._call_gemini_json(content_prompt)
        
        section_completeness = SectionCompleteness(**content_data["section_completeness"])
        content_analysis = ResumeContentAnalysis(
            identified_skills=content_data["identified_skills"],
            experience_strength=content_data["experience_strength"],
            achievement_density=content_data["achievement_density"],
            keyword_richness=content_data["keyword_richness"],
            section_completeness=section_completeness,
            missing_sections=content_data["missing_sections"],
            action_verb_usage=content_data["action_verb_usage"]
        )
        
        st.status_placeholder.update(label="Step 3/8: Matching resume to job...", state="running")
        
        if job_description:
            match_prompt = RESUME_VS_JOB_MATCH_PROMPT.format(
                resume_text=resume_text,
                required_skills=", ".join(keyword_extraction.required_skills),
                tools_technologies=", ".join(keyword_extraction.tools_technologies),
                role_keywords=", ".join(keyword_extraction.role_keywords)
            )
            match_data = self._call_gemini_json(match_prompt)
            
            resume_vs_job = ResumeVsJobMatch(
                skill_matches=KeywordMatch(**match_data["skill_matches"]),
                tool_matches=KeywordMatch(**match_data["tool_matches"]),
                keyword_density=match_data["keyword_density"],
                ats_safety_score=match_data["ats_safety_score"],
                critical_missing_keywords=match_data["critical_missing_keywords"],
                strength_areas=match_data["strength_areas"],
                improvement_areas=match_data["improvement_areas"]
            )
        else:
            resume_vs_job = ResumeVsJobMatch(
                skill_matches=KeywordMatch(matched=[], missing=[]),
                tool_matches=KeywordMatch(matched=[], missing=[]),
                keyword_density=0, ats_safety_score=0,
                critical_missing_keywords=[], strength_areas=[],
                improvement_areas=[]
            )
        
        st.status_placeholder.update(label="Step 4/8: Generating rewrite suggestions...", state="running")
        
        rewrite_prompt = REWRITE_SUGGESTIONS_PROMPT.format(
            resume_text=resume_text,
            missing_keywords=", ".join(resume_vs_job.critical_missing_keywords),
            weak_areas=", ".join(resume_vs_job.improvement_areas),
            target_skills=", ".join(keyword_extraction.required_skills)
        )
        rewrite_data = self._call_gemini_json(rewrite_prompt)
        
        bullet_improvements = [
            BulletImprovement(**item) for item in rewrite_data["bullet_improvements"]
        ]
        rewrite_suggestions = RewriteSuggestions(
            summary_rewrite=rewrite_data.get("summary_rewrite"),
            bullet_improvements=bullet_improvements,
            keywords_to_add=rewrite_data["keywords_to_add"],
            structure_improvements=rewrite_data["structure_improvements"],
            quick_wins=rewrite_data["quick_wins"]
        )
        
        st.status_placeholder.update(label="Step 5/8: Checking ATS compliance...", state="running")
        
        ats_prompt = ATS_WARNINGS_PROMPT.format(resume_text=resume_text)
        ats_data = self._call_gemini_json(ats_prompt)
        
        formatting_issues = [
            FormattingIssue(**issue) for issue in ats_data["formatting_issues"]
        ]
        ats_warnings = ATSWarnings(
            formatting_issues=formatting_issues,
            keyword_gaps=ats_data["keyword_gaps"],
            readability_score=ats_data["readability_score"],
            ats_pass_probability=ats_data["ats_pass_probability"],
            critical_fixes=ats_data["critical_fixes"],
            nice_to_haves=ats_data["nice_to_haves"]
        )
        
        st.status_placeholder.update(label="Step 6/8: Assessing impact quality...", state="running")
        
        impact_prompt = IMPACT_ASSESSMENT_PROMPT.format(
            resume_text=resume_text,
            job_title=job_title
        )
        impact_data = self._call_gemini_json(impact_prompt)
        
        impact_assessment = ImpactAssessment(
            impact_score=impact_data["impact_score"],
            clarity_score=impact_data["clarity_score"],
            professionalism_score=impact_data["professionalism_score"],
            quantification_level=impact_data["quantification_level"],
            achievement_statements=impact_data["achievement_statements"],
            weak_statements=impact_data["weak_statements"],
            recommendations=impact_data["recommendations"],
            overall_impression=impact_data["overall_impression"]
        )
        
        st.status_placeholder.update(label="Step 7/8: Generating comprehensive feedback...", state="running")
        
        feedback_prompt = COMPREHENSIVE_FEEDBACK_PROMPT.format(
            resume_text=resume_text,
            job_description=job_description if job_description else "Not provided",
            analysis_context=f"Content: {content_analysis.experience_strength}, Match: {resume_vs_job.keyword_density}%"
        )
        feedback_data = self._call_gemini_json(feedback_prompt)
        
        comprehensive_feedback = ComprehensiveFeedback(
            executive_summary=feedback_data["executive_summary"],
            match_fit=MatchFit(**feedback_data["match_fit"]),
            top_3_strengths=feedback_data["top_3_strengths"],
            top_3_improvements=feedback_data["top_3_improvements"],
            immediate_actions=feedback_data["immediate_actions"],
            long_term_improvements=feedback_data["long_term_improvements"],
            likelihood_of_ats_pass=feedback_data["likelihood_of_ats_pass"],
            likelihood_of_human_review=feedback_data["likelihood_of_human_review"]
        )
        
        st.status_placeholder.update(label="Step 8/8: Calculating final scores...", state="running")
        
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