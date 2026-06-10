"""
OPTIMIZED: Consolidated prompts for minimal API calls and token usage.
"""

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
      "summary": true,
      "experience": true,
      "skills": true,
      "education": true,
      "projects": false
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

UNIFIED_JOB_MATCHING_PROMPT = """You are an ATS and resume matching expert. Analyze the resume against the job in ONE response.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Respond ONLY as JSON with this exact nested structure (no markdown, no preamble):
{{
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

# Keep old prompts as fallback (can deprecate later)
KEYWORD_EXTRACTION_PROMPT = """
You are an ATS expert analyzing job descriptions to extract critical keywords.

Analyze this job description and extract:
1. REQUIRED_SKILLS: Technical and soft skills that are essential
2. ROLE_KEYWORDS: Job-specific terminology and titles
3. INDUSTRY_KEYWORDS: Industry-specific jargon
4. ACTION_VERBS: Strong action verbs commonly used in this role
5. TOOLS_TECHNOLOGIES: Specific tools, frameworks, platforms mentioned

JOB DESCRIPTION:
{job_description}

Respond ONLY as a JSON object with exactly these keys. Each value should be a list of strings.
Example format:
{{
  "required_skills": ["skill1", "skill2"],
  "role_keywords": ["keyword1"],
  "industry_keywords": ["keyword1"],
  "action_verbs": ["verb1"],
  "tools_technologies": ["tool1"]
}}
"""

RESUME_CONTENT_ANALYSIS_PROMPT = """
You are an expert resume analyst. Analyze this resume for content quality and structure.

RESUME:
{resume_text}

Evaluate and respond ONLY as JSON with these exact keys:
{{
  "identified_skills": ["skill1", "skill2"],
  "experience_strength": "assessment of work experience quality",
  "achievement_density": "score 1-10on quantifiable achievements",
  "keyword_richness": "assessment of relevant terminology used",
  "section_completeness": {{
    "summary": true/false,
    "experience": true/false,
    "skills": true/false,
    "education": true/false,
    "projects": true/false
  }},
  "missing_sections": ["section1", "section2"],
  "action_verb_usage": "assessment of action verbs in bullets"
}}
"""

RESUME_VS_JOB_MATCH_PROMPT = """
You are an ATS matching expert. Compare the resume against required keywords.

RESUME:
{resume_text}

REQUIRED KEYWORDS FROM JOB:
Skills: {required_skills}
Tools/Technologies: {tools_technologies}
Role Keywords: {role_keywords}

Respond ONLY as JSON:
{{
  "skill_matches": {{"matched": ["skill1"], "missing": ["skill2"]}},
  "tool_matches": {{"matched": ["tool1"], "missing": ["tool2"]}},
  "keyword_density": number between 0-100,
  "ats_safety_score": number between 0-100,
  "critical_missing_keywords": ["keyword1", "keyword2"],
  "strength_areas": ["area1"],
  "improvement_areas": ["area1"]
}}
"""

REWRITE_SUGGESTIONS_PROMPT = """
You are an expert resume writer who improves bullet points and descriptions.

CURRENT RESUME:
{resume_text}

ANALYSIS FEEDBACK:
Missing Keywords: {missing_keywords}
Weak Areas: {weak_areas}
Target Skills: {target_skills}

Generate specific rewrites for the resume. Respond ONLY as JSON:
{{
  "summary_rewrite": "improved summary paragraph or null if good",
  "bullet_improvements": [
    {{
      "original": "original bullet point",
      "improved": "improved version with keywords and metrics",
      "section": "Experience|Skills|Education",
      "reasoning": "why this is better"
    }}
  ],
  "keywords_to_add": ["keyword1", "keyword2"],
  "structure_improvements": ["suggestion1", "suggestion2"],
  "quick_wins": ["win1 that requires minimal effort"]
}}
"""

ATS_WARNINGS_PROMPT = """
You are an ATS compliance expert. Find formatting and content issues.

RESUME:
{resume_text}

Check for ATS problems and respond ONLY as JSON:
{{
  "formatting_issues": [
    {{
      "issue": "description",
      "severity": "high|medium|low",
      "fix": "how to fix it"
    }}
  ],
  "keyword_gaps": ["gap1"],
  "readability_score": number 1-10,
  "ats_pass_probability": percentage 0-100,
  "critical_fixes": ["fix1"],
  "nice_to_haves": ["improvement1"]
}}
"""

IMPACT_ASSESSMENT_PROMPT = """
You are an expert at assessing resume impact and presentation quality.

RESUME:
{resume_text}

CONTEXT: This is for a {job_title} role.

Analyze impact and respond ONLY as JSON:
{{
  "impact_score": number 1-10,
  "clarity_score": number 1-10,
  "professionalism_score": number 1-10,
  "quantification_level": "high|medium|low",
  "achievement_statements": ["achievement1"],
  "weak_statements": ["weak statement1"],
  "recommendations": ["rec1"],
  "overall_impression": "brief assessment"
}}
"""

COMPREHENSIVE_FEEDBACK_PROMPT = """
You are the ultimate resume expert providing comprehensive feedback.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

PREVIOUS ANALYSIS RESULTS (for context):
{analysis_context}

Provide comprehensive feedback as JSON:
{{
  "executive_summary": "2-3 sentence overview",
  "match_fit": {{
    "rating": "Excellent|Good|Fair|Poor",
    "explanation": "why this rating"
  }},
  "top_3_strengths": ["strength1", "strength2", "strength3"],
  "top_3_improvements": ["improvement1", "improvement2", "improvement3"],
  "immediate_actions": ["action1", "action2"],
  "long_term_improvements": ["improvement1"],
  "likelihood_of_ats_pass": percentage,
  "likelihood_of_human_review": percentage
}}
"""
