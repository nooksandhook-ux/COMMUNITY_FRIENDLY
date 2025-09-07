# nooks/utils/__init__.py
def sanitize_input(text, max_length):
    """Sanitize input text and enforce max length"""
    if not isinstance(text, str):
        return ""
    return text.strip()[:max_length]
