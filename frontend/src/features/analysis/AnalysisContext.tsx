import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useFullAnalysis } from '../../hooks/useYoutubeQuery';
import { useKeywordModes } from '../../hooks/useKeywordModes';
import type { FullAnalysisResponse, KeywordMode } from '../../api/types';

// 탭 간 분석 결과를 공유하기 위해 AppView 수준에서 hoist 한다.
// 이 컨텍스트가 없으면 ChatTab과 AnalysisTab이 각각 useFullAnalysis를 호출하는데,
// 탭 전환 시 마운트/언마운트가 반복되어 이전에 분석 2회가 발생하던 원인이었다.

interface AnalysisContextValue {
  videoId: string | null;
  errorMsg: string | null;
  data: FullAnalysisResponse | null;
  isLoading: boolean;
  isError: boolean;
  keywordModes: Record<string, KeywordMode>;
  setMode: (word: string, mode: KeywordMode) => void;
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null);

export const AnalysisProvider = ({ children }: { children: ReactNode }) => {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const urlStr = tabs[0]?.url;
        if (urlStr && urlStr.includes('youtube.com/watch')) {
          try {
            const url = new URL(urlStr);
            const v = url.searchParams.get('v');
            if (v) {
              setVideoId(v);
              setErrorMsg(null);
            } else {
              setErrorMsg('유튜브 영상 ID를 찾을 수 없습니다.');
            }
          } catch {
            setErrorMsg('URL을 분석할 수 없습니다.');
          }
        } else {
          setErrorMsg('유튜브 영상 페이지에서 실행해주세요.');
        }
      });
    } else {
      setVideoId('Z7_WWJEj-j8');
    }
  }, []);

  const { modes: keywordModes, setMode } = useKeywordModes(videoId);
  const { data, isLoading, isError } = useFullAnalysis(videoId, keywordModes);

  const value = useMemo<AnalysisContextValue>(
    () => ({ videoId, errorMsg, data, isLoading, isError, keywordModes, setMode }),
    [videoId, errorMsg, data, isLoading, isError, keywordModes, setMode],
  );

  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>;
};

export const useAnalysisContext = (): AnalysisContextValue => {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error('useAnalysisContext must be used within AnalysisProvider');
  return ctx;
};
