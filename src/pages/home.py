import streamlit as st

def render():

    st.title("Resume Reviewer Pro")


    col1,col2 = st.columns(2)
    with col1:
        st.caption("A fully customisable AI powered resume reviewing platform")
        st.file_uploader("Upload your resume here:",accept_multiple_files=False,max_upload_size=5,type="pdf") 
        pass
    with col2:
        st.image("res/home_resume_image.jpg",
                width=400,
                caption="Helo sur! Plix no reject me",
                )
        
