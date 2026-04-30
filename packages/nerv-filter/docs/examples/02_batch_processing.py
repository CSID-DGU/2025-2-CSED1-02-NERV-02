"""배치 처리 — 대량 텍스트를 빠르게 분석.

analyze_batch() 는 Kiwi 의 네이티브 배치 토큰화를 사용해
analyze() 반복보다 약 2~3배 빠릅니다.

실행:
    python 02_batch_processing.py
"""
import time

from nerv_filter import NervFilter


def main():
    flt = NervFilter()

    # 가상의 댓글 100개
    sample_comments = [
        "오늘 영상 너무 재밌어요!",
        "이 시발 뭐하는 거야",
        "구독하고 갑니다 ㅎㅎ",
        "병신같은 플레이 ㅋㅋ",
        "보지 못한 장면이네요",  # POS 마스크로 통과
        "ㅈㄴ 잘하시네요",
        "쒸발 어이없어",
        "감사합니다 좋은 영상",
        "시바견이 귀여워요",  # 시바 != 시발 사전에 없으면 통과
        "다음 영상도 기대됩니다",
    ] * 10  # 100개

    # 1) 개별 호출
    t0 = time.time()
    individual = [flt.analyze(c) for c in sample_comments]
    t1 = time.time()

    # 2) 배치 호출
    t2 = time.time()
    batch = flt.analyze_batch(sample_comments)
    t3 = time.time()

    # 결과 동일성 검증
    for ind, bat in zip(individual, batch):
        assert ind.action == bat.action, "결과 불일치!"

    print(f"개별 처리 ({len(sample_comments)}개): {(t1 - t0) * 1000:.1f} ms")
    print(f"배치 처리 ({len(sample_comments)}개): {(t3 - t2) * 1000:.1f} ms")
    print(f"속도 향상: {(t1 - t0) / (t3 - t2):.2f}x")
    print()

    # 액션별 통계
    from collections import Counter
    counter = Counter(r.action.value for r in batch)
    print("액션 분포:")
    for action, count in counter.most_common():
        print(f"  {action:<13} {count}건")


if __name__ == "__main__":
    main()
