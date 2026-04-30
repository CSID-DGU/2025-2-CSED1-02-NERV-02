"""사용자 정의 사전 사용 — custom_dict_path 로 외부 사전 로드.

기본 사전(default_dic.json) 대신 자체 제작 사전 사용 시.

dic.json 스키마:
    {
      "category_name": {
        "root_word": {"pos": "NNG", "variants": ["변형1", "변형2"]},
        ...
      }
    }

실행:
    python 05_custom_dictionary.py
"""
import json
import tempfile
from pathlib import Path

from nerv_filter import NervFilter


def main():
    # 임시 사전 작성
    custom_dict = {
        "_comment": "사용자 정의 사전 예시",
        "custom": {
            "독자단어xyz": {"pos": "NNG", "variants": ["독자단어ZYX", "독자단어"]},
            "테스트금칙어": {"pos": "NNG", "variants": []},
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(custom_dict, f, ensure_ascii=False, indent=2)
        custom_path = f.name

    try:
        # 사용자 정의 사전으로 초기화
        flt = NervFilter(custom_dict_path=custom_path)

        print(f"Custom dict size: {flt.get_dictionary_size()} words")
        print()

        # 동작 확인
        for text in [
            "이건 독자단어xyz 입니다",
            "다른 표기로 독자단어ZYX",
            "테스트금칙어 가 들어있다",
            "일반 텍스트는 통과",
            "시발 진짜 (기본 사전 없으니 통과)",  # custom dict에는 없음
        ]:
            result = flt.analyze(text)
            marker = "BLK" if not result.is_clean else "OK "
            print(f"  [{marker}] {text:<35} → {result.masked_text}")

    finally:
        Path(custom_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
