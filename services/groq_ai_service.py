"""
Groq AI Service for error analysis.
Provides intelligent error diagnostics using Groq's LLM API.
"""

import os
import json
import logging
from typing import Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)


class GroqAIService:
    """Service for AI-powered error analysis using Groq API."""

    def __init__(self):
        """Initialize Groq client with API key from environment."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama3-8b-8192"
        self.temperature = 0.3

    def analyzeError(self, errorMessage: str) -> Dict[str, str]:
        """
        Analyze an error message and return explanation, cause, and fix.
        
        Args:
            errorMessage: The error message or traceback to analyze
            
        Returns:
            Dictionary with keys: explanation, cause, fix
            
        Raises:
            ValueError: If GROQ_API_KEY is not set
            Exception: If API call fails (logged and returned in response)
        """
        if not errorMessage or not errorMessage.strip():
            return {
                "explanation": "No error message provided",
                "cause": "Empty or null error message",
                "fix": "Provide a valid error message to analyze"
            }

        try:
            prompt = self._build_prompt(errorMessage)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=500,
            )
            
            response_text = response.choices[0].message.content
            return self._parse_response(response_text)

        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            return {
                "explanation": "Error analysis unavailable",
                "cause": f"API error: {type(e).__name__}",
                "fix": "Check API key and try again"
            }

    def _build_prompt(self, errorMessage: str) -> str:
        """Build analysis prompt for Groq."""
        return f"""Analyze this error concisely and respond ONLY with valid JSON (no markdown, no extra text):

Error: {errorMessage}

Return JSON with these keys:
- explanation: What went wrong (1-2 sentences, technical)
- cause: Root cause (1-2 sentences)
- fix: How to fix it (1-2 sentences, practical)

JSON:"""

    def _parse_response(self, response_text: str) -> Dict[str, str]:
        """Extract JSON from Groq response."""
        try:
            # Find JSON in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                return {
                    "explanation": parsed.get("explanation", "").strip(),
                    "cause": parsed.get("cause", "").strip(),
                    "fix": parsed.get("fix", "").strip()
                }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Groq response: {e}")
        
        # Fallback response
        return {
            "explanation": response_text[:150],
            "cause": "Unable to parse AI response",
            "fix": "Check the explanation field for details"
        }
