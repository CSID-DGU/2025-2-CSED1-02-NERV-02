"""사전 동적 갱신 테스트."""
from nerv_filter import NervFilter, SecurityLevel


def test_add_to_blacklist_dynamic():
    """블랙리스트 동적 추가 → 즉시 탐지."""
    flt = NervFilter(security_level=SecurityLevel.MEDIUM)
    word = "테스트금칙어xyz"

    # 처음엔 통과
    assert flt.analyze(f"안녕 {word} 입니다").is_clean

    # 블랙리스트 추가
    added = flt.add_to_blacklist([word])
    assert added == 1

    # 이제는 차단
    result = flt.analyze(f"안녕 {word} 입니다")
    assert not result.is_clean


def test_add_to_whitelist_dynamic():
    """화이트리스트 추가 → 차단되던 게 통과."""
    flt = NervFilter(security_level=SecurityLevel.MEDIUM)
    word = "씨발"

    # 처음엔 차단
    assert not flt.analyze(f"이 {word}").is_clean

    # 화이트리스트 추가
    flt.add_to_whitelist([word])

    # 이제는 통과
    assert flt.analyze(f"이 {word}").is_clean


def test_remove_from_blacklist():
    """블랙리스트 제거 → 다시 통과."""
    flt = NervFilter()
    word = "임시단어zzz"
    flt.add_to_blacklist([word])
    assert not flt.analyze(word).is_clean

    removed = flt.remove_from_blacklist([word])
    assert removed == 1
    assert flt.analyze(word).is_clean


def test_whitelist_property():
    """whitelist 속성은 불변 복사본 반환."""
    flt = NervFilter(whitelist=["허용1"])
    snapshot = flt.whitelist
    snapshot.add("불법침입")
    assert "불법침입" not in flt.whitelist
