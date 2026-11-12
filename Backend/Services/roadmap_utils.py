import hashlib


def logical_item_key(
    phase_number: int,
    skill_name: str,
    skill_uri: str | None,
) -> str:
    identity = (
        f"uri:{skill_uri.strip().casefold()}"
        if skill_uri and skill_uri.strip()
        else f"name:{skill_name.strip().casefold()}"
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"phase:{phase_number}:skill:{digest}"
