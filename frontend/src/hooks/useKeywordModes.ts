import { useCallback, useEffect, useState } from 'react';
import type { KeywordMode } from '../api/types';

const STORAGE_KEY = (videoId: string) => `guard-keyword-modes:${videoId}`;

const readFromStorage = (videoId: string | null): Record<string, KeywordMode> => {
  if (!videoId) return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY(videoId));
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

// 초기 상태를 localStorage에서 즉시 읽어 "빈 객체 → 채워진 객체" 레이스를 제거한다.
// 이 레이스가 동일 비디오에 대해 useFullAnalysis queryKey 를 두 번 바꿔 중복 분석을 유발했다.
export const useKeywordModes = (videoId: string | null) => {
  const [modes, setModes] = useState<Record<string, KeywordMode>>(() => readFromStorage(videoId));

  useEffect(() => {
    setModes(readFromStorage(videoId));
  }, [videoId]);

  const setMode = useCallback((word: string, mode: KeywordMode) => {
    setModes(prev => {
      const next = { ...prev, [word]: mode };
      if (videoId) {
        localStorage.setItem(STORAGE_KEY(videoId), JSON.stringify(next));
      }
      return next;
    });
  }, [videoId]);

  const clearMode = useCallback((word: string) => {
    setModes(prev => {
      const next = { ...prev };
      delete next[word];
      if (videoId) {
        localStorage.setItem(STORAGE_KEY(videoId), JSON.stringify(next));
      }
      return next;
    });
  }, [videoId]);

  return { modes, setMode, clearMode };
};
