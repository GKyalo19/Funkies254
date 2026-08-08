"""
A single, predictable JSON error shape for every API error.

Without this, DRF returns different shapes for validation errors (dict of
field -> [messages]) vs. permission/auth errors (a single "detail" string).
The frontend would need special-case handling for each. Instead, everything
gets normalised to:

    { "error": { "message": "...", "fields": {...} | null } }
"""
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    fields = None
    if isinstance(data, dict) and "detail" not in data:
        # Validation errors come back as {"field": ["msg"], ...}
        fields = data
        message = "Please fix the highlighted fields and try again."
    elif isinstance(data, dict) and "detail" in data:
        message = str(data["detail"])
    else:
        message = "Something went wrong."

    response.data = {"error": {"message": message, "fields": fields}}
    return response
