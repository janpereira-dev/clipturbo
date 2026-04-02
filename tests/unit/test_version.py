from clipturbo_core.version import APP_NAME, APP_VERSION


def test_version_constants_are_defined() -> None:
    assert APP_NAME == "clipturbo-api"
    assert APP_VERSION == "0.1.0"
