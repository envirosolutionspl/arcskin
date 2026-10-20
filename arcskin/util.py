"""Shared helpers: translation, Pro icons, small widgets, undo log."""

from pathlib import Path

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QFrame, QToolButton

ICON_DIR = Path(__file__).resolve().parent / "resources" / "icons" / "pro"


def tr(text):
    """Translate ``text`` (English) with the plugin's translator."""
    return QCoreApplication.translate("ArcSkin", text)


def pro_icon(name):
    """Return the bundled Pro-style icon ``name``."""
    return QIcon(str(ICON_DIR / f"{name}.svg"))


def tool_button(icon, tip, checkable=False):
    """Flat tool button with a Pro icon and a tooltip."""
    button = QToolButton(autoRaise=True, checkable=checkable, toolTip=tip)
    button.setIcon(pro_icon(icon))
    return button


def separator():
    """Thin vertical line between groups of footer buttons."""
    line = QFrame(objectName="ArcSkinFooterSeparator")
    line.setFrameShape(QFrame.Shape.VLine)
    return line


class Changes:
    """Undo log: each change to the QGIS interface records how to revert it."""

    def __init__(self):
        self._undo = []

    def set(self, obj, prop, value):
        """Call ``obj.set<Prop>(value)``, remembering the old value.

        The old value comes from ``obj.<prop>()`` or ``obj.is<Prop>()``.
        """
        cap = prop[0].upper() + prop[1:]
        getter = getattr(obj, prop, None) or getattr(obj, "is" + cap)
        setter = getattr(obj, "set" + cap)
        old = getter()
        setter(value)
        # Widgets may be deleted by QGIS before the undo (e.g. dialogs).
        self._undo.append(lambda: sip.isdeleted(obj) or setter(old))

    def add(self, undo):
        """Register a callable that reverts a change made by the caller."""
        self._undo.append(undo)

    def undo(self, progress=None):
        """Revert all changes, newest first; ``progress(fraction done)``.

        A step that fails does not stop the others: half a restore would
        leave QGIS without its menus and toolbars. The first error is
        raised once everything else has been reverted.
        """
        total = len(self._undo)
        error = None
        while self._undo:
            try:
                self._undo.pop()()
            except Exception as failure:  # noqa: BLE001 (re-raised below)
                error = error or failure
            if progress:
                progress(1 - len(self._undo) / total)
        if error is not None:
            raise error
