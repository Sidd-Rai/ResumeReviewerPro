import streamlit as st
import re

from src.services.pdf_service import PDFService
from src.services.gemini_service import MultiAgentResumeService
from src.services.analysis_engine import AnalysisEngine
from src.config.settings import (
    IMAGE_WIDTH,
    TEXT_AREA_HEIGHT,
    HOME_PAGE_IMAGE_CAPTION,
    ALLOWED_FILE_TYPES,
    FILE_UPLOAD_MAX_SIZE_MB
)


def render():
    st.title("Resume Reviewer Pro")
    st.caption("A fully customisable AI powered resume reviewing platform")
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your resume here:",
            type=ALLOWED_FILE_TYPES,
            max_upload_size=FILE_UPLOAD_MAX_SIZE_MB,
            accept_multiple_files=False
        )
        job_desc = st.text_area(
            "Target Job Description",
            height=TEXT_AREA_HEIGHT
        )
        analyze_btn = st.button("Submit Resume", type="primary", use_container_width=True)
    with col2:
        st.image("res/home_resume_image.jpg",
                width=IMAGE_WIDTH,
                caption=HOME_PAGE_IMAGE_CAPTION
                )
    
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
        st.session_state.raw_text = ""
        st.session_state.rewritten_text = ""
        st.session_state.analysis_result = None
        st.session_state.finalized_text = ""
              
    if analyze_btn and uploaded_file:
        try:
            st.session_state.raw_text = PDFService.extract_and_preprocess_text(uploaded_file.read())
            
            with st.status("Engine 1: Running Deep ATS & Content Analysis...", expanded=True) as status1:
                analyzer = AnalysisEngine()
                st.session_state.analysis_result = analyzer.analyze_resume(
                    resume_text=st.session_state.raw_text,
                    job_description=job_desc
                )
                status1.update(label="Analysis Engine Complete!", state="complete")
                
            with st.status("Engine 2: Initializing Multi-Agent Editors...", expanded=True) as status2:
                agent_system = MultiAgentResumeService()
                response_stream = agent_system.stream_pipeline(st.session_state.raw_text, job_desc)
                
                placeholder = st.empty()
                full_text = ""
                for chunk in response_stream:
                    full_text += chunk.text
                    placeholder.markdown(full_text)
                    
                clean_rewrite = re.sub(r'```json\s*\{.*?\}\s*```', '', full_text, flags=re.DOTALL)
                st.session_state.rewritten_text = clean_rewrite.strip()
                st.session_state.finalized_text = st.session_state.rewritten_text
                
                status2.update(label="Multi-Agent Rewriting Complete!", state="complete")
                
            st.session_state.analysis_complete = True
            st.success("Analysis complete! Navigate to 'Results' to view your dashboard.")
            
        except Exception as e:
            st.error(f"Pipeline Error: {e}")
    
    if not st.session_state.analysis_complete:
        st.info("Use the sidebar to navigate")