from clipturbo_core.settings import AppSettings


def test_default_settings_are_stable() -> None:
    settings = AppSettings()

    assert settings.app_name == "clipturbo-api"
    assert settings.environment == "local"
