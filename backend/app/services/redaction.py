import re

# Regex patterns matching API keys, Bearer tokens, passwords, authorization headers, and connection strings
SECRET_PATTERNS = [
    (r"(bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1[REDACTED]"),
    (r"(api[_-]?key\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]+['\"]?", r"\1[REDACTED]"),
    (r"(password\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]+['\"]?", r"\1[REDACTED]"),
    (r"(authorization\s*:\s*bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1[REDACTED]"),
    (r"(postgresql://)[a-zA-Z0-9_]+:[a-zA-Z0-9_]+(@[a-zA-Z0-9_\-\.]+:\d+/[a-zA-Z0-9_]+)", r"\1[REDACTED]:[REDACTED]\2")
]

def redact_secrets(text: str) -> str:
    """
    Scans log text and replaces secret matches with redactor flags.
    """
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted
