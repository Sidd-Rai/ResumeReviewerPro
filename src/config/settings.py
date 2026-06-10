"""
Configuration settings.
"""

import os

# Application Settings
APP_VERSION = "3.0.0"
APP_NAME = "Resume Reviewer Pro"

# Gemini API Key
GEMINI_API_KEY = os.getenv("KEY_SID1")
GEMINI_API_KEY = os.getenv("KEY_SID2")

# ---------------------------------------------------------
# MULTI-AGENT MODEL ROUTING
# ---------------------------------------------------------
# 1. The Parser: Fast, deterministic JSON structural extraction
PARSER_MODEL = os.getenv("PARSER_MODEL", "gemini-3.1-flash-lite")

# 2. The Critic: Deep analytical reasoning for metric calculations and AIO grading
CRITIC_MODEL = os.getenv("CRITIC_MODEL", "gemini-3.1-flash-lite")

# 3. The Editor: High-tier creative professional writing and context alignment
EDITOR_MODEL = os.getenv("EDITOR_MODEL", "gemini-3.1-flash-lite")


# ---------------------------------------------------------
# UI CONFIGURATION & STYLING
# ---------------------------------------------------------
MAIN_CONTENT_PADDING = 2

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

# Color scheme for data and metrics visualization
COLORS = {
    "excellent": "#27ae60",
    "good": "#3498db",
    "fair": "#f39c12",
    "poor": "#e74c3c",
    "primary": "#2c3e50",
    "secondary": "#34495e",
}

# Scoring thresholds
SCORE_THRESHOLDS = {
    "excellent": 85,
    "good": 70,
    "fair": 50,
    "poor": 0,
}

# ---------------------------------------------------------
# SCORE FACTORS (ResumeWorded Benchmarks)
# ---------------------------------------------------------
SCORE_FACTOR_MULTIPLEERS = {
    "ats_score_multiplier" : 0.40,
    "kw_density_multiplier" : 0.20,
    "impact_multiplier":0.20,
    "clarity_multiplier": 0.10,
    "structure_score_multiplier": 0.10
}
