"""Tests for the pluggable static gate adapter."""

import subprocess
from pathlib import Path

import pytest

import ppt_quality_review.gate as gate_module
from ppt_quality_review.gate import (
    GateResult,
    SubprocessStaticGate,
    run_quality_gate,
)


def _write_checker(scripts: Path, exit_code: int) -> Path:
    scripts.mkdir(parents=True, exist_ok=True)
    checker = scripts / "svg_quality_checker.py"
    checker.write_text(
        f"import sys\nprint('checker output')\nsys.exit({exit_code})\n"
    )
    return checker


def test_arg_dir_pass(tmp_path):
    scripts = tmp_path / "scripts"
    _write_checker(scripts, 0)
    result = SubprocessStaticGate(script_dir=scripts).run(tmp_path / "svg")
    assert result.passed is True
    assert result.exit_code == 0
    assert "checker output" in result.output


def test_arg_dir_blocking(tmp_path):
    scripts = tmp_path / "scripts"
    _write_checker(scripts, 1)
    result = SubprocessStaticGate(script_dir=scripts).run(tmp_path / "svg")
    assert result.passed is False
    assert result.exit_code == 1
    assert "checker output" in result.output


def test_env_var_resolution(tmp_path, monkeypatch):
    scripts = tmp_path / "envscripts"
    _write_checker(scripts, 0)
    monkeypatch.setenv("PPT_MASTER_SCRIPTS_DIR", str(scripts))
    result = SubprocessStaticGate().run(tmp_path / "svg")
    assert result.passed is True


def test_arg_beats_env(tmp_path, monkeypatch):
    good = tmp_path / "good"
    _write_checker(good, 0)
    bad = tmp_path / "bad"
    _write_checker(bad, 1)
    monkeypatch.setenv("PPT_MASTER_SCRIPTS_DIR", str(bad))
    result = SubprocessStaticGate(script_dir=good).run(tmp_path / "svg")
    assert result.passed is True


def test_env_dir_missing_script_soft_passes(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PPT_MASTER_SCRIPTS_DIR", str(empty))
    result = SubprocessStaticGate().run(tmp_path / "svg")
    assert result == GateResult(
        passed=True, exit_code=-1, output="static gate unavailable"
    )


def test_no_config_soft_passes(tmp_path, monkeypatch):
    monkeypatch.delenv("PPT_MASTER_SCRIPTS_DIR", raising=False)
    result = SubprocessStaticGate().run(tmp_path / "svg")
    assert result == GateResult(
        passed=True, exit_code=-1, output="static gate unavailable"
    )


def test_run_quality_gate_convenience(tmp_path):
    scripts = tmp_path / "scripts"
    _write_checker(scripts, 0)
    result = run_quality_gate(
        tmp_path / "svg", gate=SubprocessStaticGate(script_dir=scripts)
    )
    assert result.passed is True


def test_custom_script_name(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "my_checker.py").write_text("import sys\nsys.exit(0)\n")
    gate = SubprocessStaticGate(script_dir=scripts, script_name="my_checker.py")
    assert gate.run(tmp_path / "svg").passed is True


def test_timeout_propagates(tmp_path, monkeypatch):
    scripts = tmp_path / "scripts"
    _write_checker(scripts, 0)

    def _raise_timeout(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

    monkeypatch.setattr(gate_module.subprocess, "run", _raise_timeout)
    gate = SubprocessStaticGate(script_dir=scripts)
    with pytest.raises(subprocess.TimeoutExpired):
        gate.run(tmp_path / "svg")


def test_stderr_captured_in_output(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    checker = scripts / "svg_quality_checker.py"
    checker.write_text(
        "import sys\nsys.stderr.write('err detail\\n')\nsys.exit(1)\n"
    )
    result = SubprocessStaticGate(script_dir=scripts).run(tmp_path / "svg")
    assert result.passed is False
    assert "err detail" in result.output
