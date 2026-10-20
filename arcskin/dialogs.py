"""Windows QGIS opens while the skin is on: Pro icons and attribute table.

QGIS hands out icons it cached before the icon theme was active, so every
window that gets focus has its known QGIS icons swapped for the Pro ones.
Attribute tables also get Pro's toolbar order with captions ("Field: Add,
Calculate | Selection: Select By Attributes, Zoom To, Switch, Clear, Delete,
Copy", then the remaining QGIS tools) and Pro's footer; those changes are
undone for the tables still open when the skin is switched off.
"""

from qgis.core import QgsProject
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QLocale, QObject, Qt
from qgis.PyQt.QtGui import QAction, QFont, QGuiApplication
from qgis.PyQt.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QHBoxLayout, QLabel, QMenu,
    QSlider, QTableView, QToolBar, QToolButton, QWidget,
)

from .icon_theme import holders_in, swap_icons
from .util import Changes, pro_icon, separator, tool_button, tr

# Widget properties marking what was done: icons swapped in a window,
# an attribute table dressed.
ICONS_DONE = "arcskinIconsSwapped"
TABLE_DONE = "arcskinTableDressed"
# Pro's attribute table toolbar: (label, [(QGIS action, icon, caption)]).
TABLE_TOOLBAR = [
    (tr("Field:"), [
        ("mActionAddAttribute", "add_data", tr("Add")),
        ("mActionOpenFieldCalculator", "field_calculator", tr("Calculate")),
    ]),
    (tr("Selection:"), [
        ("mActionExpressionSelect", "select_expression",
         tr("Select By Attributes")),
        ("mActionZoomMapToSelectedRows", "zoom_selected", tr("Zoom To")),
        ("mActionInvertSelection", "invert_selection", tr("Switch")),
        ("mActionRemoveSelection", "clear_selection", tr("Clear")),
        ("mActionDeleteSelected", "delete", tr("Delete")),
        ("mActionCopySelectedRows", "copy", tr("Copy")),
    ]),
]
# QGIS's own footer buttons, replaced by TableFooter.
QGIS_FOOTER = ("mFilterButton", "mAttributeViewButton", "mTableViewButton")


class TableFooter(QWidget):
    """Bottom bar of Pro's attribute table.

    Left edge: show all / selected records, first / last record, "N of M
    selected". Right edge: filters (map extent, edited, all QGIS filters),
    zoom slider with percentage, refresh. Uses the dialog's own actions.
    """

    def __init__(self, dialog, layer):
        super().__init__(objectName="ArcSkinTableFooter")
        self.layer = layer
        self.table = dialog.findChild(QTableView, "mTableView")
        self.actions = {a.objectName(): a
                        for a in dialog.findChildren(QAction)}
        show_all = tool_button("show_all_records", tr("Show all records"),
                               True)
        show_selected = tool_button("show_selected_records",
                                    tr("Show selected records"), True)
        self.modes = QButtonGroup(self)
        for button, name in ((show_all, "mActionShowAllFilter"),
                             (show_selected, "mActionSelectedFilter")):
            self.modes.addButton(button)
            button.clicked.connect(lambda _=False, n=name: self._filter(n))
        show_all.setChecked(True)
        first = tool_button("first_record", tr("First record"))
        first.clicked.connect(lambda: self._go(0))
        last = tool_button("last_record", tr("Last record"))
        last.clicked.connect(lambda: self._go(-1))
        self.count = QLabel()
        extent = tool_button("filter_extent", tr("Filter by map extent"),
                             True)
        extent.toggled.connect(
            lambda on: self._filter("mActionVisibleFilter" if on
                                    else "mActionShowAllFilter"))
        edited = tool_button("filter_edited", tr("Filter edited records"),
                             True)
        edited.toggled.connect(
            lambda on: self._filter("mActionEditedFilter" if on
                                    else "mActionShowAllFilter"))
        more = tool_button("filter", tr("All filters"))
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button = dialog.findChild(QToolButton, "mFilterButton")
        if button:
            menu = QMenu(more)
            menu.addActions(button.actions())
            more.setMenu(menu)
        zoom_out = tool_button("zoom_out", tr("Zoom out"))
        zoom_in = tool_button("zoom_in", tr("Zoom in"))
        self.zoom = QSlider(Qt.Orientation.Horizontal, minimum=50,
                            maximum=200, value=100)
        self.zoom.setFixedWidth(110)
        self.percent = QLabel("100%", minimumWidth=40)
        zoom_out.clicked.connect(lambda: self.zoom.setValue(
            self.zoom.value() - 10))
        zoom_in.clicked.connect(lambda: self.zoom.setValue(
            self.zoom.value() + 10))
        self.zoom.valueChanged.connect(self.set_zoom)
        refresh = tool_button("refresh", tr("Refresh"))
        if "mActionReload" in self.actions:
            refresh.clicked.connect(self.actions["mActionReload"].trigger)
        self.base_font = QFont(self.table.font()) if self.table else None
        self.base_row = (self.table.verticalHeader().defaultSectionSize()
                         if self.table else 0)
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(2)
        for widget in (show_all, show_selected, separator(), first, last,
                       self.count):
            row.addWidget(widget)
        row.addStretch(1)  # what follows is aligned to the right edge
        for widget in (QLabel(tr("Filters:")), extent, edited, more,
                       separator(), zoom_out, self.zoom, zoom_in,
                       self.percent, refresh):
            row.addWidget(widget)
        for signal in (layer.selectionChanged, layer.featureAdded,
                       layer.featuresDeleted):
            signal.connect(self.update_count)
        self.update_count()

    def _filter(self, name):
        """Trigger one of the dialog's filter actions, if it has it."""
        if name in self.actions:
            self.actions[name].trigger()

    def _go(self, row):
        """Select row ``row`` of the table (-1: the last one)."""
        if self.table and self.table.model():
            model = self.table.model()
            index = model.index(row % max(model.rowCount(), 1), 0)
            self.table.scrollTo(index)
            self.table.setCurrentIndex(index)

    def set_zoom(self, value):
        """Scale the table's font and row height to ``value`` percent."""
        self.percent.setText(f"{value}%")
        if self.table and self.base_font:
            font = QFont(self.base_font)
            font.setPointSizeF(self.base_font.pointSizeF() * value / 100)
            self.table.setFont(font)
            self.table.verticalHeader().setDefaultSectionSize(
                round(self.base_row * value / 100))

    def update_count(self, *_):
        """"N of M selected" with the layer's current counts."""
        locale = QLocale()
        self.count.setText(tr("{} of {} selected").format(
            locale.toString(self.layer.selectedFeatureCount()),
            locale.toString(self.layer.featureCount())))

    def remove(self):
        """Take the footer out; the table keeps its size and font."""
        if sip.isdeleted(self):  # the table was closed (and deleted)
            return
        self.zoom.setValue(100)
        self.hide()
        self.deleteLater()


def dress_attribute_table(dialog, changes):
    """Pro's toolbar order, captions and footer for an attribute table."""
    bar = dialog.findChild(QToolBar, "mToolbar")
    if bar is None:
        return
    original = bar.actions()
    actions = {a.objectName(): a for a in original if a.objectName()}
    rest = list(original)
    bar.clear()  # also deletes the labels and separators added below
    changes.add(lambda: sip.isdeleted(bar)
                or (bar.clear(), bar.addActions(original)))
    for label, items in TABLE_TOOLBAR:
        bar.addWidget(QLabel(label, objectName="ArcSkinToolbarLabel"))
        for name, icon, caption in items:
            action = actions.get(name)
            if action is None:
                continue
            changes.set(action, "icon", pro_icon(icon))
            changes.set(action, "iconText", caption)
            bar.addAction(action)
            bar.widgetForAction(action).setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            rest.remove(action)
        bar.addSeparator()
    bar.addActions(rest)
    for table in dialog.findChildren(QTableView, "mTableView"):
        changes.set(table, "alternatingRowColors", True)
    layer_id = dialog.objectName().split("/", 1)[-1]
    layer = QgsProject.instance().mapLayer(layer_id)
    bottom = dialog.findChild(QHBoxLayout, "hboxLayout")
    if layer is None or bottom is None:
        return
    footer = TableFooter(dialog, layer)
    bottom.insertWidget(0, footer, 1)
    changes.add(footer.remove)
    for name in QGIS_FOOTER:
        widget = dialog.findChild(QWidget, name)
        if widget:
            changes.set(widget, "visible", False)


def dress_window(window, changes):
    """Pro icons for a QGIS window and Pro's layout for the attribute
    tables in it (a window is checked again at every focus, as attribute
    tables may be docked into the main window later)."""
    if window is None or sip.isdeleted(window):
        return
    if not window.property(ICONS_DONE):
        window.setProperty(ICONS_DONE, True)
        widgets = [window] + window.findChildren(QWidget)
        swap_icons(holders_in(widgets) + window.findChildren(QAction))
    for dialog in [window] + window.findChildren(QDialog):
        if (dialog.objectName().startswith("QgsAttributeTableDialog")
                and not dialog.property(TABLE_DONE)):
            dialog.setProperty(TABLE_DONE, True)
            changes.add(lambda d=dialog: sip.isdeleted(d)
                        or d.setProperty(TABLE_DONE, None))
            dress_attribute_table(dialog, changes)


class WindowDresser(QObject):
    """Dresses the open windows and each window when it gets focus.

    The main window's icons are handled by the icon theme, so only its
    attribute tables are dressed here. The changes made to attribute
    tables are undone when the skin is switched off.
    """

    def __init__(self, iface, changes):
        super().__init__(QApplication.instance())
        self.changes = Changes()
        win = iface.mainWindow()
        win.setProperty(ICONS_DONE, True)
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible():
                dress_window(widget, self.changes)
        QGuiApplication.instance().focusWindowChanged.connect(self.dress)
        changes.add(self.stop)

    def dress(self, qwindow):
        """Dress the widget behind the window that just got focus."""
        if qwindow is None:
            return
        for widget in QApplication.topLevelWidgets():
            if widget.windowHandle() is qwindow:
                dress_window(widget, self.changes)

    def stop(self):
        """Undo the attribute table changes, stop watching windows."""
        QGuiApplication.instance().focusWindowChanged.disconnect(self.dress)
        self.changes.undo()
        self.deleteLater()
