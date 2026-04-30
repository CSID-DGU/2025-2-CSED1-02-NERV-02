"""Smoke test — verifies the package can be imported and basic metadata is correct."""


def test_import():
    """패키지 import가 동작해야 한다."""
    import nerv_filter
    assert nerv_filter is not None


def test_version_format():
    """버전이 semantic versioning 형식이어야 한다."""
    import nerv_filter
    parts = nerv_filter.__version__.split(".")
    assert len(parts) == 3, f"Expected MAJOR.MINOR.PATCH, got {nerv_filter.__version__}"
    for part in parts:
        assert part.isdigit() or "-" in part, f"Invalid version part: {part}"


def test_version_is_alpha():
    """초기 알파 버전이어야 한다 (v0.x.x)."""
    import nerv_filter
    major = int(nerv_filter.__version__.split(".")[0])
    assert major == 0, "v1.0 안정화 전에는 0.x.x 유지"
