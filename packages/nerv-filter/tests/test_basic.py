"""기본 동작 테스트."""
from nerv_filter import ModerationAction, NervFilter, SecurityLevel


def test_clean_text_passes(filter_default):
    """욕설 없는 정상 텍스트는 통과."""
    result = filter_default.analyze("오늘 날씨가 좋네요")
    assert result.is_clean
    assert result.action == ModerationAction.NORMAL


def test_basic_curse_detected(filter_default):
    """기본 욕설은 탐지."""
    result = filter_default.analyze("이 시발 진짜")
    assert not result.is_clean


def test_filter_text_function():
    """1줄 함수 사용."""
    from nerv_filter import filter_text

    result = filter_text("오늘 날씨")
    assert result.is_clean


def test_dictionary_loaded(filter_default):
    """사전이 동봉되어 로드되었는지."""
    size = filter_default.get_dictionary_size()
    assert size > 1000, f"Expected 1000+ words, got {size}"


def test_security_level_property(filter_default):
    """security_level 속성."""
    assert filter_default.security_level == SecurityLevel.MEDIUM


def test_to_dict_serialization(filter_default):
    """FilterResult.to_dict() 직렬화."""
    result = filter_default.analyze("이 시발")
    d = result.to_dict()
    assert "action" in d
    assert "masked_text" in d
    assert "score" in d
    assert "detected_words" in d
    assert "flags" in d
