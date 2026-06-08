import streamlit as st
import pandas as pd

from src.services.export_service import ExportService
from src.config.settings import (
    CHART_HEIGHT,
    TEXT_AREA_EDITOR_HEIGHT,
    DASHBOARD_COLUMN_RATIO,
    DASHBOARD_COLUMN_GAP,
)


def render():
    st.title("📊 Results Dashboard")
    
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
        st.session_state.analysis_result = None
        st.session_state.rewritten_text = ""
        st.session_state.finalized_text = ""
    
    if not st.session_state.analysis_complete or st.session_state.analysis_result is None:
        st.warning("⚠️ No analysis data available. Please go to 'Home' and run an analysis first.")
        return
    
    st.divider()
    
    dash_col, editor_col = st.columns(DASHBOARD_COLUMN_RATIO, gap=DASHBOARD_COLUMN_GAP)
    
    with dash_col:
        st.subheader("📊 ATS Analytics Dashboard")
        result = st.session_state.analysis_result
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall Match", f"{result.scores.overall}/100")
        m2.metric("ATS Safety", f"{result.resume_vs_job.ats_safety_score}/100")
        m3.metric("Impact Quality", f"{result.scores.impact_quality}/100")
        m4.metric("Keyword Density", f"{result.scores.keyword_density}%")
        
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
            for action in result.comprehensive_feedback.immediate_actions:
                st.warning(action, icon="🚨")
    
    with editor_col:
        
        with st.expander("📝 Editor Workspace", expanded=True):
            st.session_state.finalized_text = st.text_area(
                "Review and finalize your newly optimized resume content below:",
                value=st.session_state.rewritten_text,
                height=TEXT_AREA_EDITOR_HEIGHT
            )
        
        with st.expander("📥 Export Center", expanded=False):
            st.caption("Generate your final files using the updated analysis data.")
            
            pdf_report_bytes = ExportService.generate_analysis_report_pdf(st.session_state.analysis_result)
            
            docx_bytes = ExportService.generate_improved_resume_docx(
                original_resume_text=st.session_state.raw_text,
                analysis=st.session_state.analysis_result,
                improvements_only=False
            )

            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                st.download_button(
                    label="📄 Download Detailed PDF Report",
                    data=pdf_report_bytes.getvalue(),
                    file_name="Resume_Analysis_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
                
            with ex_col2:
                st.download_button(
                    label="📝 Download Word (.docx)",
                    data=docx_bytes.getvalue(),
                    file_name="Optimized_Resume.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )