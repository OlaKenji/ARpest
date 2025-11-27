"""
Helpers for saving and loading complete application sessions.

Session files capture the list of dataset tabs together with their
file stacks and visualization settings so that work can be resumed later.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from ..models import FileStack
from .cursor.cursor_manager import CursorState


SESSION_FILE_EXTENSION = ".arpest"
SESSION_FORMAT_VERSION = 1


@dataclass
class SessionTabState:
    """
    Serializable state for a DatasetTab.

    Attributes:
        title: Title shown on the tab.
        file_stacks: All FileStack objects in the tab.
        current_index: Currently selected FileStack index.
        colormap: Active colormap name.
        color_limits: Current (vmin, vmax) tuple.
        integration_radius: Integration radius applied to plots.
        cursor_states: Per-file cursor positions.
        cut_states: Per-file cut anchor positions.
    """

    title: str
    file_stacks: list[FileStack]
    current_index: int
    colormap: str
    color_limits: tuple[Optional[float], Optional[float]]
    integration_radius: int
    cursor_states: list[Optional[CursorState]] = field(default_factory=list)
    cut_states: list[Optional[CursorState]] = field(default_factory=list)


@dataclass
class SessionData:
    """Container for everything stored inside a session file."""

    version: int
    tabs: list[SessionTabState]


def _coerce_color_limits(value: Optional[Sequence[Optional[float]]]) -> tuple[Optional[float], Optional[float]]:
    """Normalize various iterable inputs to a 2-tuple."""
    if value is None:
        return (None, None)
    items = list(value)
    if len(items) == 0:
        return (None, None)
    if len(items) == 1:
        return (items[0], None)
    return (items[0], items[1])


def _coerce_tab_state(state: SessionTabState | dict) -> SessionTabState:
    """Return a SessionTabState regardless of serialized structure."""
    if isinstance(state, SessionTabState):
        return state
    if isinstance(state, dict):
        return SessionTabState(
            title=state.get("title", "Session"),
            file_stacks=list(state.get("file_stacks", [])),
            current_index=int(state.get("current_index", 0)),
            colormap=state.get("colormap", ""),
            color_limits=_coerce_color_limits(state.get("color_limits")),
            integration_radius=int(state.get("integration_radius", 0)),
            cursor_states=list(state.get("cursor_states", [])),
            cut_states=list(state.get("cut_states", [])),
        )
    raise ValueError("Invalid tab state in session file")


def ensure_session_extension(path: Path) -> Path:
    """Return the path with the session extension appended if missing."""
    path = Path(path)
    if path.suffix != SESSION_FILE_EXTENSION:
        path = path.with_suffix(SESSION_FILE_EXTENSION)
    return path


def is_session_file(path: Path) -> bool:
    """Return True if the path most likely references a saved session."""
    return Path(path).suffix == SESSION_FILE_EXTENSION


def save_session(path: Path, session: SessionData) -> None:
    """Serialize the session to disk."""
    path = ensure_session_extension(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(session, fh, protocol=pickle.HIGHEST_PROTOCOL)


def load_session(path: Path) -> SessionData:
    """Load a previously saved session from disk."""
    with Path(path).open("rb") as fh:
        data = pickle.load(fh)

    if isinstance(data, SessionData):
        data.tabs = [_coerce_tab_state(tab) for tab in data.tabs]
        return data

    if isinstance(data, dict):
        # Basic backwards compatibility in case early files stored dicts.
        tabs = [_coerce_tab_state(tab) for tab in data.get("tabs", [])]
        version = data.get("version", SESSION_FORMAT_VERSION)
        return SessionData(version=version, tabs=tabs)

    raise ValueError("Invalid session file format")
