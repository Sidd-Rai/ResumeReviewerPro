import streamlit as st
import re

from src.services.pdf_service import PDFService
from src.services.gemini_service import MultiAgentResumeService
from src.analysis.analysis_engine import AnalysisEngine
from src.config.settings import (
    IMAGE_WIDTH,
    TEXT_AREA_HEIGHT,
    HOME_PAGE_IMAGE_CAPTION,
    ALLOWED_FILE_TYPES,
    FILE_UPLOAD_MAX_SIZE_MB
)


def _init_session_state():
    """Initialize session state variables if not present."""
    defaults = {
        "analysis_complete": False,
        "raw_text": "",
        "rewritten_text": "",
        "analysis_result": None,
        "finalized_text": "",
        "job_desc_input": "",
        "last_file_name": "",
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_analysis():
    """Clear analysis results when starting new analysis."""
    st.session_state.analysis_complete = False
    st.session_state.raw_text = ""
    st.session_state.rewritten_text = ""
    st.session_state.analysis_result = None
    st.session_state.finalized_text = ""
    st.session_state.last_file_name = ""


def render():
    _init_session_state()
    
    st.title("Resume Reviewer Pro")
    st.caption("A fully customisable AI powered resume reviewing platform")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Resume & Job Details")
        
        uploaded_file = st.file_uploader(
            "Upload your resume here:",
            type=ALLOWED_FILE_TYPES,
            max_upload_size=FILE_UPLOAD_MAX_SIZE_MB,
            accept_multiple_files=False
        )
        
        # Show last processed file
        if st.session_state.last_file_name:
            st.caption(f"Last processed: {st.session_state.last_file_name}")
        
        # Job description with session state preservation
        job_desc = st.text_area(
            "Target Job Description",
            value=st.session_state.job_desc_input,
            height=TEXT_AREA_HEIGHT,
            key="job_desc_area"
        )
        
        # Update session state when textarea changes
        st.session_state.job_desc_input = job_desc
        
        # Action buttons in columns
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            analyze_btn = st.button(
                "Submit Resume",
                type="primary",
                use_container_width=True,
                key="analyze_btn"
            )
        
        with btn_col2:
            clear_btn = st.button(
                "Clear Analysis",
                use_container_width=True,
                key="clear_btn"
            )
        
        if clear_btn:
            _clear_analysis()
            st.rerun()
    
    with col2:
        st.image(
            "res/home_resume_image.jpg",
            width=IMAGE_WIDTH,
            caption=HOME_PAGE_IMAGE_CAPTION
        )
    
    # ========================================================================
    # ANALYSIS FLOW
    # ========================================================================
    if analyze_btn and uploaded_file:
        try:
            # Extract resume text
            resume_text = PDFService.extract_and_preprocess_text(uploaded_file.read())
            
            # Validate resume
            if not resume_text or len(resume_text.strip()) < 100:
                st.error("❌ Resume extraction failed or too short. Please try another PDF.")
                return
            
            st.session_state.raw_text = resume_text
            st.session_state.last_file_name = uploaded_file.name
            
            # ================================================================
            # ENGINE 1: Deep ATS & Content Analysis
            # ================================================================
            with st.status("Engine 1: Running Deep ATS & Content Analysis...", expanded=True) as status1:
                try:
                    analyzer = AnalysisEngine()
                    st.session_state.analysis_result = analyzer.analyze_resume(
                        resume_text=st.session_state.raw_text,
                        job_description=job_desc
                    )
                    status1.update(label="✅ Analysis Engine Complete!", state="complete")
                except Exception as e:
                    status1.update(label="❌ Analysis Engine Failed", state="error")
                    # st.error(f"Analysis Error: {str(e)[:200]}")
                    raise
                    return
            
            # ================================================================
            # ENGINE 2: Multi-Agent Resume Editor
            # ================================================================
            with st.status("Engine 2: Initializing Multi-Agent Editors...", expanded=True) as status2:
                try:
                    agent_system = MultiAgentResumeService()
                    response_stream = agent_system.stream_pipeline(
                        st.session_state.raw_text,
                        job_desc
                    )
                    
                    placeholder = st.empty()
                    full_text = ""
                    
                    for chunk in response_stream:
                        full_text += chunk.text
                        placeholder.markdown(full_text)
                    
                    # Clean rewritten text
                    clean_rewrite = re.sub(
                        r'```json\s*\{.*?\}\s*```',
                        '',
                        full_text,
                        flags=re.DOTALL
                    )
                    st.session_state.rewritten_text = clean_rewrite.strip()
                    st.session_state.finalized_text = st.session_state.rewritten_text
                    
                    status2.update(label="✅ Multi-Agent Rewriting Complete!", state="complete")
                    
                except Exception as e:
                    status2.update(label="❌ Multi-Agent Processing Failed", state="error")
                    st.error(f"Editor Error: {str(e)[:200]}")
                    return
            
            # Analysis successful
            st.session_state.analysis_complete = True
            st.success(
                "✅ Analysis complete! Navigate to **'Results'** in the sidebar to view your dashboard."
            )
            
        except Exception as e:
            st.error(f"❌ Pipeline Error: {str(e)[:300]}")
            st.session_state.analysis_complete = False
    
    # Show info if no analysis run
    if not st.session_state.analysis_complete:
        st.info(
            "👈 **Start here:** Upload your resume, paste a job description (optional), and click 'Submit Resume' to begin analysis."
        )