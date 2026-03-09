import sys
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import config
    
class YouTubeClient:
    def __init__(self):
        print("[System] YouTube Client 초기화 중...")
        self.youtube = self._build_service()

    def _build_service(self):
        """(내부 메서드) YouTube API 서비스 연결"""
        api_key = config.YOUTUBE_API_KEY
        
        if not api_key or api_key == "YOUR_ACTUAL_API_KEY_HERE":
            print("Error: YouTube API Key가 설정되지 않았습니다.", file=sys.stderr)
            return None
        
        try:
            service = build('youtube', 'v3', developerKey=api_key)
            print("[System] YouTube 서비스 연결 성공")
            return service
        except Exception as e:
            print(f"YouTube 서비스 빌드 실패: {e}", file=sys.stderr)
            return None

    def get_video_details(self, video_id):
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
                print(f"Error: 비디오 ID {video_id}를 찾을 수 없습니다.", file=sys.stderr)
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
            print(f"YouTube API Error: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unknown Error: {e}", file=sys.stderr)
            return None

    def get_comments(self, video_id, max_pages=1):
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
            print(f"YouTube API Error: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Unknown Error: {e}", file=sys.stderr)
            return []