"""Progress box shown while the skin is switched on or off (a few seconds).

The work runs in the GUI thread, so the box repaints itself directly
between steps (no event processing: nothing else runs meanwhile). Its look
comes from the active style sheet: Pro's thin blue bar while the skin is on.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QApplication, QFrame, QLabel, QProgressBar, QVBoxLayout,
)


class Progress(QFrame):
    """Box in the middle of ``window`` with a message and a progress bar."""

    def __init__(self, window, text):
        super().__init__(window, objectName="ArcSkinProgress",
                         frameShape=QFrame.Shape.StyledPanel,
                         autoFillBackground=True)
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 12, 16, 14)
        box.addWidget(QLabel(text))
        self.bar = QProgressBar(maximum=100, textVisible=False)
        box.addWidget(self.bar)
        self.setFixedWidth(320)
        self.adjustSize()
        self.move((window.width() - self.width()) // 2,
                  (window.height() - self.height()) // 2)
        self.show()
        self.raise_()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.set(0)

    def set(self, fraction):
        """Show ``fraction`` (0-1) of the work done."""
        value = round(fraction * 100)
        if value != self.bar.value() or not fraction:
            self.bar.setValue(value)
            self.repaint()

    def done(self):
        QApplication.restoreOverrideCursor()
        self.hide()
        self.deleteLater()
