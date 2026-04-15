# Re-export all dependencies for backward compatibility
from .auth import get_current_user
from .repositories import (
    get_system_dict,
    get_user_repository,
    get_dictionary_repository,
    get_video_analysis_cache_repository,
    get_comment_analysis_cache_repository,
)
from .services import (
    get_kiwi_engine,
    get_first_pass_filter,
    get_second_pass_filter,
    get_risk_scorer,
    get_policy_manager,
    get_dictionary_service,
    get_text_analysis_service,
    get_youtube_analysis_service,
    get_user_service,
    get_auth_service,
)
