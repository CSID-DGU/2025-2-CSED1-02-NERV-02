import { useEffect, useState } from 'react';
import { useFullAnalysis } from '../../hooks/useYoutubeQuery';

const AnalysisTab = () => {
  // 비디오 ID 가져오는 로직
  const [videoId, setVideoId] = useState<string | null>(null);
  
  useEffect(() => {
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const urlStr = tabs[0]?.url;
        if (urlStr) {
            const url = new URL(urlStr);
            const v = url.searchParams.get('v');
            if(v) setVideoId(v);
        }
      });
    } else {
      setVideoId('Z7_WWJEj-j8');
    }
  }, []);

  const { data, isLoading } = useFullAnalysis(videoId);

  if (isLoading) return <div className="p-4">분석 데이터 로딩 중...</div>;
  if (!data) return <div className="p-4">데이터가 없습니다.</div>;

  const total = data.results.length;
  
  const filtered = data.results.filter(comment => comment.action !== 'PASS').length;
  
  const safe = total - filtered;
  
  // 퍼센트 계산
  const safePercent = total > 0 ? Math.round((safe / total) * 100) : 0;
  const filteredPercent = total > 0 ? Math.round((filtered / total) * 100) : 0;

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">분석 리포트</h2>
      
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
      <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm">
        <h3 className="font-bold text-sm mb-4">댓글 상태 분포</h3>
        <div className="space-y-4">
          {/* 정상 댓글 */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-600">정상 / 안전</span>
              <span className="font-bold">{safePercent}%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-green-500 h-2 rounded-full transition-all duration-500" style={{ width: `${safePercent}%` }}></div>
            </div>
          </div>

          {/* 필터링 댓글 */}
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
      
      <div className="mt-4 text-xs text-gray-400 text-center">
        현재 영상: {data.video_info.title || 'Unknown Video'}
      </div>
    </div>
  );
};

export default AnalysisTab;