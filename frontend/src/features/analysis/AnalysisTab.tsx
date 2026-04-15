import { useMemo, useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useAnalysisContext } from './AnalysisContext';
import { derivePolicy } from './policy';
import { useDeleteDictionaryWord, useYoutubeChannel, useLinkYoutubeChannel, useUnlinkYoutubeChannel, useSettings } from '../../hooks/useSystemConfig';
import { fetchKeywordAnalysis } from '../../api/services';
import type { FilteredKeyword, KeywordMode, ModerationAction } from '../../api/types';

const MODE_ORDER: KeywordMode[] = ['IGNORE', 'TRIGGER', 'FILTER'];
const MODE_LABEL: Record<KeywordMode, string> = {
  IGNORE: '무시',
  TRIGGER: '트리거',
  FILTER: '필터',
};
const MODE_COLORS: Record<KeywordMode, { active: string; inactive: string }> = {
  IGNORE: {
    active: 'bg-green-500 text-white border-green-500',
    inactive: 'bg-white text-green-600 border-green-200 hover:bg-green-50',
  },
  TRIGGER: {
    active: 'bg-orange-500 text-white border-orange-500',
    inactive: 'bg-white text-orange-600 border-orange-200 hover:bg-orange-50',
  },
  FILTER: {
    active: 'bg-red-500 text-white border-red-500',
    inactive: 'bg-white text-red-600 border-red-200 hover:bg-red-50',
  },
};

const AnalysisTab = () => {
  const [channelInput, setChannelInput] = useState('');

  const { videoId, data, isLoading, keywordModes, setMode } = useAnalysisContext();
  const { data: settings } = useSettings();

  const { data: channel } = useYoutubeChannel();
  const linkChannel = useLinkYoutubeChannel();
  const unlinkChannel = useUnlinkYoutubeChannel();

  const deleteWord = useDeleteDictionaryWord();

  // 보안 모드 기반으로 action 을 클라이언트에서 재유도.
  const actionsByComment = useMemo(() => {
    const m = new Map<string, ModerationAction>();
    if (!data || !settings) return m;
    for (const c of data.results) {
      m.set(c.comment_id, derivePolicy(c, settings.intensity).action);
    }
    return m;
  }, [data, settings]);

  // /keywords 엔드포인트는 이제 형태소 추출(trending)만 수행 — 댓글 분석 재실행 없음.
  // 키워드 모드 변경과 무관하므로 queryKey에서 제외.
  const keywordQuery = useQuery({
    queryKey: ['keyword-analysis', videoId],
    queryFn: () => fetchKeywordAnalysis(
      data!.results.map(r => ({ comment_id: r.comment_id, text: r.text, author: r.author, published_at: r.published_at })),
      { videoId },
    ),
    enabled: !!data,
    staleTime: 1000 * 60 * 5,
    placeholderData: keepPreviousData,
  });

  const trendingKeywords = useMemo(
    () => keywordQuery.data?.trending_keywords ?? [],
    [keywordQuery.data],
  );
  const trendingWordSet = useMemo(
    () => new Set(trendingKeywords.map((kw) => kw.word)),
    [trendingKeywords],
  );

  // 필터링된 키워드는 분석 결과에서 직접 집계. trending 단어는 제외한다.
  const filteredKeywords: FilteredKeyword[] = useMemo(() => {
    if (!data) return [];
    const counter = new Map<string, { word: string; count: number; type: string }>();
    for (const c of data.results) {
      for (const dw of c.detected_words) {
        if (trendingWordSet.has(dw.word)) continue; // trending 단어는 trending 섹션에서만
        const key = `${dw.word}|${dw.type}`;
        const cur = counter.get(key);
        if (cur) cur.count += 1;
        else counter.set(key, { word: dw.word, count: 1, type: dw.type });
      }
    }
    return Array.from(counter.values()).sort((a, b) => b.count - a.count);
  }, [data, trendingWordSet]);

  const isLinked = !!channel?.channel_id;

  const handleLink = () => {
    const id = channelInput.trim();
    if (!id) return;
    linkChannel.mutate(id, {
      onSuccess: () => setChannelInput(''),
    });
  };

  // 필터링 키워드의 "허용" 버튼: USER_BLACKLIST 단어만 여기 나타나므로 DB에서 삭제
  const handleAllow = (word: string) => {
    deleteWord.mutate({ words: [word], list_type: 'blacklist' });
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

      {/* 영상 주제 분석 카드 */}
      {data && (data.video_info.category || data.video_info.topics.length > 0 || data.video_info.tags.length > 0) && (
        <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
          <h3 className="font-bold text-sm mb-3">영상 주제 분석</h3>

          {data.video_info.category && (
            <div className="mb-3">
              <span className="text-xs text-gray-500">카테고리</span>
              <div className="mt-1">
                <span className="inline-block bg-blue-100 text-blue-700 text-xs font-medium px-2.5 py-1 rounded">
                  {data.video_info.category}
                </span>
              </div>
            </div>
          )}

          {data.video_info.topics.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-gray-500">주제</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {data.video_info.topics.map((topic) => (
                  <span key={topic} className="inline-block bg-purple-100 text-purple-700 text-xs font-medium px-2.5 py-1 rounded">
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {data.video_info.tags.length > 0 && (
            <div>
              <span className="text-xs text-gray-500">태그</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {data.video_info.tags.slice(0, 15).map((tag) => (
                  <span key={tag} className="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">
                    #{tag}
                  </span>
                ))}
                {data.video_info.tags.length > 15 && (
                  <span className="text-xs text-gray-400">+{data.video_info.tags.length - 15}개</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 분석 데이터 영역 */}
      {isLoading && <div className="text-center text-gray-400 text-sm py-8">분석 데이터 로딩 중...</div>}
      {!isLoading && !data && <div className="text-center text-gray-400 text-sm py-8">데이터가 없습니다.</div>}

      {data && (() => {
        // total_comments는 YouTube 공식 집계(답글 포함) → 상단 카드 표시용.
        // 상태 분포는 실제 분석된 댓글 수(analyzed)를 분모로 사용한다.
        const total = data.total_comments ?? data.results.length;
        const analyzed = data.results.length;
        const blocked = data.results.filter(c => {
          const a = actionsByComment.get(c.comment_id);
          return a === 'FULL_BLOCK' || a === 'PARTIAL_MASK';
        }).length;
        const review = data.results.filter(c => actionsByComment.get(c.comment_id) === 'REVIEW').length;
        const safe = analyzed - blocked - review;
        const safePercent = analyzed > 0 ? Math.round((safe / analyzed) * 100) : 0;
        const blockedPercent = analyzed > 0 ? Math.round((blocked / analyzed) * 100) : 0;
        const reviewPercent = analyzed > 0 ? Math.round((review / analyzed) * 100) : 0;

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
                <div className="text-2xl font-bold text-red-500">{blocked.toLocaleString()}</div>
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
                    <span className="text-gray-600">검토 필요</span>
                    <span className="font-bold">{reviewPercent}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-yellow-400 h-2 rounded-full transition-all duration-500" style={{ width: `${reviewPercent}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">차단 / 마스킹</span>
                    <span className="font-bold">{blockedPercent}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-red-500 h-2 rounded-full transition-all duration-500" style={{ width: `${blockedPercent}%` }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* 필터링된 키워드 */}
            {filteredKeywords.length > 0 && (
              <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
                <h3 className="font-bold text-sm mb-3">필터링된 키워드</h3>
                <div className="space-y-2">
                  {filteredKeywords.map((kw) => {
                    const tag = kw.type === 'SYSTEM_KEYWORD' ? '시스템' : '블랙리스트';
                    const canAllow = kw.type === 'USER_BLACKLIST';
                    return (
                      <div key={kw.word} className="flex items-center justify-between bg-red-50 px-3 py-2 rounded">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-red-700">{kw.word}</span>
                          <span className="text-xs text-red-400">{kw.count}회</span>
                          <span className="text-xs text-gray-400">{tag}</span>
                        </div>
                        {canAllow && (
                          <button
                            onClick={() => handleAllow(kw.word)}
                            className="text-xs bg-white border border-green-300 text-green-600 px-2 py-1 rounded hover:bg-green-50"
                          >
                            허용
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 자주 등장하는 키워드 */}
            {trendingKeywords.length > 0 && (
              <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm mb-4">
                <h3 className="font-bold text-sm mb-3">자주 등장하는 키워드</h3>
                <div className="space-y-2">
                  {trendingKeywords.map((kw) => {
                    const current: KeywordMode = keywordModes[kw.word] ?? 'IGNORE';
                    return (
                      <div key={kw.word} className="bg-gray-50 px-3 py-2 rounded flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-sm font-medium text-gray-700 truncate">{kw.word}</span>
                          <span className="text-xs text-gray-400 shrink-0">{kw.count}회</span>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          {MODE_ORDER.map((m) => {
                            const isActive = current === m;
                            const color = MODE_COLORS[m];
                            return (
                              <button
                                key={m}
                                onClick={() => setMode(kw.word, m)}
                                className={`text-[10px] px-1.5 py-0.5 rounded border font-medium transition-colors ${
                                  isActive ? color.active : color.inactive
                                }`}
                              >
                                {MODE_LABEL[m]}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
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
