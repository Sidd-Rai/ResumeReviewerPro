"""
Gemini Multi-Agent Resume Service - Streaming formatter.
Uses pipeline result from AnalysisEngine, formats for UI.
Eliminates duplicate pipeline execution.
"""

import json
import re
from typing import Optional, Dict, Any
from src.analysis.analysis_result import AnalysisResult
from src.services.unified_pipeline import UnifiedAnalysisPipeline


class MultiAgentResumeService:
    """
    Streaming formatter for analysis results.
    Accepts pipeline result from AnalysisEngine to avoid duplicate execution.
    Falls back to creating own pipeline if needed.
    """
    
    def __init__(self, pipeline_result: Optional[Dict[str, Any]] = None):
        self.pipeline_result = pipeline_result
    
    def stream_pipeline(self, raw_resume_text: str, job_description: str = "", 
                       skip_pipeline: bool = False) -> 'TextStream':
        """
        Stream formatted analysis output.
        
        If pipeline_result provided, uses that.
        Otherwise creates own pipeline execution.
        """
        
        # Use provided result or create new pipeline
        if self.pipeline_result:
            pipeline_result = self.pipeline_result
        else:
            if skip_pipeline:
                return self._empty_stream()
            pipeline = UnifiedAnalysisPipeline()
            pipeline_result = pipeline.execute(raw_resume_text, job_description)
        
        yield_text = self._format_pipeline_output(pipeline_result)
        
        # Create simple generator that yields complete text
        class TextStream:
            def __init__(self, text):
                self.text = text
            
            def __iter__(self):
                yield self
        
        return TextStream("".join(yield_text))
    
    def _format_pipeline_output(self, pipeline_result: Dict[str, Any]) -> list:
        """Format pipeline results for UI display."""
        yield_text = []
        
        try:
            parsed_resume = pipeline_result["parsed_resume"]
            parsed_jd = pipeline_result["parsed_jd"]
            original_analysis = pipeline_result["original_analysis"]
            edited_resume = pipeline_result["edited_resume"]
            final_analysis = pipeline_result["final_analysis"]
            metrics = pipeline_result["metrics"]
            
            # Phase 1: Parsing
            yield_text.append("🔍 **Phase 1: Parsing Resume**\n")
            yield_text.append("Structuring your resume into sections...\n\n")
            yield_text.append("✅ Resume parsed successfully\n")
            yield_text.append(f"Sections found: {', '.join(k for k in parsed_resume.keys() if k != 'missing_sections')}\n\n")
            
            if parsed_jd:
                yield_text.append("🔍 **Analyzing Job Description**\n")
                yield_text.append("✅ Job description analyzed\n\n")
            
            # Phase 2: Quality Analysis
            yield_text.append("🧐 **Phase 2: Analyzing Quality**\n")
            yield_text.append("Running comprehensive quality audit...\n\n")
            
            if "scores" in original_analysis:
                scores = original_analysis["scores"]
                yield_text.append("📊 **Original Resume Scores:**\n")
                for metric, score in scores.items():
                    yield_text.append(f"  • {metric}: {score}/100\n")
                yield_text.append("\n")
            
            if "critical_issues" in original_analysis:
                issues = original_analysis["critical_issues"]
                if issues:
                    yield_text.append("⚠️ **Issues Found:**\n")
                    for issue in issues[:3]:
                        yield_text.append(f"  • {issue}\n")
                    yield_text.append("\n")
            
            # Phase 3: Improvements
            yield_text.append("✏️ **Phase 3: Improving Resume**\n")
            yield_text.append("Rewriting with improvements...\n\n")
            yield_text.append("✅ Resume improved\n\n")
            
            if "bullet_improvements" in edited_resume:
                improvements = edited_resume["bullet_improvements"]
                yield_text.append(f"📝 **{len(improvements)} Bullet Points Improved**\n\n")
            
            # Phase 4: Verification
            yield_text.append("🔄 **Phase 4: Verifying Improvements**\n")
            yield_text.append("Auditing changes...\n\n")
            
            if "scores" in final_analysis:
                scores = final_analysis["scores"]
                yield_text.append("📊 **Final Improved Scores:**\n")
                for metric, score in scores.items():
                    original_score = original_analysis.get("scores", {}).get(metric, 0)
                    improvement = score - original_score
                    improvement_sign = "+" if improvement > 0 else ""
                    yield_text.append(f"  • {metric}: {score}/100 ({improvement_sign}{improvement})\n")
                yield_text.append("\n")
            
            # Metrics
            yield_text.append("📊 **Pipeline Metrics:**\n")
            yield_text.append(f"  • Cache hits: {metrics.get('cache_hits', 0)}\n")
            yield_text.append(f"  • Total tokens used: {metrics.get('total_input_tokens', 0) + metrics.get('total_output_tokens', 0)}\n")
            if metrics.get('total_cache_tokens', 0) > 0:
                yield_text.append(f"  • Tokens saved by cache: {metrics.get('total_cache_tokens', 0)}\n")
            yield_text.append("\n")
            
            yield_text.append("✅ **Analysis Complete!**\n\n")
            yield_text.append("---\n")
            yield_text.append(f"```json\n{json.dumps(final_analysis, indent=2)}\n```")
            
        except Exception as e:
            yield_text.append(f"\n❌ Error formatting output: {str(e)}\n")
        
        return yield_text
    
    def _empty_stream(self) -> 'TextStream':
        """Return empty stream."""
        class TextStream:
            def __init__(self):
                self.text = ""
            
            def __iter__(self):
                yield self
        
        return TextStream()
