"""
사전 생성기.

자모 단위 규칙으로 욕설 root 의 variants 를 조합해 dic.json 을 재생성한다.
- variants 는 root 와 같은 글자 수만 허용 (예외: 니애미/니애비 통합 그룹)
- 초성/종성 변화는 최소화. 쌍자음 승급/강등(시→씨, 씨→시 등) 위주
- ㅣ → {ㅣ, ㅢ, ㅟ}, ㅏ → 기본 {ㅏ, ㅑ} (단어별 확장 있음)
- 합성어(새끼·년·놈 계열)는 구성요소 variants 의 곱
"""
import json
from pathlib import Path

CHO = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
JUNG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
JONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']


def compose(c: str, j: str, jg: str = '') -> str:
    ci, ji, jgi = CHO.index(c), JUNG.index(j), JONG.index(jg)
    return chr(0xAC00 + (ci * 21 + ji) * 28 + jgi)


def decompose(ch: str):
    code = ord(ch) - 0xAC00
    ci = code // (21 * 28)
    ji = (code % (21 * 28)) // 28
    jgi = code % 28
    return CHO[ci], JUNG[ji], JONG[jgi]


def expand(word: str, rules: list) -> list[str]:
    """각 글자 위치마다 허용 자모 세트를 받아 조합을 전개."""
    results = ['']
    for ch, rule in zip(word, rules):
        c, j, jg = decompose(ch)
        chos = rule.get('cho', [c]) if rule else [c]
        jungs = rule.get('jung', [j]) if rule else [j]
        jongs = rule.get('jong', [jg]) if rule else [jg]
        new = []
        for pref in results:
            for nc in chos:
                for nj in jungs:
                    for njg in jongs:
                        new.append(pref + compose(nc, nj, njg))
        results = new
    seen = set()
    ordered = []
    for w in results:
        if w not in seen:
            seen.add(w)
            ordered.append(w)
    return ordered


def variants(word: str, rules: list) -> list[str]:
    return [w for w in expand(word, rules) if w != word]


# ─── 자모 변형 규칙 프리셋 ─────────────────────────────
NONE = None

SI      = {'cho': ['ㅅ', 'ㅆ'], 'jung': ['ㅣ', 'ㅢ', 'ㅟ']}
BAL     = {'cho': ['ㅂ'],       'jung': ['ㅏ', 'ㅓ', 'ㅗ', 'ㅑ'], 'jong': ['ㄹ']}
BYEONG  = {'cho': ['ㅂ', 'ㅃ'], 'jung': ['ㅕ', 'ㅜ', 'ㅠ'], 'jong': ['ㅇ']}
SIN     = {'cho': ['ㅅ', 'ㅆ'], 'jung': ['ㅣ', 'ㅢ', 'ㅟ'], 'jong': ['ㄴ']}
JI      = {'cho': ['ㅈ', 'ㅉ'], 'jung': ['ㅣ', 'ㅢ', 'ㅟ']}
RAL     = {'cho': ['ㄹ'],       'jung': ['ㅏ', 'ㅑ'], 'jong': ['ㄹ']}            # 지랄 전용
BU_RAL  = {'cho': ['ㄹ'],       'jung': ['ㅏ', 'ㅑ', 'ㅗ'], 'jong': ['ㄹ']}      # 부랄 전용
SAE     = {'cho': ['ㅅ', 'ㅆ'], 'jung': ['ㅐ', 'ㅔ', 'ㅒ', 'ㅖ']}                 # 새끼의 새
KKI     = {'cho': ['ㄲ', 'ㄱ'], 'jung': ['ㅣ', 'ㅢ', 'ㅟ']}                      # 새끼의 끼
GAE     = {'cho': ['ㄱ', 'ㄲ'], 'jung': ['ㅐ', 'ㅔ', 'ㅖ', 'ㅒ']}                 # 개- 접두어
JOT     = {'cho': ['ㅈ'],       'jung': ['ㅗ', 'ㅛ'], 'jong': ['ㅅ', 'ㅆ', 'ㅈ', 'ㅂ']}
BAP     = {'cho': ['ㅂ'],       'jung': ['ㅏ', 'ㅑ'], 'jong': ['ㅂ']}
SSIP    = {'cho': ['ㅅ', 'ㅆ'], 'jung': ['ㅣ', 'ㅢ', 'ㅟ'], 'jong': ['ㅂ']}
MI      = {'cho': ['ㅁ'],       'jung': ['ㅣ', 'ㅢ', 'ㅟ']}
CHIN    = {'cho': ['ㅊ'],       'jung': ['ㅣ', 'ㅢ', 'ㅟ'], 'jong': ['ㄴ']}
JANG    = {'cho': ['ㅈ', 'ㅉ'], 'jung': ['ㅏ', 'ㅑ'], 'jong': ['ㅇ']}
AE      = {'cho': ['ㅇ'],       'jung': ['ㅐ', 'ㅒ', 'ㅔ', 'ㅖ']}                 # 장애/니애미의 애
SSANG   = {'cho': ['ㅆ'],       'jung': ['ㅏ', 'ㅑ'], 'jong': ['ㅇ']}             # 쌍년/쌍놈의 쌍
GEOL    = {'cho': ['ㄱ'],       'jung': ['ㅓ', 'ㅕ'], 'jong': ['ㄹ']}             # 걸레의 걸
RE      = {'cho': ['ㄹ'],       'jung': ['ㅔ', 'ㅖ', 'ㅒ']}                       # 걸레의 레
CHANG   = {'cho': ['ㅊ'],       'jung': ['ㅏ', 'ㅐ', 'ㅒ', 'ㅔ', 'ㅑ', 'ㅖ'], 'jong': ['ㅇ']}
BO      = {'cho': ['ㅂ', 'ㅃ'], 'jung': ['ㅗ', 'ㅛ', 'ㅠ']}                       # 보지의 보
JI_SEX  = {'cho': ['ㅈ', 'ㅉ'], 'jung': ['ㅣ', 'ㅢ', 'ㅟ']}                       # 보지/자지의 지
JA      = {'cho': ['ㅈ', 'ㅉ'], 'jung': ['ㅏ', 'ㅑ', 'ㅘ', 'ㅠ']}                 # 자지의 자


def build_basic() -> dict:
    out: dict[str, dict] = {}

    def add(root: str, rules: list):
        out[root] = {'pos': 'NNG', 'variants': variants(root, rules)}

    def add_merged(root: str, forms: list[tuple[str, list]], extras: list[str] = None):
        """여러 기준어를 하나의 root 아래 병합. 니애미/니애비 그룹 전용."""
        collected: list[str] = []
        seen = {root}
        for word, rules in forms:
            for v in expand(word, rules):
                if v not in seen:
                    seen.add(v)
                    collected.append(v)
        for e in extras or []:
            if e not in seen:
                seen.add(e)
                collected.append(e)
        out[root] = {'pos': 'NNG', 'variants': collected}

    # 시발 계열
    add('시발',       [SI, BAL])
    add('개시발',     [GAE, SI, BAL])
    add('시발새끼',   [SI, BAL, SAE, KKI])
    add('시발년',     [SI, BAL, NONE])
    add('시발놈',     [SI, BAL, NONE])

    # 시부랄 계열
    add('시부랄',     [SI, NONE, BU_RAL])
    add('개시부랄',   [GAE, SI, NONE, BU_RAL])
    # 시부랄 특이 패턴: 붕알 계열 (글자 수는 같음, 자모 규칙 밖)
    out['시부랄']['variants'].append('시붕알')
    out['개시부랄']['variants'].append('개시붕알')

    # 병신 계열
    add('병신',       [BYEONG, SIN])
    add('개병신',     [GAE, BYEONG, SIN])
    add('병신새끼',   [BYEONG, SIN, SAE, KKI])
    add('병신년',     [BYEONG, SIN, NONE])
    add('병신놈',     [BYEONG, SIN, NONE])

    # 지랄 계열
    add('지랄',       [JI, RAL])
    add('개지랄',     [GAE, JI, RAL])

    # 새끼 / 개새끼
    add('새끼',       [SAE, KKI])
    add('개새끼',     [GAE, SAE, KKI])

    # 씹새끼 계열
    add('씹새끼',     [SSIP, SAE, KKI])

    # 좆 계열
    add('좆',         [NONE])
    add('좆밥',       [JOT, BAP])

    # 미친 계열
    add('미친새끼',   [MI, CHIN, SAE, KKI])
    add('미친년',     [MI, CHIN, NONE])
    add('개미친년',   [GAE, MI, CHIN, NONE])
    add('미친놈',     [MI, CHIN, NONE])
    add('개미친놈',   [GAE, MI, CHIN, NONE])

    # 장애 계열
    add('장애',       [JANG, AE])
    add('개장애',     [GAE, JANG, AE])
    add('장애새끼',   [JANG, AE, SAE, KKI])
    add('장애년',     [JANG, AE, NONE])
    add('개장애년',   [GAE, JANG, AE, NONE])
    add('장애놈',     [JANG, AE, NONE])
    add('개장애놈',   [GAE, JANG, AE, NONE])

    # 걸레 계열
    add('걸레새끼',   [GEOL, RE, SAE, KKI])
    add('걸레년',     [GEOL, RE, NONE])
    add('개걸레년',   [GAE, GEOL, RE, NONE])

    # 등신 계열 — 등신의 변형은 '신'에 대해서만
    add('등신',       [NONE, SIN])
    add('등신년',     [NONE, SIN, NONE])
    add('개등신년',   [GAE, NONE, SIN, NONE])
    add('등신놈',     [NONE, SIN, NONE])
    add('개등신놈',   [GAE, NONE, SIN, NONE])

    # 쌍년/쌍놈 계열
    add('쌍년',       [SSANG, NONE])
    add('개쌍년',     [GAE, SSANG, NONE])
    add('쌍놈',       [SSANG, NONE])
    add('개쌍놈',     [GAE, SSANG, NONE])

    # 창녀 계열
    add('창녀',       [CHANG, NONE])
    add('개창녀',     [GAE, CHANG, NONE])
    add('창녀새끼',   [CHANG, NONE, SAE, KKI])

    # 창남 계열
    add('창남',       [CHANG, NONE])
    add('개창남',     [GAE, CHANG, NONE])
    add('창남새끼',   [CHANG, NONE, SAE, KKI])

    # 성기류
    add('보지', [BO, JI_SEX])
    add('자지', [JA, JI_SEX])

    # 니애미/니애비 통합 root (예외적으로 글자수 섞임)
    add_merged(
        '니애미',
        forms=[
            ('니애미', [NONE, AE, NONE]),
            ('느그애미', [NONE, NONE, AE, NONE]),
            ('느금마', [NONE, NONE, NONE]),
        ],
        extras=['느금'],
    )
    add_merged(
        '니애비',
        forms=[
            ('니애비', [NONE, AE, NONE]),
            ('느그애비', [NONE, NONE, AE, NONE]),
            ('느금빠', [NONE, NONE, NONE]),
        ],
        extras=['느금'],
    )

    return out


# ─── 핵심어 기준 그룹 정렬 (가독성용) ───────────────────
GROUPS: list[list[str]] = [
    ['시발', '개시발', '시발새끼', '시발년', '시발놈'],
    ['시부랄', '개시부랄'],
    ['병신', '개병신', '병신새끼', '병신년', '병신놈'],
    ['지랄', '개지랄'],
    ['새끼', '개새끼'],
    ['씹새끼'],
    ['좆', '좆밥'],
    ['미친새끼', '미친년', '개미친년', '미친놈', '개미친놈'],
    ['장애', '개장애', '장애새끼', '장애년', '개장애년', '장애놈', '개장애놈'],
    ['걸레새끼', '걸레년', '개걸레년'],
    ['등신', '등신년', '개등신년', '등신놈', '개등신놈'],
    ['쌍년', '개쌍년', '쌍놈', '개쌍놈'],
    ['창녀', '개창녀', '창녀새끼'],
    ['창남', '개창남', '창남새끼'],
    ['보지'],
    ['자지'],
    ['니애미'],
    ['니애비'],
]


# ─── 커스텀 JSON 직렬화 (엔트리 1줄 포맷 + 그룹 공백) ────
def _entry_line(root: str, info: dict) -> str:
    variants_str = ', '.join(json.dumps(v, ensure_ascii=False) for v in info['variants'])
    pos_str = json.dumps(info['pos'], ensure_ascii=False)
    root_str = json.dumps(root, ensure_ascii=False)
    return f'    {root_str}: {{"pos": {pos_str}, "variants": [{variants_str}]}}'


def _dump_category(cat: dict) -> str:
    entries: list[tuple[str, bool]] = []  # (line, is_last_in_group)
    for group in GROUPS:
        for i, root in enumerate(group):
            if root not in cat:
                continue
            entries.append((_entry_line(root, cat[root]), i == len(group) - 1))

    out = ['{']
    for idx, (line, is_end_of_group) in enumerate(entries):
        is_last = idx == len(entries) - 1
        out.append(line + ('' if is_last else ','))
        if is_end_of_group and not is_last:
            out.append('')
    out.append('  }')
    return '\n'.join(out)


def dump_dic(data: dict) -> str:
    parts = ['{']
    keys = list(data.keys())
    for i, k in enumerate(keys):
        v = data[k]
        key_str = json.dumps(k, ensure_ascii=False)
        if isinstance(v, str):
            val_str = json.dumps(v, ensure_ascii=False)
            line = f'  {key_str}: {val_str}'
        elif isinstance(v, dict):
            line = f'  {key_str}: {_dump_category(v)}'
        else:
            line = f'  {key_str}: {json.dumps(v, ensure_ascii=False)}'
        if i < len(keys) - 1:
            line += ','
        parts.append(line)
    parts.append('}')
    return '\n'.join(parts) + '\n'


def main():
    base = Path(__file__).resolve().parents[1] / 'data' / 'dic.json'

    new_data = {
        '_comment': (
            'Kiwi user_word — 명사/복합명사 전용. variants 규칙: root 와 같은 글자 수, '
            '쌍자음 승급·ㅣ/ㅏ 중성 변형 위주. 합성어(새끼류/년·놈류)는 구성요소 variants 의 곱. '
            '예외: 니애미/니애비 통합 root 는 글자수 혼합 허용.'
        ),
        'basic': build_basic(),
    }

    base.write_text(dump_dic(new_data), encoding='utf-8')

    basic = new_data['basic']
    total_forms = sum(1 + len(v['variants']) for v in basic.values())
    print(f'[basic] roots={len(basic)} total_forms={total_forms}')
    print(f'전체 등록어 수: {total_forms}')
    print()
    print('── 샘플 ──')
    for k in ['시발', '시부랄', '새끼', '장애새끼', '걸레년', '니애미', '니애비', '보지', '자지', '창녀']:
        if k in basic:
            vs = basic[k]['variants']
            print(f'  {k} ({len(vs)}): {vs[:10]}{" ..." if len(vs) > 10 else ""}')


if __name__ == '__main__':
    main()
