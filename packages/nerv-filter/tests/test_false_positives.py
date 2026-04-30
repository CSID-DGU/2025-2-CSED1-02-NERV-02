"""오탐 차단 테스트 — 정상 문장에서 욕설로 잘못 인식되면 안 된다."""
import pytest


@pytest.mark.parametrize(
    "safe_text",
    [
        "오늘 날씨가 좋네요",
        "회의 자료 정리했어요",
        "공주와 왕자",
        "개나리가 피었네요",
        "아저씨 발가락",
    ],
)
def test_no_false_positive(filter_default, safe_text):
    """일반 문장에는 false positive 가 없어야 한다."""
    result = filter_default.analyze(safe_text)
    assert result.is_clean, f"false positive on: {safe_text}"


@pytest.mark.parametrize(
    "ambiguous_text",
    [
        "숙제 했나 보지",       # 보지 = 보조용언 활용
        "자지러지게 웃었다",    # 자지 = 자지러지다 부분
        "신경과 전문의",        # 신경 ≠ 병신의 신
    ],
)
def test_pos_disambiguation(filter_default, ambiguous_text):
    """동음이의어가 명사가 아닌 위치에 있으면 차단."""
    result = filter_default.analyze(ambiguous_text)
    assert result.is_clean, f"POS-based FP not blocked: {ambiguous_text}"
