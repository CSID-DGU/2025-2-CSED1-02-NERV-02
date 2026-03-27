let filterResults: Array<{ original: string; processed: string; action: string }> = [];
let currentVideoId: string | null = null;
let observer: MutationObserver | null = null;

function getVideoId(): string | null {
    return new URLSearchParams(window.location.search).get('v');
}

function applyFilter() {
    document.querySelectorAll('ytd-comment-view-model span.yt-core-attributed-string--white-space-pre-wrap[role="text"]').forEach(el => {
        const htmlEl = el as HTMLElement;
        if (htmlEl.dataset.filtered) return;

        const original = htmlEl.textContent?.trim();
        const normalize = (s: string) => s.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
        const match = filterResults.find(r => normalize(r.original) === normalize(original ?? ''));
        if (!match) return;

        if (match.action === 'AUTO_HIDE') {
            htmlEl.textContent = '🚫 필터링된 댓글입니다.';
        } else if (match.action === 'MANUAL_REVIEW') {
            htmlEl.textContent = `⚠️ ${match.processed}`;
        }
        htmlEl.dataset.filtered = 'true';
    });
}

async function fetchFilterResults(videoId: string) {
    try {
        const response = await chrome.runtime.sendMessage({ type: 'FETCH_ANALYSIS', videoId });
        if (!response?.ok) return;
        filterResults = response.results;
        applyFilter();
    } catch (e) {
        console.error('[GuardFilter] API 호출 실패', e);
    }
}

function startObserver() {
    observer?.disconnect();
    observer = new MutationObserver(() => applyFilter());
    observer.observe(document.body, { childList: true, subtree: true });
}

function init() {
    const videoId = getVideoId();
    if (!videoId || videoId === currentVideoId) return;

    currentVideoId = videoId;
    filterResults = [];
    startObserver();
    fetchFilterResults(videoId);
}

console.log('[GuardFilter] Content Script Loaded!');
init();
window.addEventListener('yt-navigate-finish', init);