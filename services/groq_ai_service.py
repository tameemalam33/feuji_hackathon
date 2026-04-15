"""
Groq AI Service for error explanation and analysis.
Integrates with Groq API to provide intelligent error diagnostics.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from groq import Groq

logger = logging.getLogger(__name__)


class GroqAIService:
    """Service for AI-powered error explanation using Groq API."""

    def __init__(self):
        """Initialize Groq client."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=api_key)
        self.model = "mixtral-8x7b-32768"  # Fast, capable model
        self.temperature = 0.3  # Lower temp for more consistent explanations

    def explain_error(self, error_message: str, error_type: str = None, context: str = None) -> Dict[str, Any]:
        """
        Generate AI explanation for an error using Groq.

        Args:
            error_message: The error message/traceback to analyze
            error_type: Type of error (e.g., 'TypeError', 'RuntimeError')
            context: Additional context about when/where error occurred

        Returns:
            Dictionary with explanation, cause, and suggested_fix
        """
        try:
            # Build the prompt
            prompt = self._build_error_analysis_prompt(error_message, error_type, context)

            # Call Groq API
            message = self.client.messages.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=1000,
            )

            response_text = message.content[0].text
            result = self._parse_ai_response(response_text, error_message, error_type)
            return result

        except Exception as e:
            logger.error(f"Error calling Groq API: {str(e)}")
            return {
                "explanation": "Unable to generate AI explanation at this time.",
                "cause": None,
                "suggested_fix": None,
                "raw_response": str(e),
                "model": self.model,
                "generated_at": datetime.utcnow().isoformat(),
                "error": True
            }

    def _build_error_analysis_prompt(self, error_message: str, error_type: str = None, context: str = None) -> str:
        """Build a detailed prompt for error analysis."""
        prompt = f"""Analyze this error and provide a concise, technical explanation.

Error Message:
{error_message}
"""
        if error_type:
            prompt += f"\nError Type: {error_type}"

        if context:
            prompt += f"\nContext: {context}"

        prompt += """

Please provide your response in JSON format with these exact keys:
{
  "explanation": "Brief, technical explanation of what went wrong (1-2 sentences)",
  "cause": "Root cause of the error (1-2 sentences)",
  "suggested_fix": "Practical steps to fix or prevent this error (1-2 sentences)"
}

Be specific and technical. Focus on actionable insights."""

        return prompt

    def _parse_ai_response(self, response_text: str, error_message: str, error_type: str) -> Dict[str, Any]:
        """Parse the AI response and extract structured data."""
        try:
            # Try to extract JSON from the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)

                return {
                    "explanation": parsed.get("explanation", ""),
                    "cause": parsed.get("cause", ""),
                    "suggested_fix": parsed.get("suggested_fix", ""),
                    "raw_response": response_text,
                    "model": self.model,
                    "generated_at": datetime.utcnow().isoformat(),
                }
            else:
                # Fallback if JSON parsing fails
                return {
                    "explanation": response_text[:200],
                    "cause": None,
                    "suggested_fix": None,
                    "raw_response": response_text,
                    "model": self.model,
                    "generated_at": datetime.utcnow().isoformat(),
                }

        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response as JSON")
            return {
                "explanation": response_text[:200],
                "cause": None,
                "suggested_fix": None,
                "raw_response": response_text,
                "model": self.model,
                "generated_at": datetime.utcnow().isoformat(),
            }

    def analyze_test_failure(self, test_name: str, failure_reason: str, stack_trace: str = None) -> Dict[str, Any]:
        """
        Analyze a test failure and provide debugging suggestions.

        Args:
            test_name: Name of the failing test
            failure_reason: Why the test failed
            stack_trace: Optional stack trace

        Returns:
            Analysis with explanation and fix suggestions
        """
        error_msg = f"Test '{test_name}' failed: {failure_reason}"
        if stack_trace:
            error_msg += f"\n\nStack trace:\n{stack_trace}"

        return self.explain_error(error_msg, error_type="TestFailure", context=f"Test: {test_name}")

    def analyze_performance_issue(self, metric: str, current_value: float, expected_value: float, details: str = None) -> Dict[str, Any]:
        """
        Analyze a performance issue.

        Args:
            metric: Performance metric name (e.g., 'response_time', 'memory_usage')
            current_value: Current measured value
            expected_value: Expected/threshold value
            details: Additional performance details

        Returns:
            Analysis with optimization suggestions
        """
        error_msg = f"Performance issue: {metric} is {current_value} (expected: {expected_value})"
        if details:
            error_msg += f"\nDetails: {details}"

        return self.explain_error(error_msg, error_type="PerformanceIssue", context=f"Metric: {metric}")

    def batch_explain_errors(self, errors: list) -> list:
        """
        Explain multiple errors in batch.

        Args:
            errors: List of dicts with 'message', 'type', and optional 'context'

        Returns:
            List of explanations
        """
        results = []
        for error in errors:
            result = self.explain_error(
                error.get("message", ""),
                error.get("type"),
                error.get("context")
            )
            results.append(result)

        return results
