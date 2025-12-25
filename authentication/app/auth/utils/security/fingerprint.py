import hashlib

# To generate a session fingerprint, to detect token theft and bind sessions to specific devices

def generate_fingerprint(
    user_agent: str,
    accept_language: str
) -> str:
    raw = f"{user_agent}|{accept_language}"
    return hashlib.sha256(raw.encode()).hexdigest()