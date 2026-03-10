import os
from functools import lru_cache
from fastapi import Depends

from app.repositories.dictionary_repository import DictionaryRepository
from app.services import FirstPassFilter, FirstPassFilterV2, SecondPassFilter, RiskScorer, PolicyManager, DictionaryService
from app.clients.youtube_client import YouTubeClient

@lru_cache()
def get_dictionary_repository() -> DictionaryRepository:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    dict_dir = os.path.join(app_dir, 'resources', 'dictionaries')
    return DictionaryRepository(dict_dir=dict_dir)

@lru_cache()
def get_dictionary_service(
    repo: DictionaryRepository = Depends(get_dictionary_repository)
) -> DictionaryService:
    return DictionaryService(repo=repo)

@lru_cache()
def get_first_pass_filter_v2(
    repo: DictionaryRepository = Depends(get_dictionary_repository)
) -> FirstPassFilterV2:
    print("🚀 [System] 1차 필터(FirstPassFilter) 로딩 중...")
    return FirstPassFilterV2(repo=repo)

@lru_cache()
def get_first_pass_filter(
    repo: DictionaryRepository = Depends(get_dictionary_repository)
) -> FirstPassFilter:
    print("🚀 [System] 1차 필터(FirstPassFilter) 로딩 중...")
    return FirstPassFilter(repo=repo)

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