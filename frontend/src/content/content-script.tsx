let filterResults: Array<{ original: string; processed: string; action: string }> = [];
let currentVideoId: string | null = null;
let observer: MutationObserver | null = null;

const COMMENT_SELECTOR = 'ytd-comment-view-model span.yt-core-attributed-string--white-space-pre-wrap[role="text"]';

function getVideoId(): string | null {
    return new URLSearchParams(window.location.search).get('v');
}

function applyFilter() {
    document.querySelectorAll(COMMENT_SELECTOR).forEach(el => {
        const htmlEl = el as HTMLElement;
        if (htmlEl.dataset.filtered) return;

        const normalize = (s: string) => s.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
        const original = htmlEl.dataset.originalText || htmlEl.textContent?.trim();
        const match = filterResults.find(r => normalize(r.original) === normalize(original ?? ''));
        if (!match) return;

        if (match.action === 'AUTO_HIDE' || match.action === 'PERMANENT_DELETE') {
            htmlEl.dataset.originalText = original ?? '';
            htmlEl.textContent = '🚫 필터링된 댓글입니다.';
            htmlEl.dataset.filtered = 'true';
        } else if (match.action === 'REVIEW_HUMAN') {
            htmlEl.dataset.originalText = original ?? '';
            htmlEl.textContent = `⚠️ ${match.processed}`;
            htmlEl.dataset.filtered = 'true';
        } else if (match.action === 'MASKING') {
            htmlEl.dataset.originalText = original ?? '';
            htmlEl.textContent = match.processed;
            htmlEl.dataset.filtered = 'true';
        } else {
            if (htmlEl.dataset.originalText) {
                htmlEl.textContent = htmlEl.dataset.originalText;
                delete htmlEl.dataset.originalText;
            }
        }
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

chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'DICTIONARY_UPDATED' && currentVideoId) {
        document.querySelectorAll<HTMLElement>('[data-filtered]').forEach(el => {
            delete el.dataset.filtered;
        });
        filterResults = [];
        fetchFilterResults(currentVideoId);
    }
});

console.log('[GuardFilter] Content Script Loaded!');
init();
window.addEventListener('yt-navigate-finish', init);
