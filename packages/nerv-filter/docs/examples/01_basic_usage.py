"""기본 사용 — 1줄 호출 vs 인스턴스 재사용.

실행:
    python 01_basic_usage.py
"""
from nerv_filter import NervFilter, SecurityLevel, filter_text


def example_one_liner():
    """패턴 1 — filter_text() 한 줄 호출."""
    print("=== 1. 1줄 사용 ===")
    result = filter_text("이 시발 새끼야")
    print(f"  Action:      {result.action.value}")
    print(f"  Masked:      {result.masked_text}")
    print(f"  Score:       {result.score:.2f}")
    print(f"  Detected:    {[d.word for d in result.detected_words]}")
    print()


def example_instance_reuse():
    """패턴 2 — 인스턴스 재사용 (Kiwi 로딩 비용 1회)."""
    print("=== 2. 인스턴스 재사용 (권장) ===")
    flt = NervFilter(security_level=SecurityLevel.HIGH)
    texts = [
        "오늘 날씨 좋네요",
        "이 시발 진짜",
        "병신아",
        "씨발 또야?",
    ]
    for text in texts:
        result = flt.analyze(text)
        marker = "OK " if result.is_clean else "BLK"
        print(f"  [{marker}] {text:<20} → {result.masked_text}")
    print()


def example_security_levels():
    """패턴 3 — 보안 수준별 동작 차이."""
    print("=== 3. 보안 수준별 비교 ===")
    text = "씨발 진짜 짜증나"
    for level in (SecurityLevel.LOW, SecurityLevel.MEDIUM, SecurityLevel.HIGH):
        flt = NervFilter(security_level=level)
        result = flt.analyze(text)
        print(f"  [{level.value:<6}] action={result.action.value:<13} masked='{result.masked_text}'")
    print()


if __name__ == "__main__":
    example_one_liner()
    example_instance_reuse()
    example_security_levels()
