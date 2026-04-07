import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useFullAnalysis } from '../../hooks/useYoutubeQuery';
import { useAddDictionaryWord, useDeleteDictionaryWord, useYoutubeChannel, useLinkYoutubeChannel, useUnlinkYoutubeChannel } from '../../hooks/useSystemConfig';
import { fetchKeywordAnalysis } from '../../api/services';
import type { KeywordAnalysisResponse, FilteredKeyword, TrendingKeyword } from '../../api/types';

const AnalysisTab = () => {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [channelInput, setChannelInput] = useState('');

  // 허용/차단 버튼으로 이동된 키워드를 로컬에서 즉시 반영
  const [allowedWords, setAllowedWords] = useState<Set<string>>(new Set());
  const [blockedWords, setBlockedWords] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const urlStr = tabs[0]?.url;
        if (urlStr) {
          const url = new URL(urlStr);
          const v = url.searchParams.get('v');
          if (v) setVideoId(v);
        }
      });
    } else {
      setVideoId('Z7_WWJEj-j8');
    }
  }, []);

  const { data: channel } = useYoutubeChannel();
  const linkChannel = useLinkYoutubeChannel();
  const unlinkChannel = useUnlinkYoutubeChannel();

  const { data, isLoading } = useFullAnalysis(videoId);
  const addWord = useAddDictionaryWord();
  const deleteWord = useDeleteDictionaryWord();

  const keywordQuery = useQuery({
    queryKey: ['keyword-analysis', videoId],
    queryFn: () => fetchKeywordAnalysis(
      data!.results.map(r => ({ comment_id: r.comment_id, text: r.text, author: r.author, published_at: r.published_at }))
    ),
    enabled: !!data,
    staleTime: 1000 * 60 * 5,
  });

  const keywords: KeywordAnalysisResponse | null = keywordQuery.data ?? null;
  const isLinked = !!channel?.channel_id;

  // 서버 키워드 데이터가 갱신되면 로컬 오버라이드 초기화
  useEffect(() => {
    if (keywordQuery.dataUpdatedAt > 0) {
      setAllowedWords(new Set());
      setBlockedWords(new Set());
    }
  }, [keywordQuery.dataUpdatedAt]);

  // 서버 데이터에 로컬 상태 적용한 최종 키워드 목록
  const filteredKeywords: FilteredKeyword[] = keywords
    ? [
        // 서버 필터링 키워드에서 허용된 것 제거
        ...keywords.filtered_keywords.filter(kw => !allowedWords.has(kw.word)),
        // 차단으로 이동된 트렌딩 키워드 추가
        ...[...blockedWords]
          .map(word => {
            const trending = keywords.trending_keywords.find(kw => kw.word === word);
            return trending ? { word: trending.word, count: trending.count, type: 'USER_BLACKLIST' } : null;
          })
          .filter((kw): kw is FilteredKeyword => kw !== null),
      ]
    : [];

  const trendingKeywords: TrendingKeyword[] = keywords
    ? [
        // 서버 트렌딩에서 차단된 것 제거
        ...keywords.trending_keywords.filter(kw => !blockedWords.has(kw.word)),
        // 허용으로 이동된 필터링 키워드 추가 (자주 등장하는 키워드에 표시)
        ...[...allowedWords]
          .map(word => {
            const filtered = keywords.filtered_keywords.find(kw => kw.word === word);
            return filtered ? { word: filtered.word, count: filtered.count } : null;
          })
          .filter((kw): kw is TrendingKeyword => kw !== null),
      ]
    : [];

  const handleLink = () => {
    const id = channelInput.trim();
    if (!id) return;
    linkChannel.mutate(id, {
      onSuccess: () => setChannelInput(''),
    });
  };

  const handleAllow = (word: string, type: string) => {
    setAllowedWords(prev => new Set(prev).add(word));

    if (type === 'USER_BLACKLIST') {
      deleteWord.mutate({ words: [word], list_type: 'blacklist' });
    } else {
      addWord.mutate({ words: [word], list_type: 'whitelist' });
    }
  };

  const handleBlock = (word: string) => {
    setBlockedWords(prev => new Set(prev).add(word));
    addWord.mutate({ words: [word], list_type: 'blacklist' });
  };

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">분석 리포트</h2>

      {/* YouTube 채널 연동 카드 */}
      <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
        {isLinked ? (
          <div className="flex items-center gap-3">
            {channel.thumbnail_url && (
              <img
                src={channel.thumbnail_url}
                alt={channel.channel_name ?? ''}
                className="w-12 h-12 rounded-full border border-gray-200"
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="font-bold text-sm text-gray-800 truncate">{channel.channel_name}</div>
              <div className="text-xs text-gray-400 truncate">{channel.channel_id}</div>
            </div>
            <button
              onClick={() => unlinkChannel.mutate()}
              className="text-xs bg-gray-100 text-gray-500 px-3 py-1.5 rounded hover:bg-gray-200"
            >
              연동 해제
            </button>
          </div>
        ) : (
          <div>
            <p className="text-sm text-gray-600 mb-3">
              개인화 필터링 서비스를 이용하기 위해 YouTube 계정을 연동하세요.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={channelInput}
                onChange={(e) => setChannelInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleLink()}
                placeholder="YouTube 채널 ID 입력"
                className="flex-1 px-3 py-2 border border-gray-200 rounded text-sm focus:outline-none focus:border-blue-400"
              />
              <button
                onClick={handleLink}
                disabled={linkChannel.isPending || !channelInput.trim()}
                className="px-4 py-2 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50"
              >
                {linkChannel.isPending ? '...' : '연동'}
              </button>
            </div>
            {linkChannel.isError && (
              <p className="text-xs text-red-500 mt-2">유효하지 않은 채널 ID입니다.</p>
            )}
          </div>
        )}
      </div>

      {/* 분석 데이터 영역 */}
      {isLoading && <div className="text-center text-gray-400 text-sm py-8">분석 데이터 로딩 중...</div>}
      {!isLoading && !data && <div className="text-center text-gray-400 text-sm py-8">데이터가 없습니다.</div>}

      {data && (() => {
        const total = data.results.length;
        const filtered = data.results.filter(c => c.action !== 'PASS').length;
        const safe = total - filtered;
        const safePercent = total > 0 ? Math.round((safe / total) * 100) : 0;
        const filteredPercent = total > 0 ? Math.round((filtered / total) * 100) : 0;

        return (
          <>
            {/* 상단 카드 */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm">
                <div className="text-gray-500 text-xs">총 댓글 수</div>
                <div className="text-2xl font-bold text-gray-900">{total.toLocaleString()}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm">
                <div className="text-gray-500 text-xs">필터링됨</div>
                <div className="text-2xl font-bold text-red-500">{filtered.toLocaleString()}</div>
              </div>
            </div>

            {/* 그래프 영역 */}
            <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
              <h3 className="font-bold text-sm mb-4">댓글 상태 분포</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">정상 / 안전</span>
                    <span className="font-bold">{safePercent}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full transition-all duration-500" style={{ width: `${safePercent}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">차단 / 숨김</span>
                    <span className="font-bold">{filteredPercent}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-red-500 h-2 rounded-full transition-all duration-500" style={{ width: `${filteredPercent}%` }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* 필터링된 키워드 */}
            {filteredKeywords.length > 0 && (
              <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
                <h3 className="font-bold text-sm mb-3">필터링된 키워드</h3>
                <div className="space-y-2">
                  {filteredKeywords.map((kw) => (
                    <div key={kw.word} className="flex items-center justify-between bg-red-50 px-3 py-2 rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-red-700">{kw.word}</span>
                        <span className="text-xs text-red-400">{kw.count}회</span>
                        <span className="text-xs text-gray-400">{kw.type === 'SYSTEM_KEYWORD' ? '시스템' : '블랙리스트'}</span>
                      </div>
                      <button
                        onClick={() => handleAllow(kw.word, kw.type)}
                        className="text-xs bg-white border border-green-300 text-green-600 px-2 py-1 rounded hover:bg-green-50"
                      >
                        허용
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 자주 등장하는 키워드 */}
            {trendingKeywords.length > 0 && (
              <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
                <h3 className="font-bold text-sm mb-3">자주 등장하는 키워드</h3>
                <div className="space-y-2">
                  {trendingKeywords.map((kw) => (
                    <div key={kw.word} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-700">{kw.word}</span>
                        <span className="text-xs text-gray-400">{kw.count}회</span>
                      </div>
                      <button
                        onClick={() => handleBlock(kw.word)}
                        className="text-xs bg-white border border-red-300 text-red-600 px-2 py-1 rounded hover:bg-red-50"
                      >
                        차단
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {keywordQuery.isLoading && (
              <div className="text-xs text-gray-400 text-center mb-4">키워드 분석 중...</div>
            )}

            <div className="mt-4 text-xs text-gray-400 text-center">
              현재 영상: {data.video_info.title || 'Unknown Video'}
            </div>
          </>
        );
      })()}
    </div>
  );
};

export default AnalysisTab;
