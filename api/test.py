"""Minimal test endpoint to verify Python functions work on Vercel."""

import sys
from typing import Any, Dict


def handler(req: Any) -> Dict[str, Any]:
    """
    Minimal test handler that doesn't import anything.
    
    Args:
        req: Vercel request object.
    
    Returns:
        HTTP response dictionary.
    """
    try:
        # Print to stderr (captured by Vercel)
        print("Test endpoint called!", file=sys.stderr)
        print(f"Request type: {type(req)}", file=sys.stderr)
        
        return {
            "statusCode": 200,
            "body": "OK - Python function is working",
        }
    except Exception as e:
        print(f"Error in test handler: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}",
        }

