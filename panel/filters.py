"""Search box, the kind filter, and the tag chips."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QWidget,
)

KINDS: tuple[tuple[str, str | None], ...] = (
    ("All", None),
    ("Video", "video"),
    ("Audio", "audio"),
    ("Image", "image"),
)


class SearchBar(QLineEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("search your stash…")
        self.setClearButtonEnabled(True)
        self.setObjectName("searchBar")


class KindFilter(QWidget):
    kindChanged = Signal(object)  # str | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for position, (label, kind) in enumerate(KINDS):
            button = QToolButton(self)
            button.setText(label)
            button.setCheckable(True)
            button.setProperty("kind", kind)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(f"{label}  (Ctrl+{position + 1})")
            if kind is None:
                button.setChecked(True)
            self.group.addButton(button, position)
            layout.addWidget(button)

        self.group.idClicked.connect(self._emit)

    def _emit(self, button_id: int) -> None:
        self.kindChanged.emit(KINDS[button_id][1])

    def select(self, position: int) -> None:
        button = self.group.button(position)
        if button is not None:
            button.setChecked(True)
            self._emit(position)


CHIP_LIMIT = 12


class TagChips(QWidget):
    """Checkable chips over the tags present in the current result set.

    Non-exclusive, unlike KindFilter: ticking two chips narrows to items
    carrying both, which is what `Query.tags` already means in search.py
    (`query.tags <= item.tags`).

    The chip list is rebuilt on every keystroke, so it must be cheap and it
    must not churn widgets when nothing changed -- hence the identity check in
    `set_tags` before touching the layout.
    """

    tagsChanged = Signal(object)  # frozenset[str]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(4)
        self._row.addStretch(1)
        self._selected: frozenset[str] = frozenset()
        self._buttons: dict[str, QToolButton] = {}
        self.hide()

    def selected(self) -> frozenset[str]:
        return self._selected

    def set_tags(self, ranked: list[tuple[str, int]]) -> None:
        """Rebuild from `top_tags` output, keeping the ticked ones visible.

        A selected tag is appended even when it falls out of the top slice --
        otherwise ticking a rare tag can remove the only chip able to untick it.
        """
        counts = dict(ranked)
        names = [tag for tag, _count in ranked[:CHIP_LIMIT]]
        names.extend(tag for tag in sorted(self._selected) if tag not in names)

        if names == list(self._buttons):
            for tag, button in self._buttons.items():
                button.setText(self._label(tag, counts.get(tag)))
            return
        self._rebuild(names, counts)

    @staticmethod
    def _label(tag: str, count: int | None) -> str:
        return f"{tag} · {count}" if count else tag

    def _rebuild(self, names: list[str], counts: dict[str, int]) -> None:
        while self._row.count() > 1:  # the trailing stretch stays
            entry = self._row.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons = {}

        for position, tag in enumerate(names):
            button = QToolButton(self)
            button.setText(self._label(tag, counts.get(tag)))
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setProperty("chip", True)
            # Check before connecting: setChecked emits toggled, and handling
            # that here would re-enter the query and rebuild this row mid-loop.
            button.setChecked(tag in self._selected)
            button.toggled.connect(lambda checked, t=tag: self._on_toggle(t, checked))
            self._row.insertWidget(position, button)
            self._buttons[tag] = button

        self.setVisible(bool(names))

    def _on_toggle(self, tag: str, checked: bool) -> None:
        updated = set(self._selected)
        if checked:
            updated.add(tag)
        else:
            updated.discard(tag)
        selected = frozenset(updated)
        if selected == self._selected:
            return
        self._selected = selected
        self.tagsChanged.emit(selected)
