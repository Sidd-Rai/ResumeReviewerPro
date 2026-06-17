import streamlit as st
import pandas as pd

from src.services.export_service import ExportService
from src.config.settings import (
    CHART_HEIGHT,
    DASHBOARD_COLUMN_RATIO,
    DASHBOARD_COLUMN_GAP,
    COLORS,
    SCORE_THRESHOLDS,
    SHOW_BEFORE_AFTER_COMPARISON,
)


def get_score_color(score: int) -> str:
    """Determine color based on score and thresholds."""
    if score >= SCORE_THRESHOLDS["excellent"]:
        return COLORS["excellent"]
    elif score >= SCORE_THRESHOLDS["good"]:
        return COLORS["good"]
    elif score >= SCORE_THRESHOLDS["fair"]:
        return COLORS["fair"]
    else:
        return COLORS["poor"]


def get_score_rating(score: int) -> str:
    """Determine rating label based on score thresholds."""
    if score >= SCORE_THRESHOLDS["excellent"]:
        return "Excellent"
    elif score >= SCORE_THRESHOLDS["good"]:
        return "Good"
    elif score >= SCORE_THRESHOLDS["fair"]:
        return "Fair"
    else:
        return "Poor"


def render():
    st.title("📊 Results Dashboard")
    
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
        st.session_state.analysis_result = None
        st.session_state.rewritten_text = ""
        st.session_state.finalized_text = ""
        st.session_state.agent_conversation = []
    
    if not st.session_state.analysis_complete or st.session_state.analysis_result is None:
        st.warning("⚠️ No analysis data available. Please go to 'Home' and run an analysis first.")
        return
    
    st.divider()
    
    dash_col, side_col = st.columns(DASHBOARD_COLUMN_RATIO, gap=DASHBOARD_COLUMN_GAP)
    
    with dash_col:
        st.subheader("📊 ATS Analytics Dashboard")
        result = st.session_state.analysis_result
        
        m1, m2, m3, m4 = st.columns(4)
        
        overall_color = get_score_color(result.scores.overall)
        overall_rating = get_score_rating(result.scores.overall)
        m1.metric(
            "Overall Match",
            f"{result.scores.overall}/100",
            f"{overall_rating}",
            delta_color="off"
        )
        
        ats_color = get_score_color(result.resume_vs_job.ats_safety_score)
        ats_rating = get_score_rating(result.resume_vs_job.ats_safety_score)
        m2.metric(
            "ATS Safety",
            f"{result.resume_vs_job.ats_safety_score}/100",
            f"{ats_rating}",
            delta_color="off"
        )
        
        impact_color = get_score_color(result.scores.impact_quality)
        impact_rating = get_score_rating(result.scores.impact_quality)
        m3.metric(
            "Impact Quality",
            f"{result.scores.impact_quality}/100",
            f"{impact_rating}",
            delta_color="off"
        )
        
        m4.metric(
            "Keyword Density",
            f"{result.scores.keyword_density}%",
            delta_color="off"
        )
        
        st.markdown("##### Performance Breakdown")
        chart_data = pd.DataFrame({
            "Metric": ["Structure", "Clarity", "ATS Match", "Impact"],
            "Score": [
                result.scores.structure,
                result.scores.clarity,
                result.scores.ats_match,
                result.scores.impact_quality
            ]
        }).set_index("Metric")
        st.bar_chart(chart_data, y="Score", use_container_width=True, height=CHART_HEIGHT)

        with st.expander("🧐 Score Explanations", expanded=False):
            st.markdown(f"**ATS Match:** {result.score_breakdown.ats_match}")
            st.markdown(f"**Keyword Density:** {result.score_breakdown.keyword_density}")
            st.markdown(f"**Impact Quality:** {result.score_breakdown.impact_quality}")
            st.markdown(f"**Clarity:** {result.score_breakdown.clarity}")
            st.markdown(f"**Structure:** {result.score_breakdown.structure}")
        
        with st.expander("⚠️ Critical ATS Warnings & Actions", expanded=True):
            if result.comprehensive_feedback.immediate_actions:
                for action in result.comprehensive_feedback.immediate_actions:
                    st.warning(action, icon="🚨")
            else:
                st.success("No critical issues found!", icon="✅")
    
    with side_col:
        
        # AI Conversation Viewer
        with st.expander("🤖 AI Agent Conversation", expanded=True):
            st.caption("Review the thinking process and edits made by AI agents")
            if st.session_state.agent_conversation:
                for msg in st.session_state.agent_conversation:
                    st.markdown(msg["message"])
            else:
                st.info("No conversation available")
        
        # Export Center
        with st.expander("📥 Export Center", expanded=False):
            st.caption("Download your analysis report with improvements.")
            
            pdf_report_bytes = ExportService.generate_analysis_report_pdf(
                st.session_state.analysis_result,
                improved_resume_text=st.session_state.rewritten_text
            )

            st.download_button(
                label="📄 Download Detailed PDF Report",
                data=pdf_report_bytes.getvalue(),
                file_name="Resume_Analysis_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
    
    # ========================================================================
    # Before & After Comparison Section - Feature Flag
    # ========================================================================
    if SHOW_BEFORE_AFTER_COMPARISON:
        st.divider()
        st.subheader("📋 Before & After Comparison")
        st.caption("Original resume vs. AI-improved version with agent edits")
        
        comp_col1, comp_col2 = st.columns(2)
        
        with comp_col1:
            st.markdown("### 📄 Original Resume")
            st.text_area(
                "Original resume content:",
                value=st.session_state.raw_text,
                height=400,
                disabled=True,
                key="original_resume_view"
            )
        
        with comp_col2:
            st.markdown("### ✨ Improved Resume")
            st.text_area(
                "AI-improved resume with agent edits:",
                value=st.session_state.rewritten_text,
                height=400,
                disabled=True,
                key="improved_resume_view"
            )