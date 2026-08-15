"""Pluggable static quality gate for slide projects.

Runs an external checker script over a directory as a subprocess.
Exit-code contract: 0 = pass (warnings tolerated), non-zero = blocking.

Point it at a checker via the constructor arg or the
``PPT_MASTER_SCRIPTS_DIR`` environment variable; any compatible checker
script works. Leave it unconfigured for a soft pass.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

DEFAULT_SCRIPT_NAME = "svg_quality_checker.py"
DEFAULT_TIMEOUT_S = 900


@dataclass
class GateResult:
    """Outcome of one static-gate run."""
    passed: bool
    exit_code: int  # -1 = gate unavailable (never ran)
    output: str


class StaticGate(Protocol):
    """Anything that can gate an SVG project directory."""

    def run(self, svg_dir: Path | str) -> GateResult: ...


class SubprocessStaticGate:
    """Static gate backed by an external checker script.

    Script-dir resolution order:
      1. ``script_dir`` constructor arg
      2. ``PPT_MASTER_SCRIPTS_DIR`` environment variable
      3. unavailable → :meth:`run` soft-passes with ``exit_code=-1``
    """

    def __init__(
        self,
        script_dir: Path | str | None = None,
        script_name: str = DEFAULT_SCRIPT_NAME,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ):
        if script_dir:
            self.script_dir: Path | None = Path(script_dir)
        else:
            override = os.getenv("PPT_MASTER_SCRIPTS_DIR", "")
            self.script_dir = Path(override) if override else None
        self.script_name = script_name
        self.timeout_s = timeout_s

    @property
    def available(self) -> bool:
        return (
            self.script_dir is not None
            and (self.script_dir / self.script_name).exists()
        )

    def run(self, svg_dir: Path | str) -> GateResult:
        if not self.available:
            logger.warning(
                "static gate unavailable (%s/%s not found); accepting",
                self.script_dir,
                self.script_name,
            )
            return GateResult(
                passed=True, exit_code=-1, output="static gate unavailable"
            )
        cmd = [
            sys.executable,
            str(self.script_dir / self.script_name),
            str(svg_dir),
        ]
        logger.info("Running static gate: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout_s
        )
        passed = proc.returncode == 0
        output = proc.stdout + proc.stderr
        if not passed:
            logger.error("static gate failed:\n%s", output)
        return GateResult(passed=passed, exit_code=proc.returncode, output=output)


def run_quality_gate(
    svg_dir: Path | str, gate: StaticGate | None = None
) -> GateResult:
    """Convenience entry point; default gate resolves via env var."""
    return (gate or SubprocessStaticGate()).run(svg_dir)
