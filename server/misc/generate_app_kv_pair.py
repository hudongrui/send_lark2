import secrets
import string

def generate_app_credentials(
    app_id_prefix: str = "app-",
    app_id_suffix_length: int = 16,
    app_key_length: int = 32
) -> tuple[str, str]:
    """
    Generates secure app-id (with prefix) and alphanumeric-only app-key.

    Args:
        app_id_prefix: Prefix for the app-id (default: "app-").
        app_id_suffix_length: Length of the random suffix for app-id (default: 16).
        app_key_length: Length of the generated app-key (default: 32).

    Returns:
        Tuple of (app_id, app_key)
    """
    # Generate app-id: prefix + random hex string
    app_id_suffix = secrets.token_hex(app_id_suffix_length // 2)
    app_id = f"{app_id_prefix}{app_id_suffix}"

    # Generate app-key: alphanumeric only (upper/lower letters + numbers)
    allowed_chars = string.ascii_letters + string.digits  # Removed special characters
    app_key = "".join(secrets.choice(allowed_chars) for _ in range(app_key_length))

    return app_id, app_key

if __name__ == "__main__":
    app_id, app_key = generate_app_credentials()
    print(f"Generated App ID     | {app_id}")
    print(f"Generated App Secret | {app_key}")  # Now alphanumeric only
