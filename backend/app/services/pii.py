from __future__ import annotations


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    user, domain = email.split("@", 1)
    if len(user) <= 2:
        masked_user = "*" * len(user)
    else:
        masked_user = f"{user[0]}***{user[-1]}"
    return f"{masked_user}@{domain}"


def mask_card_last4(last4: str) -> str:
    safe = (last4 or "")[-4:]
    return f"****{safe}" if safe else "****"


def sanitize_payload(payload):
    if isinstance(payload, dict):
        masked: dict = {}
        for key, value in payload.items():
            lower_key = key.lower()
            if "email" in lower_key and isinstance(value, str):
                masked[key] = mask_email(value)
            elif "card" in lower_key and isinstance(value, str):
                masked[key] = mask_card_last4(value)
            else:
                masked[key] = sanitize_payload(value)
        return masked
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload
