import json
import re
import streamlit as st
from google.genai import types
from src.config.settings import (
    PARSER_MODEL,
    CRITIC_MODEL,
    EDITOR_MODEL,
    SCORE_WEIGHTS_NEW,
    RESUME_QUALITY_WEIGHTS,
    JD_VALIDITY_PENALTY,
    MIN_JOB_DESCRIPTION_LENGTH,
    MIN_JOB_DESCRIPTION_WORDS
)
from src.services.gemini_runtime import get_gemini_client, get_prompt_cache_name
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
    3-Specialist Pipeline with Persistent Chats and Feedback Loops.
    
    Phase 1: PARSER - Extracts structured resume data (persistent chat)
    Phase 2: CRITIC - Audits and scores, analyzes against job (persistent chat)
    Phase 3: EDITOR - Rewrites weak bullets based on critic feedback (persistent chat)
    Phase 4: SELF-CORRECTION - Critic audits editor's work (feedback loop)
    """
    
    def __init__(self):
        self.client = get_gemini_client()
        self.parser_model = PARSER_MODEL
        self.critic_model = CRITIC_MODEL
        self.editor_model = EDITOR_MODEL
        self._init_specialist_chats()
    
    def _init_specialist_chats(self):
        """Initialize persistent conversation histories for each specialist."""

        parser_system_instruction = (
            "You are a Structural Resume Parser. Your role is to:\n"
            "1. Accept raw resume text\n"
            "2. Extract and structure into JSON: skills, experience, education, projects, summary\n"
            "3. Identify missing sections and incomplete information\n"
            "4. Return minified, valid JSON only (no prose, no markdown)\n\n"
            "Output format:\n"
            "{\n"
            "  \"summary\": \"...\",\n"
            "  \"skills\": [...],\n"
            "  \"experience\": [...],\n"
            "  \"education\": [...],\n"
            "  \"projects\": [...],\n"
            "  \"missing_sections\": [...]\n"
            "}"
        )
        critic_system_instruction = (
            "You are an elite Resume Critic and ATS Auditor. Your role is to:\n"
            "1. Accept parsed resume structure and job description (if provided)\n"
            "2. Score resume on 4 dimensions (0-100 each):\n"
            "   - impact: Quantifiable results and action verbs\n"
            "   - brevity: Word density, filler reduction\n"
            "   - style: Clarity, formatting, no clichés\n"
            "   - skills: Industry-relevant skill presence\n"
            "3. If job provided: Extract keywords, identify gaps, assess ATS match\n"
            "4. Flag critical issues and weak statements\n"
            "5. Return valid JSON with scores and detailed feedback\n\n"
            "Output format:\n"
            "{\n"
            "  \"scores\": {\"impact\": 0-100, \"brevity\": 0-100, \"style\": 0-100, \"skills\": 0-100},\n"
            "  \"job_keywords\": [...],\n"
            "  \"keyword_gaps\": [...],\n"
            "  \"ats_score\": 0-100,\n"
            "  \"critical_issues\": [...],\n"
            "  \"weak_statements\": [...],\n"
            "  \"strengths\": [...]\n"
            "}"
        )
        editor_system_instruction = (
            "You are a Master Executive Resume Editor. Your role is to:\n"
            "1. Accept parsed resume, critic's feedback, and weak statements\n"
            "2. Rewrite weak bullets to add impact without inventing false facts\n"
            "3. Inject quantifiable metrics where possible\n"
            "4. Enforce consistency and clarity\n"
            "5. Fix formatting and ATS issues flagged by critic\n"
            "6. Return both improved resume JSON and bullet-by-bullet improvements\n\n"
            "Output format:\n"
            "{\n"
            "  \"improved_resume\": {...parsed resume with rewrites...},\n"
            "  \"bullet_improvements\": [\n"
            "    {\"original\": \"...\", \"improved\": \"...\", \"reasoning\": \"...\"}\n"
            "  ],\n"
            "  \"changes_summary\": \"...\"\n"
            "}"
        )

        parser_cache = get_prompt_cache_name(
            model=self.parser_model,
            display_name="analysis-parser-system",
            system_instruction=parser_system_instruction,
        )
        critic_cache = get_prompt_cache_name(
            model=self.critic_model,
            display_name="analysis-critic-system",
            system_instruction=critic_system_instruction,
        )
        editor_cache = get_prompt_cache_name(
            model=self.editor_model,
            display_name="analysis-editor-system",
            system_instruction=editor_system_instruction,
        )

        # SPECIALIST 1: THE PARSER
        self.parser_chat = self.client.chats.create(
            model=self.parser_model,
            config=types.GenerateContentConfig(
                cached_content=parser_cache,
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        # SPECIALIST 2: THE CRITIC
        self.critic_chat = self.client.chats.create(
            model=self.critic_model,
            config=types.GenerateContentConfig(
                cached_content=critic_cache,
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        # SPECIALIST 3: THE EDITOR
        self.editor_chat = self.client.chats.create(
            model=self.editor_model,
            config=types.GenerateContentConfig(
                cached_content=editor_cache,
                temperature=0.4,
                response_mime_type="application/json"
            )
        )
    
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
    
    def _parse_json_response(self, text: str) -> dict:
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
        # PHASE 1: PARSER - Extract structured resume data
        # ============================================================================
        st.status_placeholder = st.status("📋 Parser: Extracting resume structure...", expanded=True)
        
        parser_prompt = f"Extract and structure this resume into JSON format:\n\n{resume_text}"
        parser_response = self.parser_chat.send_message(parser_prompt).text
        parsed_resume = self._parse_json_response(parser_response)
        
        st.status_placeholder.update(label="🔍 Critic: Analyzing quality and gaps...", state="running")
        
        # ============================================================================
        # PHASE 2: CRITIC - Audit and score (with job context)
        # ============================================================================
        critic_prompt = (
            f"Audit this resume structure against the target role.\n\n"
            f"Target Role: {job_title}\n"
            f"Job Description: {job_description if job_description else 'General industry metrics'}\n\n"
            f"Resume Structure:\n{json.dumps(parsed_resume, indent=2)}\n\n"
            f"Provide detailed scoring, gap analysis, and critical issues."
        )
        critic_response = self.critic_chat.send_message(critic_prompt).text
        critic_analysis = self._parse_json_response(critic_response)
        
        st.status_placeholder.update(label="✏️ Editor: Rewriting weak points...", state="running")
        
        # ============================================================================
        # PHASE 3: EDITOR - Rewrite based on critic feedback
        # ============================================================================
        editor_prompt = (
            f"Rewrite this resume to fix the vulnerabilities and weak points identified by the Critic.\n\n"
            f"Original Resume:\n{json.dumps(parsed_resume, indent=2)}\n\n"
            f"Critic's Feedback:\n{json.dumps(critic_analysis, indent=2)}\n\n"
            f"Instructions:\n"
            f"1. Rewrite weak statements with stronger action verbs\n"
            f"2. Add quantifiable metrics where possible (don't invent)\n"
            f"3. Fix ATS issues\n"
            f"4. Improve clarity and brevity\n"
            f"5. Return improved resume JSON and detailed bullet improvements"
        )
        editor_response = self.editor_chat.send_message(editor_prompt).text
        editor_improvements = self._parse_json_response(editor_response)
        
        st.status_placeholder.update(label="🔄 Self-Correction: Auditing improvements...", state="running")
        
        # ============================================================================
        # PHASE 4: SELF-CORRECTION - Critic audits editor's fixes (feedback loop)
        # ============================================================================
        correction_prompt = (
            f"Verify and audit the Editor's improvements. Assess quality of the rewrites.\n\n"
            f"Editor's Improvements:\n{json.dumps(editor_improvements, indent=2)}\n\n"
            f"Provide final scores after improvements and summary of changes."
        )
        correction_response = self.critic_chat.send_message(correction_prompt).text
        final_scores = self._parse_json_response(correction_response)
        
        st.status_placeholder.update(label="✅ Compilation: Building final results...", state="running")
        
        # ============================================================================
        # BUILD ANALYSIS RESULT FROM PIPELINE OUTPUTS
        # ============================================================================
        
        # Extract from parser
        parser_data = parsed_resume
        section_completeness = SectionCompleteness(
            summary=bool(parser_data.get("summary")),
            experience=bool(parser_data.get("experience")),
            skills=bool(parser_data.get("skills")),
            education=bool(parser_data.get("education")),
            projects=bool(parser_data.get("projects"))
        )
        
        content_analysis = ResumeContentAnalysis(
            identified_skills=parser_data.get("skills", []),
            experience_strength="Evaluated by critic",
            achievement_density=f"{critic_analysis.get('scores', {}).get('impact', 0)}/100",
            keyword_richness=f"{critic_analysis.get('scores', {}).get('skills', 0)}/100",
            section_completeness=section_completeness,
            missing_sections=parser_data.get("missing_sections", []),
            action_verb_usage=f"{critic_analysis.get('scores', {}).get('style', 0)}/100"
        )
        
        # Extract from critic analysis
        critic_data = critic_analysis
        ats_score = critic_data.get("ats_score", 0)
        keyword_gaps = critic_data.get("keyword_gaps", [])
        job_keywords = critic_data.get("job_keywords", [])
        
        formatting_issues = []
        for issue in critic_data.get("critical_issues", []):
            if isinstance(issue, dict):
                formatting_issues.append(FormattingIssue(
                    issue=issue.get("issue", issue),
                    severity=issue.get("severity", "medium"),
                    fix=issue.get("fix", "")
                ))
            else:
                formatting_issues.append(FormattingIssue(
                    issue=str(issue),
                    severity="medium",
                    fix="See editor improvements"
                ))
        
        ats_warnings = ATSWarnings(
            formatting_issues=formatting_issues,
            keyword_gaps=keyword_gaps,
            readability_score=critic_data.get("scores", {}).get("style", 0),
            ats_pass_probability=ats_score,
            critical_fixes=[issue.get("issue", str(issue)) if isinstance(issue, dict) else str(issue) 
                           for issue in critic_data.get("critical_issues", [])],
            nice_to_haves=[]
        )
        
        impact_assessment = ImpactAssessment(
            impact_score=critic_data.get("scores", {}).get("impact", 0) // 10,
            clarity_score=critic_data.get("scores", {}).get("style", 0) // 10,
            professionalism_score=critic_data.get("scores", {}).get("brevity", 0) // 10,
            quantification_level="medium" if critic_data.get("scores", {}).get("impact", 0) > 50 else "low",
            achievement_statements=critic_data.get("strengths", []),
            weak_statements=critic_data.get("weak_statements", []),
            recommendations=[],
            overall_impression=""
        )
        
        # Extract from editor improvements
        editor_data = editor_improvements
        bullet_improvements = []
        for improvement in editor_data.get("bullet_improvements", []):
            bullet_improvements.append(BulletImprovement(
                original=improvement.get("original", ""),
                improved=improvement.get("improved", ""),
                section="Experience",
                reasoning=improvement.get("reasoning", "")
            ))
        
        rewrite_suggestions = RewriteSuggestions(
            summary_rewrite=editor_data.get("improved_resume", {}).get("summary"),
            bullet_improvements=bullet_improvements,
            keywords_to_add=job_keywords,
            structure_improvements=[],
            quick_wins=[f"Added impact to {len(bullet_improvements)} bullets"]
        )
        
        # Extract job matching if job provided
        if job_description:
            keyword_extraction = KeywordExtraction(
                required_skills=job_keywords[:5],
                role_keywords=job_keywords[5:10] if len(job_keywords) > 5 else [],
                industry_keywords=job_keywords[10:] if len(job_keywords) > 10 else [],
                action_verbs=[],
                tools_technologies=[]
            )
            
            matched_skills = [s for s in job_keywords if any(skill.lower() in str(parser_data.get("skills", [])).lower() 
                                                              for skill in [s])]
            
            match_scores = {
                "ats_safety_score": ats_score,
                "keyword_density": ats_score
            }
            
            # Apply JD validity penalty
            match_scores = self._apply_jd_validity_penalty(match_scores, jd_is_valid, jd_quality_score)
            
            resume_vs_job = ResumeVsJobMatch(
                skill_matches=KeywordMatch(matched=matched_skills, missing=keyword_gaps),
                tool_matches=KeywordMatch(matched=[], missing=[]),
                keyword_density=match_scores["keyword_density"],
                ats_safety_score=match_scores["ats_safety_score"],
                critical_missing_keywords=keyword_gaps[:3],
                strength_areas=critic_data.get("strengths", []),
                improvement_areas=critic_data.get("weak_statements", [])
            )
            
            comprehensive_feedback = ComprehensiveFeedback(
                executive_summary=editor_data.get("changes_summary", ""),
                match_fit=MatchFit(
                    rating="Good" if match_scores["ats_safety_score"] > 70 else "Fair",
                    explanation=f"Resume matches {match_scores['ats_safety_score']}% of job requirements"
                ),
                top_3_strengths=critic_data.get("strengths", [])[:3],
                top_3_improvements=critic_data.get("weak_statements", [])[:3],
                immediate_actions=[f"Incorporate {len(bullet_improvements)} improved bullets"],
                long_term_improvements=keyword_gaps[:3],
                likelihood_of_ats_pass=match_scores["ats_safety_score"],
                likelihood_of_human_review=min(100, match_scores["ats_safety_score"] + 20)
            )
        else:
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
            comprehensive_feedback = ComprehensiveFeedback(
                executive_summary="",
                match_fit=MatchFit(rating="Fair", explanation=""),
                top_3_strengths=[], top_3_improvements=[],
                immediate_actions=[], long_term_improvements=[],
                likelihood_of_ats_pass=0, likelihood_of_human_review=0
            )
        
        # ============================================================================
        # CALCULATE FINAL SCORES (with your existing weights)
        # ============================================================================
        parser_score = 100 if not content_analysis.missing_sections else (100 - len(content_analysis.missing_sections) * 15)
        critic_scores = critic_data.get("scores", {})
        
        # Resume quality components
        impact = critic_scores.get("impact", 50)
        clarity = critic_scores.get("style", 50)
        structure = parser_score
        
        # Resume quality composite score
        resume_quality = int(
            (impact * RESUME_QUALITY_WEIGHTS["impact"]) +
            (clarity * RESUME_QUALITY_WEIGHTS["clarity"]) +
            (structure * RESUME_QUALITY_WEIGHTS["structure"])
        )
        
        # Job match scores
        ats_match_final = resume_vs_job.ats_safety_score
        kw_density_final = resume_vs_job.keyword_density
        
        # Calculate overall score with new weights: 50% ATS + 30% KW + 20% resume quality
        overall_score = int(
            (ats_match_final * SCORE_WEIGHTS_NEW["ats_score"]) +
            (kw_density_final * SCORE_WEIGHTS_NEW["keyword_density"]) +
            (resume_quality * SCORE_WEIGHTS_NEW["resume_quality"])
        )
        
        scores = Scores(
            ats_match=ats_match_final,
            keyword_density=kw_density_final,
            impact_quality=impact,
            clarity=clarity,
            structure=structure,
            overall=overall_score
        )
        
        score_breakdown = ScoreBreakdown(
            ats_match=f"ATS/Keyword match with job description: {ats_match_final}/100",
            keyword_density=f"Keyword coverage: {kw_density_final}%",
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
