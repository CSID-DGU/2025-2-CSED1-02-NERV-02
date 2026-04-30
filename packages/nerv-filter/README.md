# nerv-filter

Korean profanity filter with morphological analysis (Kiwi + Aho-Corasick).

> ⚠️ **Status**: Alpha — API may change before v1.0

## Features

- 🔤 **Kiwi 형태소 분석기** 기반 정규화
- ⚡ **Aho-Corasick** 빠른 사전 매칭
- 📚 **7,600+ 변형 사전** 패키지 동봉
- 🎚️ **3단계 보안 수준** (LOW / MEDIUM / HIGH)
- ➕ **사용자 화이트/블랙리스트** 동적 갱신
- 📦 **배치 처리** 지원

## Installation

```bash
pip install nerv-filter
```

## Quick Start

```python
from nerv_filter import filter_text

result = filter_text("이 시발 새끼야")
print(result.action)         # ModerationAction.PARTIAL_MASK
print(result.masked_text)    # "이 ** 새끼야"
```

For repeated use, prefer instance reuse to avoid Kiwi reloading:

```python
from nerv_filter import NervFilter, SecurityLevel

flt = NervFilter(security_level=SecurityLevel.HIGH)

for text in texts:
    result = flt.analyze(text)
    print(result.action, result.masked_text)
```

## Documentation

- [Quick Start](docs/quickstart.md)
- [API Reference](docs/api_reference.md)
- [Examples](docs/examples/)

## Development

```bash
# Local install
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## License

This project (nerv-filter) is licensed under MIT — see [LICENSE](LICENSE).

### Third-Party Dependencies

`nerv-filter` builds on top of the following open-source libraries, installed
via standard `pip install` as runtime dependencies. Their licenses apply
respectively:

| Dependency | License | Source |
|---|---|---|
| [kiwipiepy](https://github.com/bab2min/kiwipiepy) | LGPL v3 | © Minchul Lee (bab2min) |
| [pyahocorasick](https://github.com/WojciechMula/pyahocorasick) | BSD-3-Clause | © Wojciech Muła |

**LGPL v3 Notice**: kiwipiepy is dynamically linked via Python import.
Users may replace it with a different version by running
`pip install kiwipiepy==<version>`. The kiwipiepy source code is available
at <https://github.com/bab2min/kiwipiepy> under LGPL v3, and a copy of the
license can be obtained at <https://www.gnu.org/licenses/lgpl-3.0.html>.

This project does **not** redistribute kiwipiepy code or model data.
