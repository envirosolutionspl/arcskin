"""ArcSkin plugin: ArcGIS Pro look for QGIS, fully reverted on disable.

A theme is a directory under ``resources/themes/<name>/`` with two files:

* ``style.qss``     - Qt style sheet that may reference ``@name`` variables,
* ``variables.qss`` - ``@name: value;`` lines (same convention as QGIS themes).
"""

import re
from pathlib import Path

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QByteArray, QCoreApplication
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.PyQt.QtWidgets import QApplication, QToolBar

from .dialogs import WindowDresser
from .icon_theme import apply_icon_theme
from .mapview import frame_map
from .panes import arrange_panes
from .progress import Progress
from .ribbon import build_ribbon
from .symbology import ProSymbology
from .util import Changes, tr

PLUGIN_DIR = Path(__file__).resolve().parent
MENU_NAME = "&ArcSkin"
THEME = "pro_light"
VARIABLE_RE = re.compile(r"^\s*@([\w-]+)\s*:\s*(.+?)\s*;\s*$", re.MULTILINE)
# Window layout before the skin, kept in settings so that disabling the
# skin after a QGIS restart still brings the original toolbars back.
STATE_KEY = "arcskin/original_window_state"


def load_qss(theme: str) -> str:
    """Return the theme's style sheet with ``@name`` variables substituted.

    ``@icons`` expands to the plugin's icon directory, for ``url()`` values.
    """
    theme_dir = PLUGIN_DIR / "resources" / "themes" / theme
    variables = dict(
        VARIABLE_RE.findall(
            (theme_dir / "variables.qss").read_text(encoding="utf-8")
        )
    )
    variables["icons"] = (PLUGIN_DIR / "resources" / "icons").as_posix()
    qss = (theme_dir / "style.qss").read_text(encoding="utf-8")
    return re.sub(
        r"@([\w-]+)", lambda m: variables.get(m.group(1), m.group(0)), qss
    )


class ArcSkinPlugin:
    """QGIS plugin entry point: a checkable action toggles the Pro look."""

    def __init__(self, iface, translator=None):
        self.iface = iface
        self.translator = translator
        self.changes = None  # undo log while the skin is on

    def initGui(self):  # noqa: N802 (QGIS API name)
        icon = QIcon(str(PLUGIN_DIR / "resources" / "icons" / "icon.svg"))
        self.action = QAction(
            icon, tr("ArcSkin look"), self.iface.mainWindow(), checkable=True
        )
        self.action.toggled.connect(self.set_enabled)
        self.iface.addPluginToMenu(MENU_NAME, self.action)
        # The skin is on whenever the plugin is loaded. At QGIS start-up
        # wait until all plugins are loaded so their toolbars reach the
        # ribbon's Add-ins tab.
        if self.iface.mainWindow().isVisible():
            self.action.setChecked(True)
        else:
            self.iface.initializationCompleted.connect(
                lambda: self.action.setChecked(True)
            )

    def unload(self):
        # QGIS also unloads plugins when it quits; it freezes the map canvas
        # first. Then the skin is left recorded as on (icon theme, original
        # window state) for the next start instead of being reverted.
        try:
            if not self.iface.mapCanvas().isFrozen():
                self.set_enabled(False)
        finally:
            self.iface.removePluginMenu(MENU_NAME, self.action)
            if self.translator:
                QCoreApplication.removeTranslator(self.translator)

    def set_enabled(self, enabled: bool) -> None:
        """Apply the Pro look or restore the previous QGIS interface."""
        win = self.iface.mainWindow()
        settings = QgsSettings()
        if enabled and self.changes is None:
            if settings.value(STATE_KEY) is None:
                settings.setValue(STATE_KEY, win.saveState())
            changes = self.changes = Changes()
            # (relative duration, step): the bar moves with the time spent.
            steps = [
                (8, lambda: changes.set(QApplication.instance(), "styleSheet",
                                        load_qss(THEME))),
                (5, lambda: apply_icon_theme(self.iface, changes)),
                (1, lambda: WindowDresser(self.iface, changes)),
                (1, lambda: build_ribbon(self.iface, changes, self.action)),
                (1, lambda: arrange_panes(self.iface, changes)),
                (1, lambda: frame_map(self.iface, changes)),
                (3, lambda: ProSymbology(changes, self.iface.mapCanvas())),
            ]
            total = sum(weight for weight, _ in steps)
            progress = Progress(win, tr("Applying the ArcSkin look…"))
            try:
                done = 0
                for weight, step in steps:
                    step()
                    done += weight
                    progress.set(done / total)
            except Exception:
                # Half a skin is worse than none: back to plain QGIS, and
                # the switch shows off. QGIS reports the error.
                changes.undo()
                self.changes = None
                self._restore_window()
                self.action.blockSignals(True)
                self.action.setChecked(False)
                self.action.blockSignals(False)
                raise
            finally:
                progress.done()
        elif not enabled and self.changes is not None:
            progress = Progress(win, tr("Restoring the QGIS look…"))
            try:
                self.changes.undo(progress.set)
            finally:
                # Also after a failed step (undo reverts all the others):
                # the window state and the switch must match plain QGIS.
                progress.done()
                self.changes = None
                self._restore_window()

    def _restore_window(self):
        """Toolbars and panes as they were before the skin went on."""
        win = self.iface.mainWindow()
        settings = QgsSettings()
        state = settings.value(STATE_KEY)
        if isinstance(state, QByteArray):
            win.restoreState(state)
        settings.remove(STATE_KEY)
        bars = [b for b in win.findChildren(QToolBar)
                if b.parent() is win and b.actions()]
        if not any(b.isVisible() for b in bars):
            # The saved state was taken from a skinned window (e.g. after
            # a crash): fall back to showing QGIS's toolbars.
            for bar in bars:
                bar.show()
