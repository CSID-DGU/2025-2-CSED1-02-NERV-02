import math
import logging
from typing import Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core import settings

logger = logging.getLogger(__name__)

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

            return {
                "snippet": {
                    "title": snippet.get("title"),
                    "channelId": snippet.get("channelId"),
                    "description": snippet.get("description"),
                    "tags": snippet.get("tags", []),
                    "categoryId": snippet.get("categoryId"),
                },
                "statistics": {
                    "commentCount": int(statistics.get("commentCount", 0)),
                },
                "topicDetails": {
                    "topicCategories": topic_details.get("topicCategories", [])
                }
            }

        except HttpError as e:
            logger.error(f"YouTube API Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unknown Error: {e}")
            return None

    def get_comments(self, video_id: str, max_pages: int | None = None, comment_count: int = 0) -> list[dict[str, Any]]:
        """댓글 데이터 수집. max_pages=None이면 commentCount 기반 자동 계산 (상한 50페이지)."""
        if not self.youtube:
            return []

        MAX_PAGES_CAP = 50  # 안전 상한선 (5,000개)

        if max_pages is not None:
            effective_pages = min(max_pages, MAX_PAGES_CAP)
        elif comment_count > 0:
            effective_pages = min(math.ceil(comment_count / 100), MAX_PAGES_CAP)
        else:
            effective_pages = 10  # fallback

        comments_list = []
        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="relevance"
            )

            page_count = 0
            while request and page_count < effective_pages:
                response = request.execute()
                
                for item in response['items']:
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comments_list.append({
                        "comment_id": item['id'],
                        "text": snippet['textOriginal'],
                        "author": snippet.get('authorDisplayName'),
                        "published_at": snippet['publishedAt'],
                    })
                
                if 'nextPageToken' in response:
                    request = self.youtube.commentThreads().list_next(
                        previous_request=request, 
                        previous_response=response
                    )
                    page_count += 1
                else:
                    break

            return comments_list

        except HttpError as e:
            logger.error(f"YouTube API Error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unknown Error: {e}")
            return []
        
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