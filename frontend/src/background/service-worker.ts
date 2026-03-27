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
    chrome.storage.local.get('access_token').then(({ access_token }) => {
      fetch('http://localhost:8000/api/analyses/youtube', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`
        },
        body: JSON.stringify({ video_id: message.videoId })
      })
        .then(r => r.json())
        .then(data => sendResponse({ ok: true, results: data.results ?? [] }))
        .catch(e => sendResponse({ ok: false, error: String(e) }));
    });
    return true; // 비동기 응답을 위해 반드시 필요
  }
});