"""nerv-filter CLI.

설치 후 ``nerv-filter`` 명령으로 사용.

Examples:
    $ nerv-filter analyze "이 시발 새끼야"
    $ nerv-filter analyze "텍스트" --security HIGH --json
    $ nerv-filter analyze --file comments.txt
    $ echo "이 시발" | nerv-filter analyze -
    $ nerv-filter info
"""
from __future__ import annotations

import json as json_lib
import sys

import click

from . import NervFilter, SecurityLevel, __version__


@click.group()
@click.version_option(version=__version__, package_name="nerv-filter")
def main() -> None:
    """NERV Filter — Korean profanity filter CLI."""


@main.command()
@click.argument("text", required=False)
@click.option(
    "--security",
    "-s",
    type=click.Choice(["LOW", "MEDIUM", "HIGH"], case_sensitive=False),
    default="MEDIUM",
    help="Security policy level",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON",
)
@click.option(
    "--file",
    "-f",
    type=click.File("r", encoding="utf-8"),
    help="Process file line by line (use '-' for stdin)",
)
def analyze(text: str | None, security: str, as_json: bool, file) -> None:
    """Analyze text or file for profanity."""
    flt = NervFilter(security_level=SecurityLevel(security.upper()))

    # 표준 입력 처리
    if text == "-":
        text = sys.stdin.read().strip()

    if file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            result = flt.analyze(line)
            _print_result(result, as_json)
    elif text:
        result = flt.analyze(text)
        _print_result(result, as_json)
    else:
        raise click.UsageError("Provide TEXT argument or use --file")


@main.command()
def info() -> None:
    """Display SDK and dictionary info."""
    flt = NervFilter()
    click.echo(f"nerv-filter version: {__version__}")
    click.echo(f"Dictionary size: {flt.get_dictionary_size():,} words")
    click.echo(f"Default security level: MEDIUM")


def _print_result(result, as_json: bool) -> None:
    """결과 출력."""
    if as_json:
        click.echo(json_lib.dumps(result.to_dict(), ensure_ascii=False))
    else:
        action = result.action.value
        # 액션별 색상
        color = {
            "NORMAL": "green",
            "REVIEW": "yellow",
            "PARTIAL_MASK": "yellow",
            "FULL_BLOCK": "red",
        }.get(action, "white")
        click.secho(f"[{action}] ", fg=color, nl=False)
        click.echo(result.masked_text)
        if result.detected_words:
            words = ", ".join(d.word for d in result.detected_words)
            click.secho(f"  detected: {words}", fg="cyan")


if __name__ == "__main__":
    main()
