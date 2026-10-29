"""The skin's rules in the application style sheet, next to everybody else's.

QGIS has one style sheet for the whole application, and it is not ours
alone: QGIS itself sets it (UI theme, the font and toolbar spacing from
Options) and so do other plugins that style the interface. So the skin's
rules go in as a block between :data:`MARK_BEGIN`
and :data:`MARK_END`, in front of whatever is there, and switching the skin
off takes only that block out. What others put in the sheet stays, in
whatever order the plugins were switched on or off.

The block goes first so that a sheet set later wins on rules of equal
specificity: the skin is the base look, a decorative skin or the user's
font choice sits on top of it. The ``#ArcSkin…`` rules still win by
specificity.

Should somebody replace the whole sheet while the skin is on (QGIS does
when the interface font changes), Qt sends every widget a ``StyleChange``
event; the block is then put back on the next turn of the event loop. A
plugin that does the same for its own block only adds it when it is
missing, as this one does, so the two settle after at most two rounds.
"""

import re

from qgis.PyQt.QtCore import QEvent, QObject, QTimer
from qgis.PyQt.QtWidgets import QApplication

MARK_BEGIN = "/* arcskin: begin */"
MARK_END = "/* arcskin: end */"
BLOCK_RE = re.compile(re.escape(MARK_BEGIN) + ".*?" + re.escape(MARK_END)
                      + r"\n?", re.DOTALL)


def has_block(sheet):
    """Whether ``sheet`` holds the skin's block."""
    return MARK_BEGIN in sheet


def without_block(sheet):
    """``sheet`` with the skin's block taken out."""
    return BLOCK_RE.sub("", sheet)


def with_block(sheet, qss):
    """``sheet`` with ``qss`` as the skin's block in front of the rest.

    A block already there is replaced, never doubled.
    """
    rest = without_block(sheet)
    block = "\n".join((MARK_BEGIN, qss, MARK_END))
    return block + "\n" + rest if rest else block


class StyleSheetBlock(QObject):
    """Keep ``qss`` in the application style sheet as the skin's block
    until :meth:`remove`, also when something else replaces the sheet."""

    def __init__(self, win, qss):
        super().__init__(win)
        self.qss = qss
        self.active = True
        self.pending = False  # a resync is already scheduled
        self._apply()
        win.installEventFilter(self)

    def _apply(self):
        app = QApplication.instance()
        app.setStyleSheet(with_block(app.styleSheet(), self.qss))

    def eventFilter(self, watched, event):  # noqa: N802 (Qt API name)
        if event.type() == QEvent.Type.StyleChange and not self.pending:
            # Deferred: whoever set the sheet may still be at work, and
            # several changes in a row give one resync.
            self.pending = True
            QTimer.singleShot(0, self.resync)
        return False

    def resync(self):
        """Put the block back if the sheet was replaced without it."""
        self.pending = False
        if self.active and not has_block(QApplication.instance().styleSheet()):
            self._apply()

    def remove(self):
        """Take the block out and stop watching; the rest of the sheet,
        whoever put it there, stays."""
        self.active = False
        win = self.parent()
        if win is not None:
            win.removeEventFilter(self)
        app = QApplication.instance()
        app.setStyleSheet(without_block(app.styleSheet()))
        self.deleteLater()
