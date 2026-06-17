import streamlit as st
import re
import hashlib
from src.services.pdf_service import PDFService
from src.services.gemini_service import MultiAgentResumeService
from src.analysis.analysis_engine import AnalysisEngine
from src.config.settings import (
    IMAGE_WIDTH,
    TEXT_AREA_HEIGHT,
    HOME_PAGE_IMAGE_CAPTION,
    ALLOWED_FILE_TYPES,
    FILE_UPLOAD_MAX_SIZE_MB,
    MIN_JOB_DESCRIPTION_LENGTH,
    MIN_JOB_DESCRIPTION_WORDS,
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
        "agent_conversation": [],
        "last_request_hash": "",  # For deduplication
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
    st.session_state.agent_conversation = []
    st.session_state.last_request_hash = ""


def _validate_job_description(job_desc: str) -> tuple[bool, str]:
    """Validate job description upfront."""
    if not job_desc:
        return True, ""  # Optional
    
    if len(job_desc.strip()) < MIN_JOB_DESCRIPTION_LENGTH:
        return False, f"Job description too short (minimum {MIN_JOB_DESCRIPTION_LENGTH} characters)"
    
    word_count = len(job_desc.split())
    if word_count < MIN_JOB_DESCRIPTION_WORDS:
        return False, f"Job description too short (minimum {MIN_JOB_DESCRIPTION_WORDS} words)"
    
    return True, ""


def _get_request_hash(resume_text: str, job_desc: str) -> str:
    """Create hash of resume + JD for deduplication."""
    combined = f"{resume_text}|||{job_desc}"
    return hashlib.md5(combined.encode()).hexdigest()


def _should_skip_analysis(current_hash: str) -> bool:
    """Check if this exact request was just analyzed (deduplication)."""
    return current_hash == st.session_state.last_request_hash and st.session_state.analysis_complete


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
            
            # Validate job description upfront
            jd_valid, jd_error = _validate_job_description(job_desc)
            if not jd_valid:
                st.error(f"❌ {jd_error}")
                return
            
            # Check for duplicate request (deduplication)
            request_hash = _get_request_hash(resume_text, job_desc)
            if _should_skip_analysis(request_hash):
                st.info("✅ This exact resume+JD combination was just analyzed. Showing previous results.")
                st.session_state.analysis_complete = True
                return
            
            st.session_state.raw_text = resume_text
            st.session_state.last_file_name = uploaded_file.name
            st.session_state.last_request_hash = request_hash
            
            # ================================================================
            # UNIFIED ENGINE: Single 4-call pipeline
            # ================================================================
            with st.status("🚀 Running unified analysis pipeline...", expanded=True) as status:
                try:
                    analyzer = AnalysisEngine()
                    analysis_result = analyzer.analyze_resume(
                        resume_text=st.session_state.raw_text,
                        job_description=job_desc
                    )
                    st.session_state.analysis_result = analysis_result
                    
                    # Extract pipeline result for streaming service
                    pipeline_result = analysis_result.pipeline_result
                    
                    status.update(label="✅ Analysis complete, formatting results...", state="running")
                    
                except Exception as e:
                    status.update(label="❌ Analysis failed", state="error")
                    st.error(f"Analysis Error: {str(e)[:200]}")
                    st.session_state.analysis_complete = False
                    return
            
            # ================================================================
            # STREAM FORMATTER: Format results for display
            # ================================================================
            with st.status("📊 Formatting results...", expanded=True) as status_format:
                try:
                    formatter = MultiAgentResumeService(pipeline_result=pipeline_result)
                    response_stream = formatter.stream_pipeline(
                        st.session_state.raw_text,
                        job_desc,
                        skip_pipeline=True
                    )
                    
                    placeholder = st.empty()
                    full_text = ""
                    conversation_log = []
                    
                    for chunk in response_stream:
                        full_text += chunk.text
                        placeholder.markdown(full_text)
                    
                    # Store conversation log
                    conversation_log.append({
                        "role": "agent",
                        "message": full_text
                    })
                    st.session_state.agent_conversation = conversation_log
                    
                    # Clean rewritten text
                    clean_rewrite = re.sub(
                        r'```json\s*\{.*?\}\s*```',
                        '',
                        full_text,
                        flags=re.DOTALL
                    )
                    st.session_state.rewritten_text = clean_rewrite.strip()
                    st.session_state.finalized_text = st.session_state.rewritten_text
                    
                    status_format.update(label="✅ Results ready!", state="complete")
                    
                except Exception as e:
                    status_format.update(label="❌ Formatting failed", state="error")
                    st.error(f"Formatter Error: {str(e)[:200]}")
                    st.session_state.analysis_complete = False
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
