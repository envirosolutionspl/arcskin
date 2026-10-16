"""Windows QGIS opens while the skin is on: Pro icons and attribute table.

QGIS hands out icons it cached before the icon theme was active, so every
window that gets focus has its known QGIS icons swapped for the Pro ones.
The attribute table also gets Pro's toolbar order with captions:
"Field: Add, Calculate | Selection: Select By Attributes, Zoom To, Switch,
Clear, Delete, Copy", followed by the remaining QGIS tools.
"""

from qgis.core import QgsProject
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QLocale, QObject, Qt
from qgis.PyQt.QtGui import QAction, QFont, QGuiApplication
from qgis.PyQt.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QMenu,
    QSlider, QTableView, QToolBar, QToolButton, QWidget,
)

from .icon_theme import holders_in, swap_icons
from .util import pro_icon, tr

DRESSED = "arcskinDressed"
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


def _tool(icon, tip, checkable=False):
    button = QToolButton(autoRaise=True, checkable=checkable, toolTip=tip)
    button.setIcon(pro_icon(icon))
    return button


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
        action = {a.objectName(): a for a in dialog.findChildren(QAction)}
        self.filters = action
        show_all = _tool("show_all_records", tr("Show all records"), True)
        show_selected = _tool("show_selected_records",
                              tr("Show selected records"), True)
        self.modes = QButtonGroup(self)
        for button, name in ((show_all, "mActionShowAllFilter"),
                             (show_selected, "mActionSelectedFilter")):
            self.modes.addButton(button)
            button.clicked.connect(
                lambda _=False, n=name: self._filter(n))
        show_all.setChecked(True)
        first = _tool("first_record", tr("First record"))
        first.clicked.connect(lambda: self._go(0))
        last = _tool("last_record", tr("Last record"))
        last.clicked.connect(lambda: self._go(-1))
        self.count = QLabel()
        extent = _tool("filter_extent", tr("Filter by map extent"), True)
        extent.toggled.connect(
            lambda on: self._filter("mActionVisibleFilter" if on
                                    else "mActionShowAllFilter"))
        edited = _tool("filter_edited", tr("Filter edited records"), True)
        edited.toggled.connect(
            lambda on: self._filter("mActionEditedFilter" if on
                                    else "mActionShowAllFilter"))
        more = _tool("filter", tr("All filters"))
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button = dialog.findChild(QToolButton, "mFilterButton")
        if button:
            menu = QMenu(more)
            menu.addActions(button.actions())
            more.setMenu(menu)
        zoom_out = _tool("zoom_out", tr("Zoom out"))
        zoom_in = _tool("zoom_in", tr("Zoom in"))
        self.zoom = QSlider(Qt.Orientation.Horizontal, minimum=50,
                            maximum=200, value=100)
        self.zoom.setFixedWidth(110)
        self.percent = QLabel("100%", minimumWidth=40)
        zoom_out.clicked.connect(lambda: self.zoom.setValue(
            self.zoom.value() - 10))
        zoom_in.clicked.connect(lambda: self.zoom.setValue(
            self.zoom.value() + 10))
        self.zoom.valueChanged.connect(self.set_zoom)
        refresh = _tool("refresh", tr("Refresh"))
        if "mActionReload" in action:
            refresh.clicked.connect(action["mActionReload"].trigger)
        self.base_font = QFont(self.table.font()) if self.table else None
        self.base_row = (self.table.verticalHeader().defaultSectionSize()
                         if self.table else 0)
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(2)
        for widget in (show_all, show_selected, _separator(), first, last,
                       self.count):
            row.addWidget(widget)
        row.addStretch(1)  # what follows is aligned to the right edge
        for widget in (QLabel(tr("Filters:")), extent, edited, more,
                       _separator(), zoom_out, self.zoom, zoom_in,
                       self.percent, refresh):
            row.addWidget(widget)
        for signal in (layer.selectionChanged, layer.featureAdded,
                       layer.featuresDeleted):
            signal.connect(self.update_count)
        self.update_count()

    def _filter(self, name):
        if name in self.filters:
            self.filters[name].trigger()

    def _go(self, row):
        if self.table and self.table.model():
            model = self.table.model()
            index = model.index(row % max(model.rowCount(), 1), 0)
            self.table.scrollTo(index)
            self.table.setCurrentIndex(index)

    def set_zoom(self, value):
        self.percent.setText(f"{value}%")
        if self.table and self.base_font:
            font = QFont(self.base_font)
            font.setPointSizeF(self.base_font.pointSizeF() * value / 100)
            self.table.setFont(font)
            self.table.verticalHeader().setDefaultSectionSize(
                round(self.base_row * value / 100))

    def update_count(self, *_):
        locale = QLocale()
        self.count.setText(tr("{} of {} selected").format(
            locale.toString(self.layer.selectedFeatureCount()),
            locale.toString(self.layer.featureCount())))


def _separator():
    line = QFrame(objectName="ArcSkinFooterSeparator")
    line.setFrameShape(QFrame.Shape.VLine)
    return line


def dress_attribute_table(dialog):
    bar = dialog.findChild(QToolBar, "mToolbar")
    if bar is None:
        return
    actions = {a.objectName(): a for a in bar.actions() if a.objectName()}
    rest = [a for a in bar.actions()]
    bar.clear()
    for label, items in TABLE_TOOLBAR:
        bar.addWidget(QLabel(label, objectName="ArcSkinToolbarLabel"))
        for name, icon, caption in items:
            action = actions.get(name)
            if action is None:
                continue
            action.setIcon(pro_icon(icon))
            action.setIconText(caption)
            bar.addAction(action)
            bar.widgetForAction(action).setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            rest.remove(action)
        bar.addSeparator()
    bar.addActions(rest)
    for table in dialog.findChildren(QTableView, "mTableView"):
        table.setAlternatingRowColors(True)
    layer_id = dialog.objectName().split("/", 1)[-1]
    layer = QgsProject.instance().mapLayer(layer_id)
    bottom = dialog.findChild(QHBoxLayout, "hboxLayout")
    if layer is None or bottom is None:
        return
    footer = TableFooter(dialog, layer)  # first: hide QGIS's only if built
    bottom.insertWidget(0, footer, 1)
    for name in ("mFilterButton", "mAttributeViewButton",
                 "mTableViewButton"):
        widget = dialog.findChild(QWidget, name)
        if widget:
            widget.hide()


def dress_window(window):
    """Pro icons (and layout, for attribute tables) for a QGIS window."""
    if window is None or sip.isdeleted(window) or window.property(DRESSED):
        return
    window.setProperty(DRESSED, True)
    widgets = [window] + window.findChildren(QWidget)
    swap_icons(holders_in(widgets) + window.findChildren(QAction))
    for dialog in [window] + window.findChildren(QDialog):
        if dialog.objectName().startswith("QgsAttributeTableDialog"):
            dress_attribute_table(dialog)


class WindowDresser(QObject):
    """Dresses each window when it first gets focus."""

    def __init__(self, changes):
        app = QApplication.instance()
        super().__init__(app)
        QGuiApplication.instance().focusWindowChanged.connect(self.dress)
        changes.add(self.stop)

    def dress(self, qwindow):
        if qwindow is None:
            return
        for widget in QApplication.topLevelWidgets():
            if widget.windowHandle() is qwindow:
                dress_window(widget)

    def stop(self):
        QGuiApplication.instance().focusWindowChanged.disconnect(self.dress)
        self.deleteLater()
