import json
import re
from google.genai import types
from src.config.settings import PARSER_MODEL, CRITIC_MODEL, EDITOR_MODEL
from src.services.gemini_runtime import get_gemini_client, get_prompt_cache_name

class MultiAgentResumeService:
    def __init__(self):
        self.client = get_gemini_client()
        self._init_agent_chats()

    def _init_agent_chats(self):
        """Spins up persistent conversation histories for each independent role."""

        parser_system_instruction = (
            "You are a strict, objective Data Parsing Agent. Your single role is to accept "
            "raw text inputs and perfectly format them into standard Resume sections "
            "using valid, minified JSON format. Do not add summaries, conversational fluff, or prose outside the JSON."
        )
        critic_system_instruction = (
            "You are an elite, demanding ATS Audit Engine and Resume Critic matching ResumeWorded metrics.\n"
            "Grade every work statement using Google's XYZ rule (Action - Impact - Outcome).\n"
            "Calculate 4 specific core scores from 0-100:\n"
            "1. impact: Quantifiable results and strong action verbs.\n"
            "2. brevity: Length, word density, and filler reduction.\n"
            "3. style: Overused corporate clichés, formatting bugs, and structural flaws.\n"
            "4. skills: Core industry skill presence.\n\n"
            "Always output a valid structural JSON block containing these exact score fields wrapped inside ```json ... ``` blocks at the end of your response."
        )
        editor_system_instruction = (
            "You are a Master Executive Resume Writer. Your task is to accept structural "
            "critique details and rewrite every weak, unquantified profile point. Inject compelling "
            "vocabulary, isolate real impact metrics, and enforce readability without inventing artificial job facts."
        )

        parser_cache = get_prompt_cache_name(
            model=PARSER_MODEL,
            display_name="resume-parser-system",
            system_instruction=parser_system_instruction,
        )
        critic_cache = get_prompt_cache_name(
            model=CRITIC_MODEL,
            display_name="resume-critic-system",
            system_instruction=critic_system_instruction,
        )
        editor_cache = get_prompt_cache_name(
            model=EDITOR_MODEL,
            display_name="resume-editor-system",
            system_instruction=editor_system_instruction,
        )

        # AGENT 1: THE STRUCTURAL PARSER
        self.parser_chat = self.client.chats.create(
            model=PARSER_MODEL,
            config=types.GenerateContentConfig(
                cached_content=parser_cache,
                temperature=0.0,
                response_mime_type="application/json"
            )
        )

        # AGENT 2: THE ATS BENCHMARK CRITIC
        self.critic_chat = self.client.chats.create(
            model=CRITIC_MODEL,
            config=types.GenerateContentConfig(
                cached_content=critic_cache,
                temperature=0.0
            )
        )

        # AGENT 3: THE STRATEGIC REWRITE EDITOR
        self.editor_chat = self.client.chats.create(
            model=EDITOR_MODEL,
            config=types.GenerateContentConfig(
                cached_content=editor_cache,
                temperature=0.4
            )
        )

    def stream_pipeline(self, raw_resume_text: str, job_description: str = ""):
        """Executes a linear, stateful chain-of-thought pipeline passing historical metrics between agents."""
        
        # Phase 1: Structuring
        parser_prompt = f"Convert the following raw text into structured profile JSON:\n\n{raw_resume_text}"
        parsed_json_str = self.parser_chat.send_message(parser_prompt).text
        
        # Phase 2: Auditing & Scoring
        critic_prompt = (
            f"Run a complete metric analysis. Evaluate this against the target profile metrics.\n"
            f"Target Context/Job Desc: {job_description if job_description else 'General Industry Metrics'}\n\n"
            f"Profile Structure:\n{parsed_json_str}"
        )
        critique_results = self.critic_chat.send_message(critic_prompt).text
        
        # Phase 3: Fixing & Rewriting
        editor_prompt = (
            f"Take the raw components and fully rewrite the resume layout fixing all vulnerabilities "
            f"highlighted by the Critic.\n\nCritique Data:\n{critique_results}\n\nOriginal Structure:\n{parsed_json_str}"
        )
        editor_rewrites = self.editor_chat.send_message(editor_prompt).text
        
        # Phase 4: Self-Correction Loop (Critic audits the Editor's fixes)
        loop_prompt = (
            f"Verify and audit the Editor's new fixes. Provide a brief summary of what improved, "
            f"and return the updated ResumeWorded score dictionary inside a clean markdown code block at the absolute end.\n\n"
            f"Editor's Updates:\n{editor_rewrites}"
        )
        
        # Return the active stream of the evaluation summary and finalized scores
        return self.critic_chat.send_message_stream(loop_prompt)
