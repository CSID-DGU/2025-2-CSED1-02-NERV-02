import type { FullAnalysisResponse } from './types';

export const MOCK_ANALYSIS_DATA: FullAnalysisResponse = {
  video_info: {
    title: "Pixel 7 Review: The Best Android Phone?",
    id: "Z7_WWJEj-j8",
  },
  total_comments: 3,
  results: [
    {
      comment_id: "1",
      text: "Was glad to see the Pixel 7 win those two awards...",
      author: "@TheDiscfanatic",
      published_at: "1 minute ago",
      processed_text: "Was glad to see the Pixel 7 win those two awards...",
      action: "PASS",
      score: 0.05,
      detected_words: [],
    },
    {
      comment_id: "2",
      text: "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다",
      author: "@Hater123",
      published_at: "5 minutes ago",
      processed_text: "야이 **** ㅋㅋ 니네 집 주소 다 털었다",
      action: "AUTO_HIDE",
      score: 0.98,
      detected_words: [{ word: "개새끼", type: "SYSTEM_KEYWORD" }, { word: "니네 집 주소 다 털었다", type: "AI_AGGRESSION" }],
    },
    {
      comment_id: "3",
      text: "돈 버는 법 알려드림. 링크 클릭 -> http://...",
      author: "@Spammer",
      published_at: "10 minutes ago",
      processed_text: "돈 버는 법 알려드림. 링크 클릭 -> http://...",
      action: "PERMANENT_DELETE",
      score: 0.85,
      detected_words: [{ word: "링크 클릭", type: "AI_SPAM" }],
    },
  ],
};