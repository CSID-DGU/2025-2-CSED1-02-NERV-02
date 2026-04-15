// ── 상수 ──
const FILTER_RESULT_KEY = 'guard-filter-results';

// comment-id 속성을 가진 YouTube 댓글 컨테이너.
// ytd-comment-view-model 은 최신 YouTube 댓글 구조, ytd-comment-renderer 는 구버전.
const COMMENT_CONTAINER_SELECTOR = 'ytd-comment-view-model, ytd-comment-renderer';
const CONTENT_TEXT_SELECTOR = '#content-text';

// ── 타입 ──
type FilterAction = 'FULL_BLOCK' | 'PARTIAL_MASK';

interface FilterEntry {
  id: string;
  textNorm: string;
  action: FilterAction;
  maskedText: string;
}

// ── 상태 ──
let entriesById: Map<string, FilterEntry> = new Map();
let entriesByText: Map<string, FilterEntry> = new Map();
let currentVideoId: string | null = null;
let observer: MutationObserver | null = null;
let applyTimeout: ReturnType<typeof setTimeout> | null = null;

// ── 텍스트 정규화 ──
// NFKC + 소문자 + 공백/zero-width/변이선택자/구두점/기호(이모지 포함) 제거.
// YouTube API textOriginal 과 DOM textContent 사이의 렌더링 차이를 최대한 흡수한다.
function ultraNormalize(text: string): string {
  return text
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s\u200B-\u200D\uFEFF\u00A0\uFE00-\uFE0F]/g, '')
    .replace(/[\p{P}\p{S}]/gu, '');
}

// ── 댓글 컨테이너에서 comment_id 추출 ──
// 1. <ytd-comment-view-model comment-id="..."> (최신 YouTube)
// 2. 타임스탬프 앵커의 ?lc= 파라미터 (구버전/fallback)
function extractCommentId(container: Element): string | null {
  const directId = container.getAttribute('comment-id');
  if (directId) return directId;

  const link = container.querySelector<HTMLAnchorElement>('a[href*="lc="]');
  if (link?.href) {
    try {
      const url = new URL(link.href, window.location.origin);
      const lc = url.searchParams.get('lc');
      if (lc) return lc;
    } catch {
      // 파싱 실패 시 무시
    }
  }
  return null;
}

// ── 필터링 결과 로드 ──
async function loadFilterResults(): Promise<boolean> {
  try {
    const result = await chrome.storage.local.get(FILTER_RESULT_KEY);
    const data = result[FILTER_RESULT_KEY] as
      | { videoId: string; entries?: FilterEntry[] }
      | undefined;

    if (data && data.videoId === currentVideoId) {
      const list = data.entries ?? [];
      entriesById = new Map(list.map(e => [e.id, e]));
      entriesByText = new Map(list.map(e => [e.textNorm, e]));
      console.log(`[GuardFilter] 로드 완료 — ${list.length}개 엔트리`);
      return list.length > 0;
    }
  } catch (e) {
    console.warn('[GuardFilter] 필터링 결과 로드 실패:', e);
  }
  return false;
}

// ── 매칭된 엔트리 찾기: id 우선, text fallback ──
function findEntry(container: Element, textEl: HTMLElement): FilterEntry | null {
  const commentId = extractCommentId(container);
  if (commentId) {
    const byId = entriesById.get(commentId);
    if (byId) return byId;
  }

  if (entriesByText.size === 0) return null;

  const originalText = textEl.textContent?.trim() || '';
  if (!originalText) return null;
  const normalized = ultraNormalize(originalText);
  if (normalized.length < 2) return null;

  return entriesByText.get(normalized) ?? null;
}

// ── DOM 필터링 ──
function applyFilter() {
  if (entriesById.size === 0 && entriesByText.size === 0) return;

  const containers = document.querySelectorAll<HTMLElement>(COMMENT_CONTAINER_SELECTOR);
  let newFiltered = 0;

  containers.forEach((container) => {
    const textEl = container.querySelector<HTMLElement>(CONTENT_TEXT_SELECTOR);
    if (!textEl || textEl.dataset.guardProcessed) return;

    const originalText = textEl.textContent?.trim() || '';
    if (!originalText) return;

    const entry = findEntry(container, textEl);
    if (!entry) {
      textEl.dataset.guardProcessed = 'pass';
      return;
    }

    textEl.dataset.originalText = originalText;

    if (entry.action === 'FULL_BLOCK') {
      textEl.dataset.guardProcessed = 'blocked';
      textEl.textContent = '🚫 필터링된 댓글입니다.';
      textEl.style.color = '#ef4444';
      textEl.style.fontStyle = 'italic';
    } else {
      // PARTIAL_MASK: 서버가 생성한 masked_text 로 치환, 주황색 강조.
      textEl.dataset.guardProcessed = 'masked';
      textEl.textContent = entry.maskedText || originalText;
      textEl.style.color = '#ea580c';
      textEl.style.fontStyle = 'normal';
    }
    newFiltered++;
  });

  if (newFiltered > 0) {
    console.log(`[GuardFilter] ${newFiltered}개 댓글 필터링 적용`);
  }
}

function resetAllFilters() {
  document.querySelectorAll<HTMLElement>('[data-guard-processed]').forEach((el) => {
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
  }, 200);
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
    entriesById = new Map();
    entriesByText = new Map();
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

// ── 스토리지 변경 감지 ──
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes[FILTER_RESULT_KEY]) {
    console.log('[GuardFilter] 스토리지 변경 감지');
    const newData = changes[FILTER_RESULT_KEY].newValue as
      | { videoId: string; entries?: FilterEntry[] }
      | undefined;
    if (newData && newData.videoId === currentVideoId) {
      const list = newData.entries ?? [];
      entriesById = new Map(list.map(e => [e.id, e]));
      entriesByText = new Map(list.map(e => [e.textNorm, e]));
      resetAllFilters();
      applyFilter();
    }
  }
});

console.log('[GuardFilter] Content Script Loaded');
init();
window.addEventListener('yt-navigate-finish', init);
