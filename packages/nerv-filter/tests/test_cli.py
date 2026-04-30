"""CLI 테스트."""
import json

from click.testing import CliRunner

from nerv_filter.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_analyze_basic():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "오늘 날씨"])
    assert result.exit_code == 0
    assert "NORMAL" in result.output


def test_analyze_curse():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "이 시발 진짜"])
    assert result.exit_code == 0
    # NORMAL 이외의 액션이어야 함
    assert "NORMAL" not in result.output.split("]")[0]


def test_analyze_json_output():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "이 시발", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert "action" in data
    assert "masked_text" in data


def test_analyze_security_high():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "병신", "--security", "HIGH"])
    assert result.exit_code == 0


def test_analyze_no_input():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze"])
    assert result.exit_code != 0
    assert "Provide TEXT" in result.output


def test_info():
    runner = CliRunner()
    result = runner.invoke(main, ["info"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()
    assert "Dictionary size" in result.output
