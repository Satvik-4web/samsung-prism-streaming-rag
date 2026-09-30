import os

from backend.config import Settings


def test_config_load() -> None:
    os.environ["ENVIRONMENT"] = "test"
    settings = Settings.load()
    assert settings.environment == "test"
    del os.environ["ENVIRONMENT"]
