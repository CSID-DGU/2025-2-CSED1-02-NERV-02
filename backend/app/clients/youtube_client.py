import logging
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings

logger = logging.getLogger(__name__)

class YouTubeClient:
    def __init__(self):
        logger.info("[System] YouTube Client 초기화 중...")
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

    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """영상 메타데이터 수집"""
        if not self.youtube:
            return None

        try:
            request = self.youtube.videos().list(
                part="snippet,topicDetails",
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                logger.warning(f"비디오 ID {video_id}를 찾을 수 없습니다.")
                return None

            item = response['items'][0]
            snippet = item.get('snippet', {})
            topic_details = item.get('topicDetails', {})

            return {
                "snippet": {
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "tags": snippet.get("tags", []),
                    "categoryId": snippet.get("categoryId"),
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

    def get_comments(self, video_id: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """댓글 데이터 수집"""
        if not self.youtube:
            return []

        comments_list = []
        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="relevance"
            )
            
            page_count = 0
            while request and page_count < max_pages:
                response = request.execute()
                
                for item in response['items']:
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comments_list.append({
                        "comment_id": item['id'],
                        "text_original": snippet['textOriginal'],
                        "author_display_name": snippet.get('authorDisplayName'),
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