"""
Simple error analysis utility for use across the project.
Wraps GroqAIService for easy integration.
"""

import logging
from typing import Dict, Optional
from services.groq_ai_service import GroqAIService

logger = logging.getLogger(__name__)


def analyze_error(error_message: str) -> Dict[str, str]:
    """
    Analyze an error using Groq AI.
    
    Usage:
        from utils.error_analyzer import analyze_error
        result = analyze_error("TypeError: Cannot read property 'name' of undefined")
        print(result['explanation'])
        print(result['cause'])
        print(result['fix'])
    
    Args:
        error_message: The error to analyze
        
    Returns:
        Dict with keys: explanation, cause, fix
    """
    try:
        service = GroqAIService()
        return service.analyzeError(error_message)
    except ValueError as e:
        logger.error(f"Groq service initialization failed: {e}")
        return {
            "explanation": "Error analysis service not configured",
            "cause": "GROQ_API_KEY environment variable not set",
            "fix": "Set GROQ_API_KEY in environment variables"
        }
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        return {
            "explanation": "Error analysis failed",
            "cause": str(e),
            "fix": "Check logs for details"
        }


def get_error_analysis_safe(error_message: str, default: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Safely analyze error with fallback to default response.
    Never throws exceptions.
    
    Args:
        error_message: The error to analyze
        default: Optional default response if analysis fails
        
    Returns:
        Analysis result or default
    """
    try:
        return analyze_error(error_message)
    except Exception as e:
        logger.exception(f"Error analysis exception: {e}")
        if default is None:
            default = {
                "explanation": "Unable to analyze error",
                "cause": "Analysis service unavailable",
                "fix": "Please check error logs"
            }
        return default
