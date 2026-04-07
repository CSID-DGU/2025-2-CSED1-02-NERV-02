// ── 상수 ──
const FILTER_RESULT_KEY = 'guard-filter-results';

const COMMENT_SELECTORS = [
  'ytd-comment-view-model #content-text',
  'ytd-comment-renderer #content-text',
];
const COMBINED_SELECTOR = COMMENT_SELECTORS.join(', ');

// ── 상태 ──
let filteredTexts: string[] = [];  // 정규화된 필터링 대상 텍스트 배열
let currentVideoId: string | null = null;
let observer: MutationObserver | null = null;
let applyTimeout: ReturnType<typeof setTimeout> | null = null;

// ── 텍스트 정규화 (모든 비-문자를 제거하여 최대한 유연하게 매칭) ──
function normalizeForMatch(text: string): string {
  // 공백, 줄바꿈, 특수문자 차이를 모두 무시하고 순수 텍스트만 비교
  return text.replace(/[\s\u200B-\u200D\uFEFF]/g, '').toLowerCase();
}

// ── 필터링 결과 로드 ──
async function loadFilterResults(): Promise<boolean> {
  try {
    const result = await chrome.storage.local.get(FILTER_RESULT_KEY);
    const data = result[FILTER_RESULT_KEY] as { videoId: string; texts: string[] } | undefined;

    if (data && data.videoId === currentVideoId && data.texts?.length > 0) {
      filteredTexts = data.texts; // 이미 정규화된 상태
      console.log(`[GuardFilter] 필터링 대상 ${filteredTexts.length}개 로드됨`);
      return true;
    }
  } catch (e) {
    console.warn('[GuardFilter] 필터링 결과 로드 실패:', e);
  }
  return false;
}

// ── DOM 필터링 ──
function applyFilter() {
  if (filteredTexts.length === 0) return;

  const elements = document.querySelectorAll(COMBINED_SELECTOR);
  let newFiltered = 0;

  elements.forEach(el => {
    const htmlEl = el as HTMLElement;
    if (htmlEl.dataset.guardProcessed) return;

    const originalText = htmlEl.textContent?.trim() || '';
    if (!originalText) return;

    const normalized = normalizeForMatch(originalText);

    // 정규화된 텍스트가 필터링 목록에 포함되는지 확인
    const shouldFilter = filteredTexts.some(ft => normalized === ft || normalized.includes(ft) || ft.includes(normalized));

    // 디버그: 첫 5개 댓글만 로그 (문제 진단용)
    if (newFiltered === 0 && !shouldFilter && filteredTexts.length > 0) {
      const firstFt = filteredTexts[0];
      if (!htmlEl.dataset.guardDebugLogged) {
        htmlEl.dataset.guardDebugLogged = 'true';
        console.log(`[GuardFilter:debug] DOM="${normalized.substring(0, 50)}" vs FILTER="${firstFt.substring(0, 50)}"`);
      }
    }

    if (shouldFilter) {
      htmlEl.dataset.originalText = originalText;
      htmlEl.dataset.guardProcessed = 'filtered';
      htmlEl.textContent = '🚫 필터링된 댓글입니다.';
      htmlEl.style.color = '#ef4444';
      htmlEl.style.fontStyle = 'italic';
      newFiltered++;
    } else {
      htmlEl.dataset.guardProcessed = 'pass';
    }
  });

  if (newFiltered > 0) {
    console.log(`[GuardFilter] ${newFiltered}개 댓글 필터링 적용`);
  }
}

function resetAllFilters() {
  document.querySelectorAll<HTMLElement>('[data-guard-processed]').forEach(el => {
    if (el.dataset.originalText) {
      el.textContent = el.dataset.originalText;
      el.style.color = '';
      el.style.fontStyle = '';
    }
    delete el.dataset.guardProcessed;
    delete el.dataset.originalText;
  });
}

function scheduleApplyFilter() {
  if (applyTimeout) return;
  applyTimeout = setTimeout(() => {
    applyTimeout = null;
    applyFilter();
  }, 300);
}

// ── Observer ──
function startObserver() {
  observer?.disconnect();
  observer = new MutationObserver(() => scheduleApplyFilter());
  observer.observe(document.body, { childList: true, subtree: true });
}

function getVideoId(): string | null {
  return new URLSearchParams(window.location.search).get('v');
}

// ── 초기화 ──
async function init() {
  const videoId = getVideoId();
  if (!videoId) return;

  if (videoId !== currentVideoId) {
    currentVideoId = videoId;
    filteredTexts = [];
    resetAllFilters();
  }

  await loadFilterResults();
  startObserver();
  applyFilter();
}

// ── 메시지 리스너 ──
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'FILTER_RESULTS_UPDATED') {
    console.log('[GuardFilter] 필터링 결과 업데이트 알림 수신');
    loadFilterResults().then(() => {
      resetAllFilters();
      applyFilter();
    });
  }
});

// ── 스토리지 변경 감지 (메시지를 놓쳐도 스토리지 변경으로 감지) ──
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes[FILTER_RESULT_KEY]) {
    console.log('[GuardFilter] 스토리지 변경 감지');
    const newData = changes[FILTER_RESULT_KEY].newValue as { videoId: string; texts: string[] } | undefined;
    if (newData && newData.videoId === currentVideoId && newData.texts) {
      filteredTexts = newData.texts;
      resetAllFilters();
      applyFilter();
    }
  }
});

console.log('[GuardFilter] Content Script Loaded');
init();
window.addEventListener('yt-navigate-finish', init);
