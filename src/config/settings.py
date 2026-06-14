"""
Configuration settings.
"""

import os
import streamlit as st

# Application Settings
APP_VERSION = "3.0.0"
APP_NAME = "Resume Reviewer Pro"

# Gemini API Key
GEMINI_API_KEY = st.secrets["KEY_SID1"]

# ---------------------------------------------------------
# MULTI-AGENT MODEL ROUTING
# ---------------------------------------------------------
PARSER_MODEL = (
    st.secrets.get("PARSER_MODEL")
    or "gemini-3.1-flash-lite"
)

CRITIC_MODEL = (
    st.secrets.get("PARSER_MODEL")
    or "gemini-3.1-flash-lite"
)

EDITOR_MODEL = (
    st.secrets.get("PARSER_MODEL")
    or "gemini-3.1-flash-lite"
)


# ---------------------------------------------------------
# ANALYSIS & VALIDATION LIMITS
# ---------------------------------------------------------
MAX_RESUME_LENGTH = 2000
MAX_JOB_DESCRIPTION_LENGTH = 5000
MIN_RESUME_LENGTH = 500

# Job Description Validation
MIN_JOB_DESCRIPTION_LENGTH = 50  # Minimum meaningful JD length
MIN_JOB_DESCRIPTION_WORDS = 10   # Minimum word count
JOB_DESC_RELEVANCE_THRESHOLD = 0.3  # If relevance below this, cap overall score

# ---------------------------------------------------------
# SCORING CONFIGURATION
# ---------------------------------------------------------
# Score weights - Job match primary, resume quality secondary
SCORE_WEIGHTS_NEW = {
    "ats_score": 0.50,              # 50% - ATS/keyword match with JD
    "keyword_density": 0.30,         # 30% - Keyword overlap
    "resume_quality": 0.20           # 20% - Resume quality (impact, clarity, structure)
}

# Resume quality sub-components (within 20%)
RESUME_QUALITY_WEIGHTS = {
    "impact": 0.50,
    "clarity": 0.30,
    "structure": 0.20
}

# Score multipliers for invalid JD
JD_VALIDITY_PENALTY = {
    "invalid_jd_multiplier": 0.30,      # If JD is gibberish, cap scores at 30% max
    "low_relevance_multiplier": 0.60    # If JD is low relevance, cap at 60% max
}

# Score thresholds
SCORE_THRESHOLDS = {
    "excellent": 85,
    "good": 70,
    "fair": 50,
    "poor": 0,
}

# Color scheme for data and metrics visualization
COLORS = {
    "excellent": "#27ae60",
    "good": "#3498db",
    "fair": "#f39c12",
    "poor": "#e74c3c",
    "primary": "#2c3e50",
    "secondary": "#34495e",
}

# ---------------------------------------------------------
# UI CONFIGURATION & STYLING
# ---------------------------------------------------------
# File Upload Configuration
FILE_UPLOAD_MAX_SIZE_MB = 5
ALLOWED_FILE_TYPES = ["pdf"]

# UI Dimensions and Layout
IMAGE_WIDTH = 400
TEXT_AREA_HEIGHT = 250
TEXT_AREA_EDITOR_HEIGHT = 450
CHART_HEIGHT = 250
DASHBOARD_COLUMN_RATIO = [1.2, 1]
DASHBOARD_COLUMN_GAP = "large"

# UI Text
HOME_PAGE_IMAGE_CAPTION = "Helo sur! Plix no reject me 🥺🥺🥺"

# ---------------------------------------------------------
# EXPORT CONFIGURATION
# ---------------------------------------------------------
EXPORT_FORMATS = ["PDF Report", "Improved Resume (DOCX)", "Comparison PDF"]