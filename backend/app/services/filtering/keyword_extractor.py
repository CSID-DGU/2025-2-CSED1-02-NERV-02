import logging
from collections import Counter
from kiwipiepy import Kiwi

logger = logging.getLogger(__name__)


class KeywordExtractor:
    def __init__(self):
        self._kiwi: Kiwi | None = None

    @property
    def kiwi(self) -> Kiwi:
        if self._kiwi is None:
            logger.info("[System] Kiwi 형태소 분석기 로딩 중...")
            self._kiwi = Kiwi()
            logger.info("[System] KeywordExtractor 초기화 완료")
        return self._kiwi

    def extract(
        self, texts: list[str], min_count: int = 2, top_n: int = 20
    ) -> list[dict]:
        counter: Counter[str] = Counter()

        for text in texts:
            tokens = self.kiwi.tokenize(text)
            for token in tokens:
                if token.tag.startswith("NN") and len(token.form) >= 2:
                    counter[token.form] += 1

        return [
            {"word": word, "count": count}
            for word, count in counter.most_common(top_n)
            if count >= min_count
        ]
