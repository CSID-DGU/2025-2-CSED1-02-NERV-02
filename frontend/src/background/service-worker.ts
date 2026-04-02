// 확장 프로그램이 설치되거나 업데이트되었을 때 실행되는 이벤트
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('[GuardFilter] 확장 프로그램이 성공적으로 설치되었습니다!');
    
    // 초기 설정값 세팅
    const defaultSettings = {
      intensity: 3,
      modules: { 
        criticism: true, 
        conflict: true, 
        gaslighting: true, 
        sexual: true, 
        relevance: true 
      },
      whiteList: ['바보', '멍청이'],
      blackList: ['비하 별명', '경쟁 채널']
    };
    
    chrome.storage.local.set({ 'guard-filter-settings': defaultSettings });
  } else if (details.reason === 'update') {
    console.log('[GuardFilter] 확장 프로그램이 업데이트되었습니다.');
  }
});

// 메시지 리스너
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'FETCH_ANALYSIS') {
    chrome.storage.local.get('access_token').then(async ({ access_token }) => {
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${access_token}`
      };
      try {
        const youtubeRes = await fetch(
          `http://localhost:8000/api/analyses/youtube?video_id=${encodeURIComponent(message.videoId)}`,
          { method: 'GET', headers }
        );
        if (!youtubeRes.ok) { sendResponse({ ok: false, error: `YouTube API error: ${youtubeRes.status}` }); return; }
        const youtubeData = await youtubeRes.json();
        const rawComments = youtubeData.results ?? [];

        const textRes = await fetch('http://localhost:8000/api/analyses/text', {
          method: 'POST',
          headers,
          body: JSON.stringify(rawComments)
        });
        if (!textRes.ok) { sendResponse({ ok: false, error: `Text API error: ${textRes.status}` }); return; }
        const textData: Array<{ original_text: string; processed_text: string; action: string }> = await textRes.json();

        const results = textData.map(r => ({
          original: r.original_text,
          processed: r.processed_text,
          action: r.action,
        }));
        sendResponse({ ok: true, results });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    });
    return true; // 비동기 응답을 위해 반드시 필요
  }
});