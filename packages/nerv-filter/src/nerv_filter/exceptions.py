"""nerv-filter 커스텀 예외."""


class NervFilterError(Exception):
    """nerv-filter 의 모든 예외의 기반."""


class DictionaryError(NervFilterError):
    """사전 로드/파싱 실패."""


class ConfigError(NervFilterError):
    """설정값이 잘못된 경우."""


class EngineError(NervFilterError):
    """Kiwi/Aho-Corasick 엔진 동작 중 발생한 예외."""
