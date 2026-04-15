"""
영상 단위 분석 컨텍스트.

유저가 "자주 나오는 키워드"에 모드(IGNORE/FILTER/TRIGGER)를 부여하면,
분석 요청 1회마다 VideoContext로 변환해 필터링 파이프라인에 전달한다.

- FILTER 키워드는 first_pass 에서 SYSTEM_KEYWORD 로 검출되어 일반 처분 적용
- TRIGGER 키워드는 RiskScorer 에서 동시 등장 시 카테고리 강제 상승
- IGNORE 키워드는 no-op (사용자가 "이 단어는 필터링에 관여시키지 않겠다" 는
  의사 표시일 뿐, 백엔드는 아무 동작도 수행하지 않는다)
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VideoContext:
    ignore_keywords: frozenset[str] = field(default_factory=frozenset)
    trigger_keywords: frozenset[str] = field(default_factory=frozenset)
    filter_keywords: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_modes(cls, keyword_modes: dict[str, str] | None) -> "VideoContext":
        if not keyword_modes:
            return cls()
        ignore, trigger, filt = set(), set(), set()
        for word, mode in keyword_modes.items():
            if not word:
                continue
            if mode == "IGNORE":
                ignore.add(word)
            elif mode == "TRIGGER":
                trigger.add(word)
            elif mode == "FILTER":
                filt.add(word)
        return cls(
            ignore_keywords=frozenset(ignore),
            trigger_keywords=frozenset(trigger),
            filter_keywords=frozenset(filt),
        )

    def cache_signature(self) -> str:
        parts = [
            "i:" + ",".join(sorted(self.ignore_keywords)),
            "t:" + ",".join(sorted(self.trigger_keywords)),
            "f:" + ",".join(sorted(self.filter_keywords)),
        ]
        return "|".join(parts)
