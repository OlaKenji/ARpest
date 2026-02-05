"""Helpers for bridging ROI UI controls to active figures."""

from __future__ import annotations

from typing import Callable, Optional, Tuple


class RoiController:
    """Adapter that exposes ROI controls for the active figure."""

    def __init__(self, tab) -> None:
        self._tab = tab
        self._listeners: list[Callable[[], None]] = []
        self._last_figure = None

    def attach_figure(self, figure) -> None:
        if figure is None or figure is self._last_figure:
            return
        self._last_figure = figure
        add_listener = getattr(figure, "add_roi_listener", None)
        if callable(add_listener):
            add_listener(self._notify_listeners)
        self._notify_listeners()

    def add_listener(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify_listeners(self) -> None:
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                continue

    def _current_figure(self):
        return getattr(self._tab, "figure", None)

    def is_supported(self) -> bool:
        figure = self._current_figure()
        return callable(getattr(figure, "set_roi_enabled", None))

    def is_enabled(self) -> bool:
        figure = self._current_figure()
        getter = getattr(figure, "is_roi_enabled", None)
        if callable(getter):
            return bool(getter())
        return False

    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        figure = self._current_figure()
        getter = getattr(figure, "get_roi_bounds", None)
        if callable(getter):
            return getter()
        return None

    def get_axis_labels(self) -> Optional[Tuple[str, str]]:
        figure = self._current_figure()
        getter = getattr(figure, "get_roi_axis_labels", None)
        if callable(getter):
            return getter()
        return None

    def set_enabled(self, enabled: bool) -> None:
        figure = self._current_figure()
        setter = getattr(figure, "set_roi_enabled", None)
        if callable(setter):
            setter(enabled)

    def reset(self) -> None:
        figure = self._current_figure()
        resetter = getattr(figure, "reset_roi", None)
        if callable(resetter):
            resetter()

    def clear(self) -> None:
        figure = self._current_figure()
        clearer = getattr(figure, "clear_roi", None)
        if callable(clearer):
            clearer()
        else:
            self.set_enabled(False)
