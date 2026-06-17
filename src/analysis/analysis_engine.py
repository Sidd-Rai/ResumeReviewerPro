"""
Analysis Engine - Uses unified pipeline for single 4-call execution.
Returns comprehensive AnalysisResult from shared pipeline data.
"""

import json
import streamlit as st
from typing import Tuple

from src.config.settings import (
    GEMINI_API_KEY,
    SCORE_WEIGHTS_NEW,
    JD_VALIDITY_PENALTY,
)

from src.services.unified_pipeline import UnifiedAnalysisPipeline
from src.analysis.analysis_result import (
    KeywordExtraction,
    SectionCompleteness,
    ResumeContentAnalysis,
    ResumeVsJobMatch,
    KeywordMatch,
    BulletImprovement,
    RewriteSuggestions,
    ATSWarnings,
    ImpactAssessment,
    ComprehensiveFeedback,
    MatchFit,
    Scores,
    ScoreBreakdown,
    AnalysisResult,
)


class AnalysisEngine:
    """
    Analysis engine using unified pipeline.
    Eliminates duplicate 4-call execution.
    """
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing or unconfigured.")
        self.pipeline = UnifiedAnalysisPipeline()
    
    def analyze_resume(
        self,
        resume_text: str,
        job_description: str = "",
        job_title: str = "Target Role"
    ) -> AnalysisResult:
        """
        Execute analysis pipeline once via unified pipeline.
        Builds AnalysisResult from pipeline output.
        """
        
        # Execute unified pipeline
        status = st.status("📋 Analyzing resume with unified pipeline...", expanded=True)
        
        try:
            pipeline_result = self.pipeline.execute(
                resume_text=resume_text,
                job_description=job_description,
                job_title=job_title
            )
            
            parsed_resume = pipeline_result["parsed_resume"]
            parsed_jd = pipeline_result["parsed_jd"]
            original_analysis = pipeline_result["original_analysis"]
            edited_resume = pipeline_result["edited_resume"]
            final_analysis = pipeline_result["final_analysis"]
            jd_validation = pipeline_result["jd_validation"]
            
            status.update(label="✅ Pipeline complete, building report...", state="running")
        except Exception as e:
            status.update(label="❌ Analysis failed", state="error")
            raise ValueError(f"Pipeline execution error: {str(e)}")
        
        # Build AnalysisResult
        try:
            jd_is_valid = jd_validation["is_valid"]
            jd_quality_score = jd_validation["quality_score"]
            
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
                score_breakdown=score_breakdown,
                pipeline_result=pipeline_result  # Store for MultiAgentResumeService
            )
            
            status.update(label="✅ Analysis complete!", state="complete")
            return analysis_result
        
        except Exception as e:
            status.update(label="❌ Report building failed", state="error")
            raise ValueError(f"Result building error: {str(e)}")
