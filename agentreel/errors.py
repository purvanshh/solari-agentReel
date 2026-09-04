"""AgentReel exception hierarchy."""

from __future__ import annotations

from typing import Optional


class AgentReelError(Exception):
    """Base error for all AgentReel failures."""

    def __init__(self, message: str, *, hint: Optional[str] = None) -> None:
        super().__init__(message)
        self.hint = hint

    def format(self) -> str:
        parts = [str(self)]
        if self.hint:
            parts.append("")
            parts.append(self.hint)
        return "\n".join(parts)


class AgentExecutionError(AgentReelError):
    """The user agent script exited with a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        exit_code: int,
        stderr: str = "",
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message, hint=hint)
        self.exit_code = exit_code
        self.stderr = stderr


class RecordingTimeoutError(AgentReelError):
    """Recording was not available after the configured poll attempts."""

    def __init__(
        self,
        message: str,
        *,
        session_id: str,
        attempts: int,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message, hint=hint)
        self.session_id = session_id
        self.attempts = attempts


class RecordingNotFoundError(AgentReelError):
    """Session was never recorded (or the ID is unknown)."""


class ConversionError(AgentReelError):
    """WebM/GIF conversion failed."""


class DependencyError(AgentReelError):
    """A required external dependency is missing or broken."""


class GitError(AgentReelError):
    """Git publishing failed."""


class ReadmeUpdateError(AgentReelError):
    """README patch failed."""
