import os
import subprocess
import keyring
import keyring.errors


def get_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    try:
        token = keyring.get_password("rv", "github")
        if token:
            return token
    except (keyring.errors.NoKeyringError, keyring.errors.KeyringError):
        pass

    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    raise ValueError("no GitHub token found; run `rv auth login` or set GITHUB_TOKEN")


def login(token: str) -> None:
    try:
        keyring.set_password("rv", "github", token)
    except (keyring.errors.NoKeyringError, keyring.errors.KeyringError) as e:
        raise ValueError(f"Could not store token in keyring: {e}")


def logout() -> None:
    try:
        keyring.delete_password("rv", "github")
    except (keyring.errors.NoKeyringError, keyring.errors.KeyringError):
        pass


def auth_status() -> dict:
    try:
        token = keyring.get_password("rv", "github")
        if token:
            return {
                "source": "keyring",
                "has_token": True,
                "mechanism": "system keyring",
            }
    except (keyring.errors.NoKeyringError, keyring.errors.KeyringError):
        pass

    if os.getenv("GITHUB_TOKEN"):
        return {
            "source": "env",
            "has_token": True,
            "mechanism": "$GITHUB_TOKEN env var",
        }

    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode == 0:
        return {
            "source": "gh",
            "has_token": True,
            "mechanism": "gh CLI (gh auth token)",
        }

    return {"source": None, "has_token": False, "mechanism": None}
