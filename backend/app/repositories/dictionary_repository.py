import os
import json
import logging

logger = logging.getLogger(__name__)

class DictionaryRepository:
    def __init__(self, dict_dir: str):
        self.user_dict_path = os.path.join(dict_dir, 'user_dictionary.json')
        self.system_dict_path = os.path.join(dict_dir, 'word_dictionary.json')

    def load_user_dict(self) -> tuple[set, set]:
        whitelist, blacklist = set(), set()
        try:
            with open(self.user_dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            whitelist = set(w.strip().lower() for w in data.get("user_whitelist", []))
            blacklist = set(w.strip().lower() for w in data.get("user_blacklist", []))
            logger.info(f"[DictionaryRepository] 사용자 사전 로드 완료: 화이트({len(whitelist)}), 블랙({len(blacklist)})")
        except Exception as e:
            logger.error(f"[DictionaryRepository] 사용자 사전 로드 실패: {e}")
        return whitelist, blacklist

    def load_system_dict(self) -> set:
        system_dict = set()
        try:
            with open(self.system_dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for category, content in data.items():
                    for word in content.get("words", []):
                        system_dict.add(word.strip().lower())
            logger.info(f"[DictionaryRepository] 시스템 사전 로드 완료: {len(system_dict)}개 단어")
        except Exception as e:
            logger.error(f"[DictionaryRepository] 시스템 사전 로드 실패: {e}")
        return system_dict

    def save_user_dict(self, whitelist: set, blacklist: set) -> bool:
        try:
            data = {
                "user_whitelist": sorted(list(whitelist)),
                "user_blacklist": sorted(list(blacklist))
            }
            with open(self.user_dict_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"[DictionaryRepository] 사용자 사전 저장 실패: {e}")
            return False