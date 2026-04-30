"""사용자 사전 동적 갱신 — whitelist / blacklist 추가/삭제.

실행:
    python 03_dynamic_dictionary.py
"""
from nerv_filter import NervFilter


def main():
    flt = NervFilter()

    # ── 시나리오 1: 특정 단어를 임시로 차단 ──
    print("=== 시나리오 1: 블랙리스트 추가 ===")
    target = "특정닉네임xyz"
    text = f"{target} 진짜 별로다"

    print(f"  추가 전: {flt.analyze(text).is_clean=}")
    flt.add_to_blacklist([target])
    print(f"  추가 후: {flt.analyze(text).is_clean=}")
    print(f"  마스킹: '{flt.analyze(text).masked_text}'")
    print()

    # ── 시나리오 2: 오탐 단어를 화이트리스트로 보호 ──
    print("=== 시나리오 2: 화이트리스트로 오탐 보호 ===")
    fp_text = "병신년 이야기 (소설 제목)"

    print(f"  전:    action={flt.analyze(fp_text).action.value}")
    flt.add_to_whitelist(["병신년"])
    print(f"  후:    action={flt.analyze(fp_text).action.value}")
    print()

    # ── 시나리오 3: 신고/허용 워크플로우 시뮬레이션 ──
    print("=== 시나리오 3: 사용자 신고/허용 ===")
    incident = "발견된단어abc"
    flt.add_to_blacklist([incident])
    print(f"  신고 추가: blacklist size = {len(flt.blacklist)}")

    # 잘못 신고했다고 판단 → 제거
    flt.remove_from_blacklist([incident])
    print(f"  취소 후:   blacklist size = {len(flt.blacklist)}")
    print()

    # ── 시나리오 4: 일괄 등록 ──
    print("=== 시나리오 4: 사용자 사전 일괄 동기화 ===")
    user_blacklist = ["욕1", "욕2", "욕3"]
    user_whitelist = ["허용단어A", "허용단어B"]

    added_b = flt.add_to_blacklist(user_blacklist)
    added_w = flt.add_to_whitelist(user_whitelist)
    print(f"  Blacklist 추가: {added_b}건")
    print(f"  Whitelist 추가: {added_w}건")


if __name__ == "__main__":
    main()
