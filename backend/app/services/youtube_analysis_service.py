import logging
from typing import Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core import settings

logger = logging.getLogger(__name__)

# YouTube Data API categoryId → 카테고리 이름
_YOUTUBE_CATEGORIES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
    "15": "Pets & Animals", "17": "Sports", "18": "Short Movies",
    "19": "Travel & Events", "20": "Gaming", "21": "Videoblogging",
    "22": "People & Blogs", "23": "Comedy", "24": "Entertainment",
    "25": "News & Politics", "26": "Howto & Style", "27": "Education",
    "28": "Science & Technology", "29": "Nonprofits & Activism",
    "30": "Movies", "31": "Anime/Animation", "32": "Action/Adventure",
    "33": "Classics", "34": "Comedy", "35": "Documentary", "36": "Drama",
    "37": "Family", "38": "Foreign", "39": "Horror", "40": "Sci-Fi/Fantasy",
    "41": "Thriller", "42": "Shorts", "43": "Shows", "44": "Trailers",
}


class YoutubeAnalysisService:
    def __init__(self):
        self.youtube = self._build_service()
    
    def _build_service(self):
        """(내부 메서드) YouTube API 서비스 연결"""
        api_key = settings.YOUTUBE_API_KEY

        if not api_key or api_key == "YOUR_ACTUAL_API_KEY_HERE":
            logger.error("YouTube API Key가 설정되지 않았습니다.")
            return None

        try:
            service = build('youtube', 'v3', developerKey=api_key)
            logger.info("[System] YouTube 서비스 연결 성공")
            return service
        except Exception as e:
            logger.error(f"YouTube 서비스 빌드 실패: {e}")
            return None

    def get_video_details(self, video_id: str) -> Optional[dict[str, Any]]:
        """영상 메타데이터 수집"""
        if not self.youtube:
            return None

        try:
            request = self.youtube.videos().list(
                part="snippet,statistics,topicDetails",
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                logger.warning(f"비디오 ID {video_id}를 찾을 수 없습니다.")
                return None

            item = response['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            topic_details = item.get('topicDetails', {})

            # categoryId → 카테고리 이름 변환
            category_id = snippet.get("categoryId")
            category_name = _YOUTUBE_CATEGORIES.get(category_id) if category_id else None

            # topicCategories URL → 주제 이름 파싱
            # e.g. "https://en.wikipedia.org/wiki/Music" → "Music"
            topic_urls = topic_details.get("topicCategories", [])
            topics = []
            for url in topic_urls:
                name = url.rsplit("/", 1)[-1].replace("_", " ") if "/" in url else url
                topics.append(name)

            return {
                "snippet": {
                    "title": snippet.get("title"),
                    "channelId": snippet.get("channelId"),
                    "description": snippet.get("description"),
                    "tags": snippet.get("tags", []),
                    "categoryId": category_id,
                    "category": category_name,
                },
                "statistics": {
                    "commentCount": int(statistics.get("commentCount", 0)),
                },
                "topics": topics,
            }

        except HttpError as e:
            logger.error(f"YouTube API Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unknown Error: {e}")
            return None

    def get_comments(self, video_id: str, max_pages: int | None = None, comment_count: int = 0) -> list[dict[str, Any]]:
        """댓글 데이터 수집 (탑레벨 + 답글).

        - order="time"으로 페이지네이션 (relevance는 list_next가 중복 페이지를 반환하는 버그 있음).
        - `part="snippet,replies"`로 탑레벨과 함께 반환되는 최대 5개 답글을 인라인 수집.
        - 그 이상 답글이 있는 스레드는 `comments.list(parentId=...)`로 별도 페이지네이션.
        - comment_id 기반 dedupe + 연속 중복 페이지 감지 시 탈출.
        """
        if not self.youtube:
            return []

        MAX_PAGES_CAP = 50
        effective_pages = min(max_pages, MAX_PAGES_CAP) if max_pages is not None else MAX_PAGES_CAP

        comments_list: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        def _add(cid: str, snippet: dict, parent_id: str | None = None) -> bool:
            if cid in seen_ids:
                return False
            seen_ids.add(cid)
            comments_list.append({
                "comment_id": cid,
                "text": snippet.get('textOriginal', ''),
                "author": snippet.get('authorDisplayName'),
                "published_at": snippet.get('publishedAt'),
                "parent_id": parent_id,
            })
            return True

        try:
            request = self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                order="time",
            )

            page_count = 0
            while request is not None and page_count < effective_pages:
                response = request.execute()

                page_new = 0
                for item in response['items']:
                    top = item['snippet']['topLevelComment']
                    if _add(top['id'], top['snippet']):
                        page_new += 1

                    # 인라인 답글 (최대 5개)
                    top_id = top['id']
                    inline_replies = item.get('replies', {}).get('comments', [])
                    for r in inline_replies:
                        if _add(r['id'], r['snippet'], parent_id=top_id):
                            page_new += 1

                    # 인라인을 초과하는 답글이 있다면 별도 페이지네이션
                    total_reply_count = item['snippet'].get('totalReplyCount', 0)
                    if total_reply_count > len(inline_replies):
                        self._fetch_all_replies(top_id, _add)

                page_count += 1

                if page_new == 0:
                    logger.info(f"[YouTube] video={video_id} page {page_count} all duplicates, stopping")
                    break

                request = self.youtube.commentThreads().list_next(
                    previous_request=request,
                    previous_response=response,
                )

            logger.info(
                f"[YouTube] video={video_id} fetched={len(comments_list)} "
                f"pages={page_count} reported={comment_count}"
            )
            return comments_list

        except HttpError as e:
            logger.error(f"YouTube API Error: {e}")
            return comments_list
        except Exception as e:
            logger.error(f"Unknown Error: {e}")
            return comments_list

    def _fetch_all_replies(self, parent_id: str, add_fn) -> None:
        """한 탑레벨 댓글의 모든 답글을 페이지네이션으로 수집."""
        try:
            request = self.youtube.comments().list(
                part="snippet",
                parentId=parent_id,
                maxResults=100,
            )
            pages = 0
            while request is not None and pages < 10:
                response = request.execute()
                for r in response.get('items', []):
                    add_fn(r['id'], r['snippet'], parent_id=parent_id)
                pages += 1
                request = self.youtube.comments().list_next(
                    previous_request=request,
                    previous_response=response,
                )
        except HttpError as e:
            logger.warning(f"답글 수집 실패 parent={parent_id}: {e}")

    def get_channel_info(self, channel_id: str) -> dict[str, Any] | None:
        """채널 ID로 채널 정보 조회 (이름, 프로필 사진 등)"""
        if not self.youtube:
            return None

        try:
            request = self.youtube.channels().list(
                part="snippet",
                id=channel_id
            )
            response = request.execute()

            if not response.get('items'):
                return None

            snippet = response['items'][0]['snippet']
            return {
                "channel_id": channel_id,
                "channel_name": snippet.get("title"),
                "channel_url": f"https://youtube.com/channel/{channel_id}",
                "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
            }

        except Exception as e:
            logger.error(f"채널 정보 조회 실패: {e}")
            return None

    def verify_channel(self, video_info: dict, channel_id: str) -> bool:
        """영상이 특정 채널 소유인지 검증"""
        return video_info["snippet"].get("channelId") == channel_id