import { useEffect, useState } from 'react';
import { useFullAnalysis } from '../../hooks/useYoutubeQuery';
import { useDictionary } from '../../hooks/useSystemConfig';

const ChatTab = () => {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 1. 현재 탭의 Video ID 추출
  useEffect(() => {
    // 크롬 익스텐션 환경인지 확인
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
      // 현재 활성화된 탭 정보 가져오기
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const currentTab = tabs[0];
        const urlStr = currentTab?.url;

        if (urlStr && urlStr.includes('youtube.com/watch')) {
          try {
            const url = new URL(urlStr);
            const v = url.searchParams.get('v'); // URL에서 'v' 파라미터 추출
            if (v) {
              setVideoId(v); // 성공! Video ID 설정
              setErrorMsg(null);
            } else {
              setErrorMsg("유튜브 영상 ID를 찾을 수 없습니다.");
            }
          } catch (e) {
            setErrorMsg("URL을 분석할 수 없습니다.");
          }
        } else {
          // 유튜브가 아니거나 탭 정보를 못 가져온 경우
          setErrorMsg("유튜브 영상 페이지에서 실행해주세요.");
        }
      });
    } 
    // 로컬 개발 환경 (pnpm dev)
    else {
      console.log("로컬 개발 환경: 테스트용 ID 사용");
      setVideoId('Z7_WWJEj-j8');
    }
  }, []);

  // 2. TanStack Query로 데이터 가져오기
  // [설계 일치: 백엔드 API 연동] Analysis API 및 Dictionary API 호출
  const { data: analysisData, isLoading, isError } = useFullAnalysis(videoId);
  const { data: dictionary } = useDictionary();

  // [설계 일치: 안전 모드] 데이터 로딩 실패 시 빈 배열 처리 (Fail-safe)
  const localBlacklist = dictionary?.blacklist || [];
  const localWhitelist = dictionary?.whitelist || []; // 화이트리스트도 가져옴

  if (errorMsg) return <div className="p-4 text-center text-gray-500">{errorMsg}</div>;
  if (isLoading) return <div className="p-8 text-center">분석 중입니다... 🛡️</div>;
  if (isError || !analysisData) return <div className="p-4 text-center text-red-500">데이터를 불러오는데 실패했습니다.</div>;

  return (
    <div className="flex flex-col space-y-4 p-2">
      {analysisData.results.map((comment, index) => {
       // =================================================================================
        // [Logic Alignment] 요구사항명세서 및 상세설계서 로직 구현
        // =================================================================================
        
        // 1. [동작 규칙 1] 화이트리스트 최우선 적용 (Whitelist Priority) 
        // - 로컬 화이트리스트에 있는 단어가 포함되면 무조건 통과 (서버 판단보다 우선할 수도 있음 - UI UX상)
        const isWhitelisted = localWhitelist.some(goodWord => 
          comment.text.toLowerCase().includes(goodWord.toLowerCase())
        );

        // 2. [Step 4. Policy Manager] 서버의 정책 판단 확인 (Server Action)
        // - 백엔드에서 보안 레벨과 위험 점수를 계산해 내린 최종 처분
        const isServerHidden = comment.action === 'AUTO_HIDE' || comment.action === 'PERMANENT_DELETE';

        // 3. [UI_REQ_004] 클라이언트 로컬 블랙리스트 확인 (Local Blacklist)
        // - 서버 응답과 무관하게 사용자가 지정한 단어는 즉시 차단
        const isLocalBlacklisted = localBlacklist.some(badWord => 
          comment.text.toLowerCase().includes(badWord.toLowerCase())
        );

        // 4. [최종 판별] 이중 필터링 로직 (Dual-Check)
        // - 화이트리스트가 아니면서, (서버가 숨기라고 했거나 OR 로컬 블랙리스트에 걸렸거나)
        const shouldBlur = !isWhitelisted && (isServerHidden || isLocalBlacklisted);

        // =================================================================================

        return (
          <div key={index} className={`flex items-start space-x-3 p-2 rounded-lg transition-colors ${shouldBlur ? 'bg-red-50' : 'hover:bg-gray-50'}`}>
            {/* 아바타 */}
            <div className={`w-10 h-10 rounded-full shrink-0 flex items-center justify-center text-white font-bold text-xs ${shouldBlur ? 'bg-red-300' : 'bg-indigo-400'}`}>
              {comment.author.substring(1, 3).toUpperCase()}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline space-x-2">
                <span className="font-bold text-sm text-gray-800 truncate">{comment.author}</span>
                <span className="text-xs text-gray-400">{comment.published_at}</span>
              </div>
              
             {/* 본문 (조건부 렌더링) */}
              <p className={`text-sm mt-1 leading-relaxed break-words ${shouldBlur ? 'text-red-500 italic text-xs' : 'text-gray-700'}`}>
                {shouldBlur ? (
                  <span className="flex items-center">
                     {/* 아이콘 추가로 시각적 인지 강화 */}
                    <span className="mr-1">🚫</span>
                    {isLocalBlacklisted 
                      ? "사용자 블랙리스트 단어가 포함되어 숨겨졌습니다." 
                      : "규정 위반으로 숨겨진 메시지입니다."}
                  </span>
                ) : (
                  comment.processed_text
                )}
              </p>
              
              {/* 태그 표시 영역 (서버 태그 + 로컬 차단 태그) */}
              {(comment.detected_words.length > 0 || isLocalBlacklisted) && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {/* 1. 서버에서 온 위반 태그들 */}
                  {comment.detected_words.map(({ type: tag }) => (
                    <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded font-medium">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
      {analysisData.results.length === 0 && (
        <div className="text-center text-gray-400 text-xs py-10">
          표시할 댓글이 없습니다.
        </div>
      )}
    </div>
  );
};

export default ChatTab;