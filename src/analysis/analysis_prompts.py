"""
Consolidated prompts for all resume analysis specialists.
Single source of truth for Parser, Critic, and Editor prompts.
"""

# ============================================================================
# PARSER SPECIALIST PROMPTS - SIMPLIFIED
# ============================================================================

PARSER_SYSTEM_INSTRUCTION = """You are a JSON parser. Extract data and return ONLY valid JSON. No explanations."""

PARSER_PARSE_RESUME_PROMPT = """Extract resume data into this exact JSON format:

RESUME:
{resume_text}

Return ONLY JSON:
{{"summary": "summary text", "skills": ["skill1"], "experience": ["job1"], "education": ["degree1"], "projects": [], "missing_sections": []}}"""

PARSER_PARSE_JOB_DESCRIPTION_PROMPT = """Extract job data into this exact JSON format:

JOB:
{job_description}

Return ONLY JSON:
{{"required_skills": ["skill1"], "role_keywords": ["keyword1"], "industry_keywords": ["kw1"], "action_verbs": ["verb1"], "tools_technologies": ["tool1"], "responsibilities": ["resp1"], "qualifications": ["qual1"]}}"""

# ============================================================================
# CRITIC SPECIALIST PROMPTS
# ============================================================================

CRITIC_SYSTEM_INSTRUCTION = """You are a Resume Critic. Score and analyze resumes. Return valid JSON only.

Score 4 dimensions 0-100:
- impact: results and action verbs
- brevity: conciseness
- style: clarity and professionalism  
- skills: relevant skill presence

Include: scores, ats_safety_score, keyword_gaps, critical_issues, weak_statements, strengths, overall_impression"""

CRITIC_AUDIT_ORIGINAL_PROMPT = """Audit this resume and job description.

RESUME:
{parsed_resume}

JOB:
{job_description}

Return JSON with scores (impact, brevity, style, skills as 0-100), ats_safety_score (0-100), keyword_gaps (list), critical_issues (list), weak_statements (list), strengths (list), overall_impression (text)."""

CRITIC_AUDIT_EDITED_PROMPT = """Compare original and edited resume. Provide final scores.

ORIGINAL:
{original_resume}

EDITED:
{edited_resume}

IMPROVEMENTS:
{improvements}

Return JSON with scores (impact, brevity, style, skills as 0-100), ats_safety_score (0-100), improvements_summary (text), remaining_issues (list), quality_improvement_percentage (0-100)."""

# ============================================================================
# EDITOR SPECIALIST PROMPTS
# ============================================================================

EDITOR_SYSTEM_INSTRUCTION = """You are a Resume Editor. Rewrite weaknesses without inventing facts. Return JSON with improved resume."""

EDITOR_REWRITE_PROMPT = """Rewrite this resume to fix weaknesses.

ORIGINAL:
{original_resume}

CRITIC FEEDBACK:
{critic_feedback}

WEAK STATEMENTS:
{weak_statements}

Return JSON with: summary (text), skills (list), experience (list), education (list), projects (list), bullet_improvements (list of objects with: original, improved, reason)"""

# ============================================================================
# LEGACY/UNIFIED ANALYSIS PROMPTS (for reference, can be deprecated)
# ============================================================================

UNIFIED_JOB_MATCHING_PROMPT = """You are an ATS and resume matching expert. Analyze the resume against the job in ONE response.

IMPORTANT VALIDATION RULES:
- First, assess if the job description is LEGITIMATE and MEANINGFUL
- A legitimate JD should contain:
  * Actual job responsibilities or duties
  * Required skills or qualifications
  * Meaningful business context
  * Professional language and structure
- REJECT as invalid: Spam, jokes, nonsense, insults, random text, gibberish
- If JD is clearly invalid/joke/nonsense: Set ats_safety_score and keyword_density to 0-15 ONLY

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

SCORING RULES:
- ats_safety_score: 0-100. Base on keyword alignment. If JD is invalid, max 15.
- keyword_density: 0-100. Percentage of JD keywords found in resume. If JD is invalid, max 15.
- If no meaningful match exists, scores should reflect reality (not inflated)
- Do NOT give high scores to poor matches just to be polite

Respond ONLY as JSON with this nested structure (no markdown, no preamble):
{{
  "jd_validation": {{
    "is_valid_jd": true,
    "validity_reason": "brief explanation of legitimacy assessment",
    "jd_quality_score": 85
  }},
  "keyword_extraction": {{
    "required_skills": ["skill1", "skill2"],
    "role_keywords": ["keyword1"],
    "industry_keywords": ["keyword1"],
    "action_verbs": ["verb1"],
    "tools_technologies": ["tool1"]
  }},
  "resume_vs_job_match": {{
    "skill_matches": {{
      "matched": ["skill1"],
      "missing": ["skill2"]
    }},
    "tool_matches": {{
      "matched": ["tool1"],
      "missing": ["tool2"]
    }},
    "keyword_density": 75,
    "ats_safety_score": 82,
    "critical_missing_keywords": ["keyword1"],
    "strength_areas": ["area1"],
    "improvement_areas": ["area1"]
  }},
  "rewrite_suggestions": {{
    "summary_rewrite": "improved summary or null",
    "bullet_improvements": [
      {{
        "original": "original bullet",
        "improved": "improved with keywords and metrics",
        "section": "Experience|Skills|Education",
        "reasoning": "why this is better"
      }}
    ],
    "keywords_to_add": ["keyword1"],
    "structure_improvements": ["suggestion1"],
    "quick_wins": ["win1"]
  }},
  "comprehensive_feedback": {{
    "executive_summary": "2-3 sentence overview",
    "match_fit": {{
      "rating": "Excellent|Good|Fair|Poor",
      "explanation": "why this rating"
    }},
    "top_3_strengths": ["strength1"],
    "top_3_improvements": ["improvement1"],
    "immediate_actions": ["action1"],
    "long_term_improvements": ["improvement1"],
    "likelihood_of_ats_pass": 85,
    "likelihood_of_human_review": 90
  }}
}}"""

UNIFIED_RESUME_ANALYSIS_PROMPT = """You are an expert resume analyst. Analyze the resume comprehensively in ONE response.

RESUME:
{resume_text}

CONTEXT: Target role is {job_title}

Respond ONLY as JSON with this exact structure (no markdown, no preamble):
{{
  "content_analysis": {{
    "identified_skills": ["skill1", "skill2"],
    "experience_strength": "assessment of work experience quality",
    "achievement_density": "score 1-10 on quantifiable achievements",
    "keyword_richness": "assessment of relevant terminology used",
    "section_completeness": {{
      "summary": true/false,
      "experience": true/false,
      "skills": true/false,
      "education": true/false,
      "projects": false/false
    }},
    "missing_sections": ["section1"],
    "action_verb_usage": "assessment of action verbs in bullets"
  }},
  "ats_analysis": {{
    "formatting_issues": [
      {{
        "issue": "description",
        "severity": "high|medium|low",
        "fix": "how to fix it"
      }}
    ],
    "keyword_gaps": ["gap1"],
    "readability_score": 8,
    "ats_pass_probability": 85,
    "critical_fixes": ["fix1"],
    "nice_to_haves": ["improvement1"]
  }},
  "impact_assessment": {{
    "impact_score": 8,
    "clarity_score": 7,
    "professionalism_score": 9,
    "quantification_level": "medium",
    "achievement_statements": ["achievement1"],
    "weak_statements": ["weak statement1"],
    "recommendations": ["rec1"],
    "overall_impression": "brief assessment"
  }}
}}"""