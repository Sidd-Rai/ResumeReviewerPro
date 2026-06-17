from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class KeywordExtraction:
    """Extracted keywords from job description."""
    required_skills: List[str]
    role_keywords: List[str]
    industry_keywords: List[str]
    action_verbs: List[str]
    tools_technologies: List[str]

@dataclass
class SectionCompleteness:
    """Track which resume sections are present."""
    summary: bool
    experience: bool
    skills: bool
    education: bool
    projects: bool

@dataclass
class ResumeContentAnalysis:
    """Analysis of resume content quality."""
    identified_skills: List[str]
    experience_strength: str
    achievement_density: int  # 1-10
    keyword_richness: str
    section_completeness: SectionCompleteness
    missing_sections: List[str]
    action_verb_usage: str

@dataclass
class KeywordMatch:
    """Matched and unmatched keywords."""
    matched: List[str]
    missing: List[str]

@dataclass
class ResumeVsJobMatch:
    """Resume-to-job matching analysis."""
    skill_matches: KeywordMatch
    tool_matches: KeywordMatch
    keyword_density: int  # 0-100
    ats_safety_score: int  # 0-100
    critical_missing_keywords: List[str]
    strength_areas: List[str]
    improvement_areas: List[str]

@dataclass
class BulletImprovement:
    """Suggested improvement for a bullet point."""
    original: str
    improved: str
    section: str
    reasoning: str

@dataclass
class RewriteSuggestions:
    """All rewrite suggestions for the resume."""
    summary_rewrite: Optional[str]
    bullet_improvements: List[BulletImprovement]
    keywords_to_add: List[str]
    structure_improvements: List[str]
    quick_wins: List[str]

@dataclass
class FormattingIssue:
    """A single ATS formatting issue."""
    issue: str
    severity: str  # high|medium|low
    fix: str

@dataclass
class ATSWarnings:
    """ATS compliance and formatting issues."""
    formatting_issues: List[FormattingIssue]
    keyword_gaps: List[str]
    readability_score: int  # 1-10
    ats_pass_probability: int  # 0-100
    critical_fixes: List[str]
    nice_to_haves: List[str]

@dataclass
class ImpactAssessment:
    """Assessment of resume impact and presentation."""
    impact_score: int  # 1-10
    clarity_score: int  # 1-10
    professionalism_score: int  # 1-10
    quantification_level: str  # high|medium|low
    achievement_statements: List[str]
    weak_statements: List[str]
    recommendations: List[str]
    overall_impression: str

@dataclass
class MatchFit:
    """Job match fit assessment."""
    rating: str  # Excellent|Good|Fair|Poor
    explanation: str

@dataclass
class ComprehensiveFeedback:
    """Final comprehensive feedback."""
    executive_summary: str
    match_fit: MatchFit
    top_3_strengths: List[str]
    top_3_improvements: List[str]
    immediate_actions: List[str]
    long_term_improvements: List[str]
    likelihood_of_ats_pass: int
    likelihood_of_human_review: int

@dataclass
class Scores:
    """All resume scores."""
    ats_match: int  # 0-100
    keyword_density: int  # 0-100
    impact_quality: int  # 0-100
    clarity: int  # 0-100
    structure: int  # 0-100
    overall: int  # 0-100

@dataclass
class ScoreBreakdown:
    """Explanation for each score."""
    ats_match: str
    keyword_density: str
    impact_quality: str
    clarity: str
    structure: str

@dataclass
class ScoringResult:
    """Complete scoring results."""
    scores: Scores
    scoring_breakdown: ScoreBreakdown

@dataclass
class AnalysisResult:
    """Complete analysis result aggregating all analyses."""
    keyword_extraction: KeywordExtraction
    content_analysis: ResumeContentAnalysis
    resume_vs_job: ResumeVsJobMatch
    rewrite_suggestions: RewriteSuggestions
    ats_warnings: ATSWarnings
    impact_assessment: ImpactAssessment
    comprehensive_feedback: ComprehensiveFeedback
    scores: Scores
    score_breakdown: ScoreBreakdown
    pipeline_result: Dict[str, Any] = field(default_factory=dict)
    
    def get_overall_score(self) -> int:
        """Calculate weighted overall score."""
        return self.scores.overall
    
    def get_critical_items(self) -> List[str]:
        """Get all critical items that need immediate attention."""
        items = []
        items.extend(self.ats_warnings.critical_fixes)
        items.extend(self.comprehensive_feedback.immediate_actions)
        return items[:5]  # Top 5
