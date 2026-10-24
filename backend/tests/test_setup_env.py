from dotenv import dotenv_values

from app.setup_env import setup_env


def test_setup_generates_private_key_and_is_repeatable(tmp_path):
    (tmp_path / ".env.example").write_text("GOOGLE_CLIENT_ID=shared-client\nAUTH_SECRET_KEY=\n")
    setup_env(tmp_path)
    first = dotenv_values(tmp_path / ".env")
    assert first["GOOGLE_CLIENT_ID"] == "shared-client"
    assert len(first["AUTH_SECRET_KEY"]) >= 32
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    setup_env(tmp_path)
    assert dotenv_values(tmp_path / ".env") == first
    # Each developer receives a different signing key.
    other = tmp_path / "another-developer"
    other.mkdir()
    (other / ".env.example").write_text((tmp_path / ".env.example").read_text())
    setup_env(other)
    assert dotenv_values(other / ".env")["AUTH_SECRET_KEY"] != first["AUTH_SECRET_KEY"]


def test_setup_preserves_existing_settings_and_fills_empty_client_id(tmp_path):
    (tmp_path / ".env.example").write_text("GOOGLE_CLIENT_ID=shared-client\nAUTH_SECRET_KEY=\n")
    existing = "# Local settings\nPOSTGRES_PASSWORD=keep-me\nAUTH_SECRET_KEY=keep-this-key\nGOOGLE_CLIENT_ID=\n"
    (tmp_path / ".env").write_text(existing)
    setup_env(tmp_path)
    values = dotenv_values(tmp_path / ".env")
    assert values["POSTGRES_PASSWORD"] == "keep-me"
    assert values["AUTH_SECRET_KEY"] == "keep-this-key"
    assert values["GOOGLE_CLIENT_ID"] == "shared-client"
    assert "# Local settings" in (tmp_path / ".env").read_text()
    (tmp_path / ".env").write_text("GOOGLE_CLIENT_ID=custom-client\nAUTH_SECRET_KEY=keep-this-key\n")
    setup_env(tmp_path)
    assert dotenv_values(tmp_path / ".env")["GOOGLE_CLIENT_ID"] == "custom-client"
