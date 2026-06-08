import fitz  # PyMuPDF
import re

class PDFService:
    @staticmethod
    def extract_and_preprocess_text(pdf_bytes: bytes) -> str:
        """Extracts text from a PDF using PyMuPDF and cleanses it for LLM analysis."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        raw_text = ""
        
        # Pull text using layout blocks to preserve natural contextual proximity
        for page in doc:
            blocks = page.get_text("blocks")
            for block in blocks:
                raw_text += block[4] + "\n"
        
        return PDFService._preprocess_text(raw_text)

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """Removes zero-width characters, normalizes whitespace, and cleans up syntax."""
        if not text:
            return ""
        
        # Remove zero-width spaces and invisible unicode artifacts
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
        
        # Uniform bullet point representation
        text = re.sub(r'[\u2022\u00b7\u25cf\u25fe]', '* ', text)
        
        # Collapse multi-tabs and double horizontal spacing
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Clean up vertical excess while keeping paragraph separation clear
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        return text.strip()