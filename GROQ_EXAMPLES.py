"""
Groq Error Analysis - Quick Examples
Shows how to use the error analyzer in your code
"""

# ==============================================================================
# EXAMPLE 1: Basic Service Usage
# ==============================================================================

from services.groq_ai_service import GroqAIService

def example_1_basic_service():
    """Direct service class usage."""
    service = GroqAIService()
    
    error = "TypeError: Cannot read property 'name' of undefined"
    result = service.analyzeError(error)
    
    print("EXPLANATION:", result['explanation'])
    print("CAUSE:", result['cause'])
    print("FIX:", result['fix'])


# ==============================================================================
# EXAMPLE 2: Utility Function (Recommended)
# ==============================================================================

from utils.error_analyzer import analyze_error

def example_2_utility_function():
    """Simple utility function - recommended for most cases."""
    errors = [
        "ConnectionError: Failed to establish database connection",
        "ValueError: Invalid input format",
        "RuntimeError: Out of memory"
    ]
    
    for error in errors:
        print(f"\n--- Analyzing: {error} ---")
        result = analyze_error(error)
        print(f"Explanation: {result['explanation']}")
        print(f"Cause: {result['cause']}")
        print(f"Fix: {result['fix']}")


# ==============================================================================
# EXAMPLE 3: Safe Utility (Never Fails)
# ==============================================================================

from utils.error_analyzer import get_error_analysis_safe

def example_3_safe_utility():
    """Safe version - never throws exceptions."""
    result = get_error_analysis_safe("Any error here")
    
    # Always returns valid dict, even if service is down
    print(result['explanation'])
    print(result['cause'])
    print(result['fix'])


# ==============================================================================
# EXAMPLE 4: In Exception Handler
# ==============================================================================

from utils.error_analyzer import analyze_error

def example_4_exception_handler():
    """Use in try/except blocks."""
    try:
        # Some code that might fail
        x = int("not a number")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        analysis = analyze_error(error_msg)
        
        print("Error:", error_msg)
        print("What happened:", analysis['explanation'])
        print("Why it happened:", analysis['cause'])
        print("How to fix:", analysis['fix'])


# ==============================================================================
# EXAMPLE 5: In Flask Route Handler
# ==============================================================================

from flask import Flask, jsonify, request
from utils.error_analyzer import get_error_analysis_safe

app = Flask(__name__)

@app.route("/api/process", methods=["POST"])
def process_data():
    """API endpoint with error analysis."""
    try:
        data = request.json
        # Process data...
        return jsonify({"success": True})
    except Exception as e:
        # Analyze the error
        analysis = get_error_analysis_safe(str(e))
        
        return jsonify({
            "success": False,
            "error": str(e),
            "explanation": analysis['explanation'],
            "cause": analysis['cause'],
            "fix": analysis['fix']
        }), 500


# ==============================================================================
# EXAMPLE 6: REST API Call
# ==============================================================================

import requests
import json

def example_6_rest_api():
    """Call the error analysis REST API directly."""
    
    # Single error analysis
    response = requests.post(
        "http://localhost:5000/api/errors/analyze",
        json={"message": "TypeError: undefined is not a function"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Explanation:", result['explanation'])
        print("Cause:", result['cause'])
        print("Fix:", result['fix'])
    else:
        print("Error:", response.json())
    
    # Batch analysis
    response = requests.post(
        "http://localhost:5000/api/errors/batch",
        json={
            "errors": [
                "TypeError: x is not defined",
                "ValueError: invalid literal",
                "RuntimeError: system call failed"
            ]
        }
    )
    
    if response.status_code == 200:
        results = response.json()['results']
        for result in results:
            print(f"\n{result['message']}")
            print(f"Fix: {result['fix']}")


# ==============================================================================
# EXAMPLE 7: Health Check
# ==============================================================================

import requests

def example_7_health_check():
    """Check if error analysis service is available."""
    response = requests.get("http://localhost:5000/api/errors/health")
    
    if response.status_code == 200:
        health = response.json()
        print(f"Status: {health['status']}")
        print(f"Service: {health['service']}")
        print(f"Model: {health['model']}")
    else:
        print("Service unavailable")


# ==============================================================================
# EXAMPLE 8: Logging Analysis Results
# ==============================================================================

import logging
from utils.error_analyzer import get_error_analysis_safe

logger = logging.getLogger(__name__)

def example_8_logging():
    """Log error analysis for debugging."""
    try:
        # Code that might fail
        data = None
        value = data['key']  # Will raise TypeError
    except Exception as e:
        analysis = get_error_analysis_safe(str(e))
        
        logger.error({
            "error_type": type(e).__name__,
            "error_message": str(e),
            "ai_explanation": analysis['explanation'],
            "ai_cause": analysis['cause'],
            "ai_fix": analysis['fix']
        })


# ==============================================================================
# EXAMPLE 9: Database Error Analysis
# ==============================================================================

from utils.error_analyzer import analyze_error

def example_9_database_errors():
    """Analyze database connection errors."""
    db_errors = [
        "psycopg2.OperationalError: FATAL: database does not exist",
        "pymongo.errors.ServerSelectionTimeoutError: No servers found",
        "sqlite3.OperationalError: database is locked"
    ]
    
    for error in db_errors:
        analysis = analyze_error(error)
        print(f"\nDatabase Error: {error}")
        print(f"Quick Fix: {analysis['fix'][:100]}...")


# ==============================================================================
# EXAMPLE 10: Test Failure Analysis
# ==============================================================================

from utils.error_analyzer import analyze_error

def example_10_test_failures():
    """Analyze test failures."""
    test_errors = [
        "AssertionError: Expected True but got False",
        "TimeoutError: Test timed out after 30 seconds",
        "ConnectionRefusedError: Could not connect to test server"
    ]
    
    for error in test_errors:
        analysis = analyze_error(error)
        print(f"\nTest Failed: {error}")
        print(f"Why: {analysis['cause']}")
        print(f"Fix: {analysis['fix']}")


# ==============================================================================
# Running Examples
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("GROQ ERROR ANALYSIS - EXAMPLES")
    print("=" * 80)
    
    # Uncomment to run examples
    # example_1_basic_service()
    # example_2_utility_function()
    # example_3_safe_utility()
    # example_4_exception_handler()
    # example_5_flask_route()
    # example_7_health_check()
    # example_8_logging()
    # example_9_database_errors()
    # example_10_test_failures()
    
    print("\nSee GROQ_SETUP.md for complete documentation")
    print("Run individual examples by uncommenting them above")
