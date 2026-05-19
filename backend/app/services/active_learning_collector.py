import csv
from datetime import datetime
from pathlib import Path

class ActiveLearningCollector:
    def __init__(self, base_dir: str = "data/active_learning"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.fieldnames = [
            "text",
            "score",
            "human_label",
            "user_id",
            "created_at",
            "review_status",
        ]

    async def collect(self, user, filter_result: dict) -> None:
        scores = filter_result.get("second_pass_scores") or {}
        text = filter_result.get("original_text", "")

        for module_name, score in scores.items():
            score = float(score)

            if not (0.3 <= score <= 0.7):
                continue

            path = self.base_dir / f"{module_name}_candidates.csv"
            file_exists = path.exists()

            with path.open("a", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    "text": text,
                    "score": score,
                    "human_label": "",
                    "user_id": getattr(user, "id", ""),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "review_status": "PENDING",
                })