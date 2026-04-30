"""변형 우회 탐지 테스트."""
import pytest


@pytest.mark.parametrize(
    "variant",
    [
        "씨발",
        "씌발",
        "쒸발",
        "시벌",
        "시볼",
        "쒸뱔",
        "씨발새끼",
    ],
)
def test_variants_caught(filter_default, variant):
    """사전 변형이 탐지되어야 한다."""
    result = filter_default.analyze(variant)
    assert not result.is_clean, f"missed variant: {variant}"


@pytest.mark.parametrize(
    "input_text",
    [
        "시 발",       # 공백 (Kiwi space_tolerance)
        "시1발",      # 숫자 (compact_normalize)
        "시.발",      # 특수문자 (compact_normalize)
        "시이이발",   # 모음 늘림 (Kiwi typos)
        "벼엉신",     # 종성 분리 (Kiwi normalize_coda)
    ],
)
def test_normalization_uncovers_variants(filter_default, input_text):
    """정규화 메커니즘으로 변형을 잡아야 한다."""
    result = filter_default.analyze(input_text)
    assert not result.is_clean, f"missed by normalization: {input_text}"
