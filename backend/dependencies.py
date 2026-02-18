from functools import lru_cache

from filter_api.core.first_pass_filter import FirstPassFilter
from filter_api.core.second_pass_filter import SecondPassFilter
from filter_api.core.risk_scorer import RiskScorer
from filter_api.core.policy_manager import PolicyManager
from filter_api.clients.youtube_client import YouTubeClient

@lru_cache()
def get_first_pass_filter() -> FirstPassFilter:
    print("🚀 [System] 1차 필터(FirstPassFilter) 로딩 중...")
    return FirstPassFilter()

@lru_cache()
def get_second_pass_filter() -> SecondPassFilter:
    print("🚀 [System] 2차 필터(SecondPassFilter) 로딩 중...")
    return SecondPassFilter()

@lru_cache()
def get_risk_scorer() -> RiskScorer:
    print("🚀 [System] 위험도 분석기(RiskScorer) 로딩 중...")
    return RiskScorer()

@lru_cache()
def get_policy_manager() -> PolicyManager:
    print("🚀 [System] 정책 매니저(PolicyManager) 로딩 중...")
    return PolicyManager()

@lru_cache()
def get_youtube_client() -> YouTubeClient:
    print("🚀 [System] 유튜브 클라이언트(YouTubeClient) 로딩 중...")
    return YouTubeClient()