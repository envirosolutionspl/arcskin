"""Pro-style frame around the map: view tabs above, a status strip below.

* :class:`ViewTabs` lists the main map, extra 2D/3D map views and open
  print layouts; a 2D view's tab shows it in place of the main map.
* :class:`MapFooter` replaces the QGIS status bar with the layout of Pro's
  map view status bar.
"""

import math
import re

from qgis.core import (
    Qgis, QgsLayerTree, QgsMapThemeCollection, QgsPointXY, QgsProject,
    QgsSettings, QgsVectorLayer,
)
from qgis.gui import QgsMapCanvas, QgsMapCanvasItem
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QLocale, QMargins, QSize, Qt, QTimer
from qgis.PyQt.QtGui import QAction, QActionGroup, QColor, QPen
from qgis.PyQt.QtWidgets import (
    QApplication, QComboBox, QDockWidget, QHBoxLayout, QLabel, QLineEdit,
    QMenu, QStackedWidget, QTabBar, QToolButton, QWidget,
)

from . import coords
from .util import pro_icon, separator, tool_button, tr

UNIT_KEY = "arcskin/coordinate_format"
# The project's own layer check states while Contents shows another map
# view: a theme in a collection of the plugin's own (never saved).
MAIN_STATE = "main"


class ViewTabs(QTabBar):
    """Tabs above the map for every map view and open layout, like Pro's.

    Extra 2D map views are hidden while the skin is on; their tab shows
    them in the main map instead (their map theme, also in Contents; each
    tab keeps its own extent, the current one at first), so one map is
    visible at a time.
    3D views and layouts keep their own windows, which their tab brings
    to the front. The cross closes a view; the main map's tab stays.
    """

    def __init__(self, iface):
        super().__init__(objectName="ArcSkinViewTabs", drawBase=False,
                         expanding=False)
        self.iface = iface
        self.views = []  # (title, icon, dock or window; None: main map)
        self.active = None  # map view dock shown in the main map
        self.extents = {}  # tab (dock, None: main map) -> its map extent
        self.hidden = []  # map view docks hidden by the tabs
        self.checks = None  # project's check states while a view is shown
        self.saved = None  # ...and as a map theme
        self.switching = False
        self.tabBarClicked.connect(self._activate)
        self.currentChanged.connect(self._paint_close_buttons)
        project = QgsProject.instance()
        project.writeProject.connect(self._project_checks)
        project.cleared.connect(self._forget)
        project.layerTreeRoot().visibilityChanged.connect(self._edited)
        timer = QTimer(self, interval=1000)
        timer.timeout.connect(self.refresh)
        timer.start()
        self.refresh()

    def _collect(self):
        main = self.iface.mapCanvas()
        views = [(tr("Map"), "new_map", None)]
        for canvas in self.iface.mapCanvases():
            dock = canvas.parent()
            while dock and not isinstance(dock, QDockWidget):
                dock = dock.parent()
            if canvas is not main and dock:
                views.append((dock.windowTitle(), "new_map", dock))
        for window in _windows_3d(self.iface.mainWindow()):
            views.append((window.windowTitle(), "map_3d", window))
        for designer in self.iface.openLayoutDesigners():
            views.append((designer.masterLayout().name(), "new_layout",
                          designer.window()))
        return views

    def refresh(self):
        # Keep the tabs' order: QGIS reorders its list of canvases.
        order = {view[2]: index for index, view in enumerate(self.views)}
        views = sorted(self._collect(),
                       key=lambda view: order.get(view[2], len(order)))
        for _, icon, dock in views[1:]:
            if icon == "new_map" and dock.isVisible():
                dock.hide()
                self.hidden.append(dock)
        windows = [view[2] for view in views]
        if self.active not in windows:  # closed
            self.show_map(None)
        if views == self.views:
            return
        self.views = views
        self.blockSignals(True)
        while self.count():
            self.removeTab(0)
        for index, (title, icon, window) in enumerate(views):
            self.addTab(pro_icon(icon), title)
            if window is not None:
                close = QToolButton(autoRaise=True, toolTip=tr("Close"))
                close.setIconSize(QSize(10, 10))
                close.clicked.connect(lambda _=False, w=window: w.close())
                self.setTabButton(index, QTabBar.ButtonPosition.RightSide,
                                  close)
        self.setCurrentIndex(windows.index(self.active))
        self.blockSignals(False)
        self._paint_close_buttons()

    def _paint_close_buttons(self, *_):
        """White cross on the (blue) current tab, grey on the others."""
        for index in range(self.count()):
            button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
            if button:
                button.setIcon(pro_icon("tab_close_white"
                                        if index == self.currentIndex()
                                        else "tab_close"))

    def _activate(self, index):
        if not 0 <= index < len(self.views):
            return
        _, icon, window = self.views[index]
        if window is None or icon == "new_map":
            self.show_map(window)
        else:  # 3D view or layout: its own window
            window.show()
            window.raise_()
            window.activateWindow()
            QTimer.singleShot(0, lambda: self.setCurrentIndex(
                [view[2] for view in self.views].index(self.active)))

    def show_map(self, dock):
        """Show map view ``dock`` (None: the main map) in the main map.

        Like Pro, Contents then shows that map: the view's map theme is
        applied to the layer tree, and check box changes update it. The
        project's own check states are kept aside meanwhile.
        """
        if dock is not None and self._view(dock) is None:
            dock = None  # the view was closed meanwhile
        project = QgsProject.instance()
        themes, root = project.mapThemeCollection(), project.layerTreeRoot()
        model = self.iface.layerTreeView().layerTreeModel()
        main = self.iface.mapCanvas()
        dirty = project.isDirty()
        self.switching = True
        if self.active is None:
            self.saved = QgsMapThemeCollection(project)
            self.saved.insert(MAIN_STATE,
                              themes.createThemeFromCurrentState(root, model))
            self.checks = _checks(root)
        else:
            self._save_view()
        self.extents[self.active] = main.extent()
        self.active = dock
        if dock:
            themes.applyTheme(self._theme(dock), root, model)
        elif self.checks is not None:
            self.saved.applyTheme(MAIN_STATE, root, model)
            self.saved = self.checks = None
        if dock in self.extents:  # first time: keep the current extent
            main.setExtent(self.extents[dock])
        self.switching = False
        # Switching tabs is no edit (QGIS marks check changes later on).
        project.setDirty(dirty)
        QTimer.singleShot(0, lambda: project.setDirty(dirty))
        main.refresh()
        label = self.iface.mainWindow().findChild(QLabel,
                                                  "ArcSkinContentsMap")
        if label:  # the map named at the top of Contents
            label.setText(dock.windowTitle() if dock else
                          project.title() or project.baseName() or tr("Map"))

    def _view(self, dock):
        """The map canvas inside a map view dock (None once it is gone)."""
        if dock is None or sip.isdeleted(dock):
            return None
        return dock.findChild(QgsMapCanvas)

    def _theme(self, dock):
        """The view's map theme; a view without one gets a new theme."""
        view = self._view(dock)
        themes = QgsProject.instance().mapThemeCollection()
        name = view.theme() or dock.windowTitle()
        if not themes.hasMapTheme(name):
            themes.insert(name, themes.createThemeFromCurrentState(
                QgsProject.instance().layerTreeRoot(),
                self.iface.layerTreeView().layerTreeModel()))
        view.setTheme(name)
        return name

    def _edited(self, *_):
        """A check box changed in Contents: remember it in the view."""
        if not self.switching:  # the user's change, not a theme applied
            self._save_view()

    def _save_view(self):
        """Store Contents' check boxes in the shown view's map theme."""
        view = self._view(self.active)
        themes = QgsProject.instance().mapThemeCollection()
        if not view or not themes.hasMapTheme(view.theme()):
            return
        themes.update(view.theme(), themes.createThemeFromCurrentState(
            QgsProject.instance().layerTreeRoot(),
            self.iface.layerTreeView().layerTreeModel()))

    def _forget(self):
        """The project was cleared: nothing to go back to."""
        self.active, self.extents = None, {}
        self.saved = self.checks = None

    def _project_checks(self, document):
        """Save the project's own check states, not the shown view's."""
        if self.checks is None:
            return

        def walk(element, path):
            child = element.firstChildElement()
            while not child.isNull():
                if child.tagName() == "layer-tree-layer":
                    key = child.attribute("id")
                elif child.tagName() == "layer-tree-group":
                    key = f"{path}/{child.attribute('name')}"
                    walk(child, key)
                else:
                    key = None
                if key in self.checks:
                    child.setAttribute("checked", "Qt::Checked"
                                       if self.checks[key]
                                       else "Qt::Unchecked")
                child = child.nextSiblingElement()

        trees = document.elementsByTagName("layer-tree-group")
        if trees.count():
            walk(trees.at(0).toElement(), "")

    def restore(self):
        """Back to the main map; hidden map views become panels again."""
        self.show_map(None)
        project = QgsProject.instance()
        project.writeProject.disconnect(self._project_checks)
        project.cleared.disconnect(self._forget)
        project.layerTreeRoot().visibilityChanged.disconnect(self._edited)
        for dock in self.hidden:
            if not sip.isdeleted(dock):
                dock.show()


def _windows_3d(win):
    """Docks and windows holding a 3D map view.

    Found by class name: iface.mapCanvases3D() crashes QGIS 4 (sip).
    """
    windows = [w for w in QApplication.topLevelWidgets()
               if w is not win and w.isVisible()]
    for container in win.findChildren(QDockWidget) + windows:
        inner = (container.widget() if isinstance(container, QDockWidget)
                 else container)
        if inner and any(w.metaObject().className() == "Qgs3DMapCanvasWidget"
                         for w in [inner] + inner.children()
                         if w.isWidgetType()):
            yield container


def _checks(group, path=""):
    """Check state of each layer (by id) and group (by path) under group."""
    checks = {}
    for node in group.children():
        if QgsLayerTree.isLayer(node):
            checks[node.layerId()] = node.itemVisibilityChecked()
        else:
            key = f"{path}/{node.name()}"
            checks[key] = node.itemVisibilityChecked()
            checks.update(_checks(node, key))
    return checks


class ScaleBox(QComboBox):
    """Editable map scale, written in full like Pro: "1:24 000"."""

    SCALES = [1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000,
              500000, 1000000, 2500000, 5000000, 10000000, 25000000,
              50000000, 100000000]

    def __init__(self, canvas):
        super().__init__(objectName="ArcSkinScale", editable=True,
                         minimumWidth=150)
        self.canvas = canvas
        # A fresh locale: QGIS may switch group separators off globally.
        self.locale = QLocale(QLocale().name())
        for scale in self.SCALES:
            self.addItem(self.text(scale), scale)
        self.activated.connect(
            lambda i: canvas.zoomScale(self.itemData(i)))
        self.lineEdit().returnPressed.connect(self.apply_text)
        canvas.scaleChanged.connect(self.show_scale)
        self.show_scale(canvas.scale())

    def text(self, scale):
        """'1:24 000' for a scale denominator."""
        return "1:" + self.locale.toString(round(scale))

    def show_scale(self, scale):
        """Follow the canvas."""
        self.setEditText(self.text(scale))

    def apply_text(self):
        """Zoom to the scale typed in, whatever its punctuation."""
        digits = re.sub(r"\D", "", self.currentText().split(":")[-1])
        if digits:
            self.canvas.zoomScale(int(digits))


class ReferenceGrid(QgsMapCanvasItem):
    """Light reference grid over the map, Pro's tray "Grid" toggle."""

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.setZValue(5)
        canvas.extentsChanged.connect(self.follow)
        self.follow()

    def follow(self):
        """Cover the canvas after it moved."""
        self.setRect(self.canvas.extent())
        self.update()

    def paint(self, painter, option=None, widget=None):
        """Lines every 1, 2 or 5 x 10^n map units, at least 60 px apart."""
        extent = self.canvas.extent()
        per_pixel = self.canvas.mapUnitsPerPixel()
        size = 10 ** math.floor(math.log10(60 * per_pixel))
        step = next(s for s in (size, size * 2, size * 5, size * 10)
                    if s / per_pixel >= 60)
        painter.setPen(QPen(QColor(120, 120, 120, 90), 1))
        origin = self.pos()
        x = math.ceil(extent.xMinimum() / step) * step
        while x <= extent.xMaximum():
            a = self.toCanvasCoordinates(QgsPointXY(x, extent.yMinimum()))
            b = self.toCanvasCoordinates(QgsPointXY(x, extent.yMaximum()))
            painter.drawLine(a - origin, b - origin)
            x += step
        y = math.ceil(extent.yMinimum() / step) * step
        while y <= extent.yMaximum():
            a = self.toCanvasCoordinates(QgsPointXY(extent.xMinimum(), y))
            b = self.toCanvasCoordinates(QgsPointXY(extent.xMaximum(), y))
            painter.drawLine(a - origin, b - origin)
            y += step


def _mirror(button, action):
    """Keep a tray toggle and a QGIS checkable action in sync."""
    if action is None:
        button.setEnabled(False)
        return
    button.setChecked(action.isChecked())
    button.toggled.connect(
        lambda on: action.isChecked() != on and action.trigger())
    action.toggled.connect(button.setChecked)


class MapFooter(QWidget):
    """Status strip under the map, laid out like Pro's map view status bar.

    Left: scale | tray toggles (snapping, grid, constraints) | coordinates
    you can type in, with a display-unit menu, and the coordinate system.
    Right: selected features (click to zoom) | clear selection | pause |
    drawing indicator that turns into refresh.
    """

    def __init__(self, iface):
        super().__init__(objectName="ArcSkinMapFooter")
        self.iface = iface
        self.canvas = canvas = iface.mapCanvas()
        win = iface.mainWindow()
        self.unit = QgsSettings().value(UNIT_KEY, "dd")
        if not coords.is_valid(self.unit):
            self.unit = "dd"
        self.scale = ScaleBox(canvas)

        snapping = tool_button("snapping", tr("Snapping"), True)
        _mirror(snapping, win.findChild(QAction, "EnableSnappingAction"))
        grid = tool_button("grid", tr("Grid"), True)
        self.grid = None
        grid.toggled.connect(self.show_grid)
        constraints = tool_button("constraints", tr("Constraints"), True)
        _mirror(constraints, win.findChild(QAction, "mEnableAction"))

        self.coords = QLineEdit(objectName="ArcSkinCoordinates",
                                toolTip=tr("Type coordinates and press Enter "
                                           "to go there"))
        self.coords.setMinimumWidth(240)
        self.coords.returnPressed.connect(self.go_to_typed)
        units = QToolButton(autoRaise=True, toolTip=tr("Display units"))
        units.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        units.setArrowType(Qt.ArrowType.NoArrow)
        units.setMenu(self._unit_menu(units))
        self.crs = QToolButton(autoRaise=True)
        self.crs.setIcon(pro_icon("coordinates"))
        self.crs.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.crs.clicked.connect(self._crs_dialog)

        self.selected = tool_button("select",
                                    tr("Zoom to selected features"))
        self.selected.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.selected.clicked.connect(self.zoom_to_selection)
        self.clear = tool_button("clear_selection", tr("Clear selection"))
        deselect = win.findChild(QAction, "mActionDeselectAll")
        if deselect:
            self.clear.clicked.connect(deselect.trigger)
        pause = tool_button("pause_drawing", tr("Pause drawing"), True)
        pause.toggled.connect(lambda on: canvas.setRenderFlag(not on))
        self.stop_button = tool_button("stop_drawing",
                                       tr("Drawing… click to cancel"))
        self.stop_button.clicked.connect(canvas.stopRendering)
        self.stop_button.hide()
        self.refresh_button = tool_button("refresh", tr("Refresh map"))
        self.refresh_button.clicked.connect(canvas.refreshAllLayers)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 1, 6, 1)
        row.setSpacing(4)
        for item in (self.scale, None, snapping, grid, constraints, None,
                     self.coords, units, None, self.crs):
            row.addWidget(item or separator())
        row.addStretch()
        for item in (self.selected, None, self.clear, None, pause, None,
                     self.stop_button, self.refresh_button):
            row.addWidget(item or separator())

        canvas.xyCoordinates.connect(self.show_coordinates)
        canvas.selectionChanged.connect(self.count_selection)
        # Bound methods (not lambdas): PyQt disconnects them when the
        # footer is deleted, so the canvas never calls into a dead widget.
        canvas.renderStarting.connect(self._drawing_started)
        canvas.mapCanvasRefreshed.connect(self._drawing_finished)
        project = QgsProject.instance()
        project.layersRemoved.connect(self.count_selection)
        project.crsChanged.connect(self.show_crs)
        self.count_selection()
        self.show_crs()
        self.show_coordinates(canvas.extent().center())

    # --- coordinates -----------------------------------------------------

    def _unit_menu(self, parent):
        """Display units: angular and grid ones, then linear ones."""
        menu = QMenu(parent)
        group = QActionGroup(menu)
        self.linear_actions = []
        for keys in (coords.ANGULAR, coords.LINEAR):
            for key in keys:
                action = menu.addAction(coords.unit_name(key))
                action.setCheckable(True)
                action.setChecked(key == self.unit)
                action.triggered.connect(
                    lambda _=False, k=key: self.set_unit(k))
                group.addAction(action)
                if keys is coords.LINEAR:
                    self.linear_actions.append(action)
            menu.addSeparator()
        menu.aboutToShow.connect(self._enable_linear_units)
        return menu

    def _enable_linear_units(self):
        """Linear units make sense for projected map coordinates only."""
        projected = self._map_crs().mapUnits() != Qgis.DistanceUnit.Degrees
        for action in self.linear_actions:
            action.setEnabled(projected)

    def _map_crs(self):
        return self.canvas.mapSettings().destinationCrs()

    def set_unit(self, unit):
        """Switch the display unit and remember it across sessions."""
        self.unit = unit
        QgsSettings().setValue(UNIT_KEY, unit)
        self.show_coordinates(self.canvas.extent().center())

    def show_coordinates(self, point):
        """Show the pointer's position in the display unit."""
        if self.coords.hasFocus():
            return  # the user is typing
        try:
            text = coords.format_point(point, self.unit, self._map_crs())
        except Exception:  # outside the valid area of the projection
            text = "—"
        self.coords.setText(text)

    def go_to_typed(self):
        """Centre the map on the coordinates typed into the footer."""
        try:
            point = coords.parse_point(self.coords.text(), self.unit,
                                       self._map_crs())
        except Exception:
            self.iface.messageBar().pushWarning(
                "ArcSkin", tr("Coordinates not recognized: {}").format(
                    self.coords.text()))
            return
        self.canvas.setCenter(point)
        self.canvas.refresh()
        self.coords.clearFocus()

    # --- other parts -----------------------------------------------------

    def show_grid(self, on):
        """Show or hide the reference grid over the map."""
        if on and self.grid is None:
            self.grid = ReferenceGrid(self.canvas)
        if self.grid is not None:
            self.grid.setVisible(on)

    def remove(self):
        """Take the footer away and leave the canvas as it was: drawing
        resumed if it was paused here, no grid."""
        if not self.canvas.renderFlag():
            self.canvas.setRenderFlag(True)
        if self.grid is not None:
            self.canvas.extentsChanged.disconnect(self.grid.follow)
            self.canvas.scene().removeItem(self.grid)
            self.grid = None
        self.hide()
        self.deleteLater()

    def _drawing_started(self):
        self.stop_button.show()
        self.refresh_button.hide()

    def _drawing_finished(self):
        self.stop_button.hide()
        self.refresh_button.show()

    def show_crs(self):
        """The project CRS as a button that opens its settings."""
        crs = QgsProject.instance().crs()
        self.crs.setText(crs.authid() or tr("No CRS"))
        self.crs.setToolTip(crs.description())

    def _crs_dialog(self):
        """Open the project CRS settings, as the QGIS status bar does."""
        button = self.iface.mainWindow().findChild(
            QToolButton, "mOntheFlyProjectionStatusButton")
        if button:
            button.click()

    @staticmethod
    def _selected_layers():
        return [layer for layer in QgsProject.instance().mapLayers().values()
                if isinstance(layer, QgsVectorLayer)
                and layer.selectedFeatureCount()]

    def zoom_to_selection(self):
        """Zoom to the selection of all layers, like Pro (not just one)."""
        layers = self._selected_layers()
        if layers:
            self.canvas.zoomToSelected(layers)

    def count_selection(self, *_):
        """Selected features in all layers, as Pro counts them."""
        count = sum(layer.selectedFeatureCount()
                    for layer in QgsProject.instance().mapLayers().values()
                    if isinstance(layer, QgsVectorLayer))
        self.selected.setText(tr("Selected features: {}").format(count))
        self.clear.setEnabled(count > 0)


def frame_map(iface, changes):
    """Put view tabs above and the footer below the map canvas.

    QGIS's own widgets stay in place: the map stack gets a top margin
    that the tab bar covers, and the footer takes a new grid row. The QGIS
    status bar is hidden; its search box moves to the ribbon (ribbon.py).
    """
    win = iface.mainWindow()
    central = win.centralWidget()
    stack = central.findChild(QStackedWidget)
    if stack is not None:
        tabs = ViewTabs(iface)
        tabs.setParent(stack)
        height = tabs.sizeHint().height()
        tabs.setGeometry(0, 0, 10000, height)  # clipped to the map's width
        tabs.show()
        changes.set(stack, "contentsMargins", QMargins(0, height, 0, 0))
        changes.add(lambda: (tabs.restore(), tabs.hide(),
                             tabs.deleteLater()))
        _lower_message_bar(iface.messageBar(), central.layout(), height,
                           changes)
    footer = MapFooter(iface)
    grid = central.layout()
    grid.addWidget(footer, grid.rowCount(), 0)
    changes.add(footer.remove)
    changes.set(win.statusBar(), "visible", False)


def _lower_message_bar(bar, grid, height, changes):
    """Keep the QGIS message bar under the view tabs.

    The bar shares the top grid cell with the map stack and overlays the
    map, so a message (plugin updates, an error) would cover the tabs.
    Row 0 is left to the tabs; the bar moves to row 1, which gets the
    rest of the map's height.
    """
    index = grid.indexOf(bar)
    if index < 0:
        # Not in this grid (another plugin moved it?): nothing to lower.
        # getItemPosition(-1) would hand back uninitialised numbers, and
        # addWidget with those crashed QGIS (access violation).
        return
    row, column, rows, columns = grid.getItemPosition(index)
    grid.removeWidget(bar)
    grid.addWidget(bar, 1, column, Qt.AlignmentFlag.AlignTop)
    grid.setRowMinimumHeight(0, height - grid.verticalSpacing())
    grid.setRowStretch(1, 1)

    def restore():
        grid.setRowStretch(1, 0)
        grid.setRowMinimumHeight(0, 0)
        grid.removeWidget(bar)
        grid.addWidget(bar, row, column, rows, columns)

    changes.add(restore)
