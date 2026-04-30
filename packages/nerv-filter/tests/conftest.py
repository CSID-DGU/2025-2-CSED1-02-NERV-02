"""pytest 공유 픽스처 — 모듈 단위 NervFilter 재사용으로 Kiwi 로딩 비용 최소화."""
import pytest

from nerv_filter import NervFilter, SecurityLevel


@pytest.fixture(scope="session")
def filter_default():
    """MEDIUM 보안 NervFilter (세션 단위 재사용)."""
    return NervFilter(security_level=SecurityLevel.MEDIUM)


@pytest.fixture(scope="session")
def filter_low():
    return NervFilter(security_level=SecurityLevel.LOW)


@pytest.fixture(scope="session")
def filter_high():
    return NervFilter(security_level=SecurityLevel.HIGH)
