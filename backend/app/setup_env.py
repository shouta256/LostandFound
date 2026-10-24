"""Prepare local configuration without replacing existing credentials."""

from pathlib import Path
import secrets

from dotenv import dotenv_values, set_key

from app.database import PROJECT_ROOT


def setup_env(root: Path = PROJECT_ROOT) -> None:
    env_file = root / ".env"
    template = root / ".env.example"
    if not env_file.exists():
        env_file.write_text(template.read_text())
    env_file.chmod(0o600)
    values = dotenv_values(env_file)
    if not values.get("AUTH_SECRET_KEY"):
        set_key(env_file, "AUTH_SECRET_KEY", secrets.token_urlsafe(32))
        print("Generated a private local authentication key.")
    if not values.get("GOOGLE_CLIENT_ID"):
        shared_client_id = dotenv_values(template).get("GOOGLE_CLIENT_ID")
        if shared_client_id:
            set_key(env_file, "GOOGLE_CLIENT_ID", shared_client_id)
        else:
            print("Google login needs the shared development GOOGLE_CLIENT_ID in .env.example or .env.")
    print("Local .env is ready; existing settings were preserved.")


if __name__ == "__main__":
    setup_env()
