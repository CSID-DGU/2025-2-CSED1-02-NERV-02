/**
 * 한글 자모 분리 및 정규화 모듈 (Python jamo_normalizer.py의 JS 포팅)
 *
 * content-script에서 댓글 텍스트를 정규화하여
 * 서버에서 내려준 패턴 사전과 매칭하는 데 사용한다.
 */

const HANGUL_BASE = 0xac00; // '가'
const HANGUL_END = 0xd7a3;  // '힣'

const CHOSUNG = [
  'ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ',
  'ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ',
];

const JUNGSUNG = [
  'ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ',
  'ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ',
];

const JONGSUNG = [
  '','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ',
  'ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ',
  'ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ',
];

// 쌍자음 → 단자음 정규화
const SIMILAR_CONSONANT: Record<string, string> = {
  'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ',
};

function isHangulSyllable(code: number): boolean {
  return code >= HANGUL_BASE && code <= HANGUL_END;
}

function isJamo(code: number): boolean {
  return code >= 0x3131 && code <= 0x3163;
}

function decomposeChar(code: number): string {
  const offset = code - HANGUL_BASE;
  const cho = Math.floor(offset / (21 * 28));
  const jung = Math.floor((offset % (21 * 28)) / 28);
  const jong = offset % 28;
  let result = CHOSUNG[cho] + JUNGSUNG[jung];
  if (jong > 0) result += JONGSUNG[jong];
  return result;
}

function normalizeSimilar(text: string): string {
  let result = '';
  for (const c of text) {
    result += SIMILAR_CONSONANT[c] ?? c;
  }
  return result;
}

/**
 * Python full_normalize()와 동일한 파이프라인:
 * 소문자화 → 한글/영문/숫자만 보존 → 자모 분리 → 쌍자음 정규화
 */
export function fullNormalize(text: string): string {
  // 1. 소문자화
  text = text.toLowerCase();

  // 2. 한글(완성형+낱자), 영문, 숫자만 보존
  let filtered = '';
  for (const c of text) {
    const code = c.charCodeAt(0);
    if (isHangulSyllable(code) || isJamo(code)) {
      filtered += c;
    } else if ((code >= 0x61 && code <= 0x7a) || (code >= 0x30 && code <= 0x39)) {
      // a-z, 0-9
      filtered += c;
    }
  }

  // 3. 완성형 → 자모 분리
  let decomposed = '';
  for (const c of filtered) {
    const code = c.charCodeAt(0);
    if (isHangulSyllable(code)) {
      decomposed += decomposeChar(code);
    } else {
      decomposed += c;
    }
  }

  // 4. 쌍자음 → 단자음 정규화
  return normalizeSimilar(decomposed);
}
