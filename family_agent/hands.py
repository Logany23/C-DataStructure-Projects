from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    code: int
    stdout: str
    stderr: str


class AgentHands:
    """Hands layer: execute shell and GitHub actions."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        self.cwd = cwd

    def run_shell(self, command: str, timeout: int = 120) -> CommandResult:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=self.cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip())

    def run_github_cli(self, gh_args: str, timeout: int = 120) -> CommandResult:
        # Keep it explicit for readability.
        return self.run_shell(f"gh {gh_args}", timeout=timeout)
