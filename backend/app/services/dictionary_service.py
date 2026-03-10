import logging
from app.repositories.dictionary_repository import DictionaryRepository

logger = logging.getLogger(__name__)

class DictionaryService:
    def __init__(self, repo: DictionaryRepository):
        self.repo = repo

    def get_user_dictionary(self, list_type: str) -> dict:
        whitelist, blacklist = self.repo.load_user_dict()
        if list_type == 'whitelist':
            return {"whitelist": sorted(list(whitelist))}
        elif list_type == 'blacklist':
            return {"blacklist": sorted(list(blacklist))}
        return {}

    def update_user_dictionary(self, words: list, list_type: str, action: str) -> int:
        whitelist, blacklist = self.repo.load_user_dict()
        target_set = whitelist if list_type == 'whitelist' else blacklist if list_type == 'blacklist' else None
        
        if target_set is None: return 0

        changed_count = 0
        for word in words:
            word = word.strip().lower()
            if not word: continue

            if action == 'add' and word not in target_set:
                target_set.add(word)
                changed_count += 1
            elif action == 'remove' and word in target_set:
                target_set.remove(word)
                changed_count += 1
        
        if changed_count > 0:
            self.repo.save_user_dict(whitelist, blacklist)
            logger.info(f"[DictionaryService] '{list_type}'에 {changed_count}개 단어 {action} 완료.")
            
        return changed_count