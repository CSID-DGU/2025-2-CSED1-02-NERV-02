"""2차 필터 후처리 정책 테스트."""
from __future__ import annotations

from types import SimpleNamespace

from nerv_filter import ModerationAction, NervFilter, SecurityLevel


class DummySecondPass:
    is_active = True

    def __init__(self, details: dict[str, dict]):
        self.details = details
        self.config = SimpleNamespace(threshold=0.8)
        self.seen_texts: list[str] = []

    def predict_with_details(self, text: str) -> dict[str, dict]:
        self.seen_texts.append(text)
        return self.details


def test_criticism_is_removed_when_other_ai_module_also_hits():
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=DummySecondPass({
            "criticism": {"score": 0.95, "logit": 3.0, "token_evidence": []},
            "basic": {
                "score": 0.91,
                "logit": 2.0,
                "token_evidence": [
                    {"token": "테스트", "start": 0, "end": 3, "evidence": 0.2},
                ],
            },
        }),
    )

    result = flt.analyze("테스트 문장")

    assert [word.word for word in result.detected_words] == ["basic"]
    assert result.action == ModerationAction.PARTIAL_MASK


def test_criticism_applies_when_it_is_the_only_ai_hit():
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=DummySecondPass({
            "criticism": {
                "score": 0.95,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "테스트", "start": 0, "end": 3, "evidence": 0.4},
                ],
            },
            "basic": {"score": 0.10, "logit": -2.0, "token_evidence": []},
        }),
    )

    result = flt.analyze("테스트 문장")

    assert [word.word for word in result.detected_words] == ["criticism"]
    assert result.action == ModerationAction.PARTIAL_MASK


def test_basic_removes_criticism_and_sexual_but_keeps_other_modules():
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=DummySecondPass({
            "basic": {
                "score": 0.91,
                "logit": 2.0,
                "token_evidence": [
                    {"token": "기본", "start": 0, "end": 2, "evidence": 0.2},
                ],
            },
            "criticism": {
                "score": 0.95,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "비판", "start": 3, "end": 5, "evidence": 0.5},
                ],
            },
            "sexual": {
                "score": 0.95,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "성적", "start": 6, "end": 8, "evidence": 0.5},
                ],
            },
            "politics": {
                "score": 0.91,
                "logit": 2.0,
                "token_evidence": [
                    {"token": "정치", "start": 9, "end": 11, "evidence": 0.3},
                ],
            },
        }),
    )

    result = flt.analyze("기본 비판 성적 정치")

    assert [word.word for word in result.detected_words] == ["basic", "politics"]
    assert result.masked_text == "** 비판 성적 **"


def test_criticism_and_sexual_overlap_keeps_higher_score_module():
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=DummySecondPass({
            "criticism": {
                "score": 0.92,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "비판", "start": 0, "end": 2, "evidence": 0.5},
                ],
            },
            "sexual": {
                "score": 0.96,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "성적", "start": 3, "end": 5, "evidence": 0.5},
                ],
            },
        }),
    )

    result = flt.analyze("비판 성적")

    assert [word.word for word in result.detected_words] == ["sexual"]
    assert result.masked_text == "비판 **"


def test_sexual_is_removed_when_other_non_criticism_module_also_hits():
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=DummySecondPass({
            "sexual": {
                "score": 0.96,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "성적", "start": 0, "end": 2, "evidence": 0.5},
                ],
            },
            "politics": {
                "score": 0.91,
                "logit": 2.0,
                "token_evidence": [
                    {"token": "정치", "start": 3, "end": 5, "evidence": 0.3},
                ],
            },
        }),
    )

    result = flt.analyze("성적 정치")

    assert [word.word for word in result.detected_words] == ["politics"]
    assert result.masked_text == "성적 **"


def test_politics_and_family_overlap_keeps_higher_score_module():
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=DummySecondPass({
            "politics": {
                "score": 0.91,
                "logit": 2.0,
                "token_evidence": [
                    {"token": "정치", "start": 0, "end": 2, "evidence": 0.3},
                ],
            },
            "family": {
                "score": 0.96,
                "logit": 3.0,
                "token_evidence": [
                    {"token": "가족", "start": 3, "end": 5, "evidence": 2.0},
                ],
            },
        }),
    )

    result = flt.analyze("정치 가족")

    assert [word.word for word in result.detected_words] == ["family"]
    assert result.masked_text == "정치 **"


def test_second_pass_runs_on_original_text():
    second_pass = DummySecondPass({
        "pii": {"score": 0.81, "logit": 1.0, "token_evidence": []},
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "욕설 뒤 개인정보",
        "masked_text": "** 뒤 개인정보",
        "detected_words": [{"word": "욕설", "type": "SYSTEM_KEYWORD"}],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert second_pass.seen_texts == ["욕설 뒤 개인정보"]
    assert [item["word"] for item in result["detected_words"]] == ["pii"]
    assert result["action_override"] == ModerationAction.FULL_BLOCK


def test_spam_threshold_is_070_and_full_blocks():
    second_pass = DummySecondPass({
        "spam": {"score": 0.71, "logit": 1.0, "token_evidence": []},
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "광고 링크 확인",
        "masked_text": "광고 링크 확인",
        "detected_words": [],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert [item["word"] for item in result["detected_words"]] == ["spam"]
    assert result["action_override"] == ModerationAction.FULL_BLOCK


def test_second_pass_is_skipped_when_first_pass_keyword_ratio_is_at_least_030():
    second_pass = DummySecondPass({
        "basic": {
            "score": 0.91,
            "logit": 2.0,
            "token_evidence": [
                {"token": "욕설", "start": 0, "end": 2, "evidence": 0.5},
            ],
        },
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "욕설",
        "masked_text": "**",
        "detected_words": [{"word": "욕설", "type": "SYSTEM_KEYWORD"}],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert second_pass.seen_texts == []
    assert result["detected_words"] == [{"word": "욕설", "type": "SYSTEM_KEYWORD"}]
    assert result["masked_text"] == "**"


def test_second_pass_keyword_ratio_uses_masked_span_length():
    second_pass = DummySecondPass({
        "basic": {
            "score": 0.91,
            "logit": 2.0,
            "token_evidence": [
                {"token": "플레이", "start": 5, "end": 8, "evidence": 0.5},
            ],
        },
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "시1발 플레이",
        "masked_text": "**** 플레이",
        "detected_words": [{"word": "시발", "type": "SYSTEM_KEYWORD"}],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert second_pass.seen_texts == []
    assert result["masked_text"] == "**** 플레이"


def test_second_pass_runs_when_first_pass_keyword_ratio_is_below_030():
    second_pass = DummySecondPass({
        "pii": {"score": 0.81, "logit": 1.0, "token_evidence": []},
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "욕설 같은 플레이",
        "masked_text": "** 같은 플레이",
        "detected_words": [{"word": "욕설", "type": "SYSTEM_KEYWORD"}],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert second_pass.seen_texts == ["욕설 같은 플레이"]
    assert [item["word"] for item in result["detected_words"]] == ["pii"]


def test_second_pass_clean_result_resets_first_pass_result():
    second_pass = DummySecondPass({
        "basic": {"score": 0.10, "logit": -1.0, "token_evidence": []},
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "욕설 뒤 정상 문장",
        "status": "FILTERED_BY_FIRST_PASS",
        "masked_text": "** 뒤 정상 문장",
        "detected_words": [{"word": "욕설", "type": "SYSTEM_KEYWORD"}],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert result["detected_words"] == []
    assert result["masked_text"] == "욕설 뒤 정상 문장"


def test_second_pass_mask_replaces_first_pass_mask_when_ratio_is_below_030():
    second_pass = DummySecondPass({
        "basic": {
            "score": 0.91,
            "logit": 2.0,
            "token_evidence": [
                {"token": "욕설포함긴토큰", "start": 0, "end": 7, "evidence": 0.5},
                {"token": "추가", "start": 8, "end": 10, "evidence": 0.5},
            ],
        },
    })
    flt = NervFilter(
        security_level=SecurityLevel.MEDIUM,
        second_pass=second_pass,
    )
    raw = {
        "original_text": "욕설포함긴토큰 추가",
        "status": "FILTERED_BY_FIRST_PASS",
        "masked_text": "**포함긴토큰 추가",
        "detected_words": [{"word": "욕설", "type": "SYSTEM_KEYWORD"}],
    }

    result = flt._apply_second_pass(raw["original_text"], raw)

    assert result["masked_text"] == "******* **"
