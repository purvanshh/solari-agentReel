"""AgentReel — turn Solari browser-agent runs into shareable demos."""

from .session import recorded_session
from .errors import (
    AgentExecutionError,
    AgentReelError,
    ConversionError,
    DependencyError,
    GitError,
    ReadmeUpdateError,
    RecordingNotFoundError,
    RecordingTimeoutError,
)

__version__ = "1.0.0"

__all__ = [
    "recorded_session",
    "AgentReelError",
    "AgentExecutionError",
    "ConversionError",
    "DependencyError",
    "GitError",
    "ReadmeUpdateError",
    "RecordingNotFoundError",
    "RecordingTimeoutError",
    "__version__",
]
