"""ArcGIS Pro style ribbon replacing the QGIS menu bar and toolbars.

The ribbon borrows QGIS's own actions (looked up by ``objectName``), so it
needs no logic of its own; their icons and captions are swapped for Pro ones
through :class:`~.util.Changes`, which also reverts them.
"""

from qgis.core import QgsProject
from qgis.gui import QgsFloatingWidget, QgsStatusBar
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import (
    QApplication, QDockWidget, QFrame, QHBoxLayout, QLabel, QMenu,
    QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from .basemaps import gallery_menu
from .panes import reset_panes, reset_panes_menu
from .util import pro_icon, tr

LARGE, SMALL = 32, 16
# Core toolbars where plugins put their buttons; shown on the Add-ins tab.
ADDIN_HOSTS = {"mPluginToolBar", "mWebToolBar", "mDatabaseToolBar",
               "mVectorToolBar"}
# Tab -> groups -> items. An item is (action names, size, icon, caption):
# extra action names form the drop-down menu of the button, "dock:<name>"
# means the show/hide action of that dock widget, "gallery:basemaps" the
# basemap gallery and "panes:reset" the Reset Panes button.
RIBBON = [
    (tr("Map"), [
        (tr("Clipboard"), [
            ("mActionPasteFeatures", "L", "paste", tr("Paste")),
            ("mActionCutFeatures", "S", "cut", tr("Cut")),
            ("mActionCopyFeatures", "S", "copy", tr("Copy")),
        ]),
        (tr("Navigate"), [
            ("mActionPan", "L", "pan", tr("Explore")),
            ("mActionZoomFullExtent", "S", "full_extent", tr("Full Extent")),
            ("mActionZoomIn", "S", "zoom_in", tr("Zoom In")),
            ("mActionZoomOut", "S", "zoom_out", tr("Zoom Out")),
            ("mActionZoomLast", "S", "prev_extent", tr("Previous")),
            ("mActionZoomNext", "S", "next_extent", tr("Next")),
            ("mActionZoomToLayers", "S", "zoom_layer", tr("To Layer")),
            ("mActionShowBookmarks mActionNewBookmark", "L", "bookmarks",
             tr("Bookmarks")),
        ]),
        (tr("Layer"), [
            ("gallery:basemaps", "L", "basemap", tr("Basemap")),
            ("mActionDataSourceManager mActionAddOgrLayer "
             "mActionAddRasterLayer mActionAddDelimitedText "
             "mActionAddWmsLayer", "L", "add_data", tr("Add Data")),
            ("mActionAddOgrLayer", "S", "add_vector", tr("Vector")),
            ("mActionAddRasterLayer", "S", "add_raster", "Raster"),
            ("mActionAddWmsLayer", "S", "add_wms", "WMS/WMTS"),
        ]),
        (tr("Selection"), [
            ("mActionSelectFeatures mActionSelectPolygon "
             "mActionSelectFreehand mActionSelectRadius", "L", "select",
             tr("Select")),
            ("mActionSelectByExpression mActionSelectByForm", "L",
             "select_expression", tr("By Attributes")),
            ("mProcessingAlg_native:selectbylocation", "L",
             "select_location", tr("By Location")),
            ("mActionDeselectAll", "S", "clear_selection", tr("Clear")),
            ("mActionZoomToSelected", "S", "zoom_selected", tr("Zoom To")),
            ("mActionInvertSelection", "S", "invert_selection", tr("Invert")),
            ("mActionOpenTable", "S", "attribute_table",
             tr("Attribute Table")),
            ("mActionOpenFieldCalc", "S", "field_calculator",
             tr("Calculate Field")),
        ]),
        (tr("Inquiry"), [
            ("mActionIdentify", "L", "identify", tr("Identify")),
            ("mActionMeasure mActionMeasureArea mActionMeasureAngle", "L",
             "measure", tr("Measure")),
            ("mActionStatisticalSummary", "S", "statistics", tr("Statistics")),
            ("mActionMapTips", "S", "map_tips", tr("Map Tips")),
        ]),
        (tr("Labeling"), [
            ("mActionLabeling", "L", "labeling", tr("Labels")),
            ("mActionMoveLabel", "S", "label_move", tr("Move")),
        ]),
    ]),
    (tr("Insert"), [
        (tr("Project"), [
            ("mActionNewMapCanvas mActionNew3DMapCanvas", "L", "new_map",
             tr("New Map")),
            ("mActionNewPrintLayout mActionNewReport", "L", "new_layout",
             tr("New Layout")),
            ("mActionShowLayoutManager", "S", "layout_manager",
             tr("Layouts")),
        ]),
        (tr("Layers"), [
            ("mActionNewGeoPackageLayer mActionNewVectorLayer "
             "mActionNewMemoryLayer mActionNewVirtualLayer", "L",
             "new_layer", tr("New Layer")),
        ]),
        (tr("Styles"), [
            ("mActionStyleManager", "L", "style_manager", tr("Styles")),
        ]),
    ]),
    (tr("Analysis"), [
        (tr("Geoprocessing"), [
            ("toolboxAction", "L", "toolbox", tr("Tools")),
            ("modelerAction", "L", "model_builder", "ModelBuilder"),
            ("historyAction", "S", "history", tr("History")),
            ("mActionShowPythonDialog", "S", "python", "Python"),
        ]),
        (tr("Data"), [
            ("mActionOpenTable", "L", "attribute_table",
             tr("Attribute Table")),
            ("mActionOpenFieldCalc", "L", "field_calculator",
             tr("Calculate Field")),
        ]),
    ]),
    (tr("View"), [
        (tr("Windows"), [
            ("panes:reset", "L", "reset_panes", tr("Reset Panes")),
            ("dock:Layers", "S", "contents", tr("Contents")),
            ("dock:Browser", "S", "catalog", tr("Catalog")),
            ("dock:ProcessingToolbox", "S", "geoprocessing",
             tr("Geoprocessing")),
            ("dock:LayerStyling", "S", "symbology", tr("Symbology")),
            ("dock:LayerOrder", "S", "layer_order", tr("Layer Order")),
            ("dock:MessageLog", "S", "message_log", tr("Messages")),
        ]),
        (tr("View"), [
            ("mActionNew3DMapCanvas", "L", "map_3d", tr("3D View")),
            ("dock:Overview", "S", "overview", tr("Overview")),
            ("mActionTemporalController", "S", "temporal", tr("Time")),
        ]),
    ]),
    (tr("Edit"), [
        (tr("Clipboard"), [
            ("mActionPasteFeatures", "L", "paste", tr("Paste")),
            ("mActionCutFeatures", "S", "cut", tr("Cut")),
            ("mActionCopyFeatures", "S", "copy", tr("Copy")),
        ]),
        (tr("Manage Edits"), [
            ("mActionToggleEditing", "L", "edit", tr("Edit")),
            ("mActionSaveLayerEdits mActionSaveAllEdits", "L", "save_edits",
             tr("Save")),
            ("mActionRollbackEdits mActionRollbackAllEdits", "L",
             "discard_edits", tr("Discard")),
            ("mActionUndo", "S", "undo", tr("Undo")),
            ("mActionRedo", "S", "redo", tr("Redo")),
        ]),
        (tr("Snapping"), [
            ("EnableSnappingAction mActionSnappingOptions", "L", "snapping",
             tr("Snapping")),
        ]),
        (tr("Features"), [
            ("mActionAddFeature", "L", "create_feature", tr("Create")),
            ("mActionVertexTool", "L", "vertex_tool", tr("Modify")),
            ("mActionDeleteSelected", "L", "delete", tr("Delete")),
        ]),
        (tr("Tools"), [
            ("mActionMoveFeature", "S", "move", tr("Move")),
            ("mActionRotateFeature", "S", "rotate", tr("Rotate")),
            ("mActionScaleFeature", "S", "scale", tr("Scale")),
            ("mActionSplitFeatures", "S", "split", tr("Split")),
            ("mActionMergeFeatures", "S", "merge", tr("Merge")),
            ("mActionReshapeFeatures", "S", "reshape", tr("Reshape")),
        ]),
        (tr("Attributes"), [
            ("mActionMultiEditAttributes", "L", "multi_edit",
             tr("Attributes")),
        ]),
    ]),
    (tr("Share"), [
        (tr("Export"), [
            ("mActionSaveMapAsImage", "L", "export_image", tr("Image")),
            ("mActionSaveMapAsPdf", "L", "export_pdf", "PDF"),
            ("mActionDxfExport", "L", "export_image", "DXF"),
        ]),
        (tr("Print"), [
            ("mActionNewPrintLayout", "L", "print", tr("Layout")),
        ]),
    ]),
    (tr("Help"), [
        (tr("Help"), [
            ("mActionHelpContents", "L", "help", tr("Help")),
        ]),
        (tr("Customize"), [
            ("mActionManagePlugins", "L", "plugins", tr("Plugins")),
            ("mActionOptions", "L", "options", tr("Options")),
        ]),
    ]),
]

PROJECT_MENU = [
    ("mActionNewProject", "new_project"),
    ("mActionOpenProject", "open_project"),
    ("mActionSaveProject", "save_project"),
    ("mActionSaveProjectAs", "save_as"),
    ("mActionProjectProperties", "project_properties"),
    ("mActionOptions", "options"),
]


def find_action(win, name):
    """QGIS action by object name; ``dock:<name>`` is a dock's toggle."""
    if name.startswith("dock:"):
        dock = win.findChild(QDockWidget, name[5:])
        return dock.toggleViewAction() if dock else None
    return win.findChild(QAction, name)


def restyle(changes, action, icon, caption=None):
    """Give a QGIS action a Pro icon (and short caption) until undone."""
    changes.set(action, "icon", pro_icon(icon))
    if caption:
        changes.set(action, "iconText", caption)


def _button(iface, changes, names, size, icon, caption):
    large = size == "L"
    button = QToolButton(autoRaise=True)
    if names == "gallery:basemaps":
        button.setText(caption)
        button.setIcon(pro_icon(icon))
        button.setMenu(gallery_menu(iface, button))
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    elif names == "panes:reset":
        win = iface.mainWindow()
        button.setText(caption)
        button.setIcon(pro_icon(icon))
        button.clicked.connect(lambda: reset_panes(win))
        button.setMenu(reset_panes_menu(win, button))
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    else:
        win = iface.mainWindow()
        actions = [a for a in (find_action(win, n) for n in names.split())
                   if a]
        if not actions:
            return None
        restyle(changes, actions[0], icon, caption)
        button.setDefaultAction(actions[0])
        if len(actions) > 1:
            menu = QMenu(button)
            menu.addActions(actions)
            button.setMenu(menu)
            button.setPopupMode(
                QToolButton.ToolButtonPopupMode.MenuButtonPopup
            )
    side = LARGE if large else SMALL
    button.setIconSize(QSize(side, side))
    button.setToolButtonStyle(
        Qt.ToolButtonStyle.ToolButtonTextUnderIcon if large
        else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
    )
    return button


def _group(caption, buttons):
    """Ribbon group: large buttons, small ones stacked by three."""
    group = QWidget(objectName="ArcSkinRibbonGroup")
    row = QHBoxLayout()
    row.setSpacing(2)
    column = None
    for button, large in buttons:
        if large:
            row.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)
            column = None
            continue
        if column is None or column.count() == 3:
            column = QVBoxLayout()
            column.setSpacing(0)
            column.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.addLayout(column)
        column.addWidget(button)
    label = QLabel(caption, objectName="ArcSkinRibbonCaption")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box = QVBoxLayout(group)
    box.setContentsMargins(4, 2, 4, 0)
    box.setSpacing(0)
    box.addLayout(row)
    box.addStretch()
    box.addWidget(label)
    return group


def _tab(groups):
    page = QWidget()
    row = QHBoxLayout(page)
    row.setContentsMargins(2, 2, 2, 2)
    row.setSpacing(0)
    for caption, buttons in groups:
        row.addWidget(_group(caption, buttons))
        line = QFrame(objectName="ArcSkinRibbonSeparator")
        line.setFrameShape(QFrame.Shape.VLine)
        row.addWidget(line)
    row.addStretch()
    return page


def _addin_groups(bars):
    """One group per plugin toolbar: Pro's Add-ins tab."""
    groups = []
    for bar in bars:
        name = bar.objectName()
        if name.startswith("m") and name not in ADDIN_HOSTS:
            continue
        buttons = []
        for action in bar.actions():
            if action.isSeparator() or not action.text():
                continue
            button = QToolButton(autoRaise=True)
            button.setDefaultAction(action)
            button.setIconSize(QSize(LARGE, LARGE))
            buttons.append((button, True))
        if buttons:
            groups.append((bar.windowTitle(), buttons))
    return groups


def _project_button(changes, win, toggle_action):
    """Blue "Project" tab: project actions plus the hidden QGIS menu bar."""
    button = QToolButton(objectName="ArcSkinProjectButton", text=tr("Project"))
    menu = QMenu(button)
    for name, icon in PROJECT_MENU:
        action = find_action(win, name)
        restyle(changes, action, icon)
        menu.addAction(action)
    menu.addSeparator()
    qgis_menu = menu.addMenu(tr("QGIS Menu"))
    qgis_menu.addActions(win.menuBar().actions())
    menu.addAction(toggle_action)
    menu.addSeparator()
    menu.addAction(find_action(win, "mActionExit"))
    button.setMenu(menu)
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    return button


# Quick Access Toolbar, as in Pro's title row.
QUICK_ACCESS = ["mActionNewProject", "mActionOpenProject",
                "mActionSaveProject", "mActionUndo", "mActionRedo"]


def _drop_down_results(changes):
    """Open the locator's results below the search box, not above it (as
    they would from the status bar)."""
    for widget in QApplication.allWidgets():
        if widget.metaObject().className() == "QgsLocatorResultsView":
            popup = sip.cast(widget.parent(), QgsFloatingWidget)
            point = QgsFloatingWidget.AnchorPoint
            changes.set(popup, "anchorPoint", point.TopLeft)
            changes.set(popup, "anchorWidgetPoint", point.BottomLeft)


class TitleRow(QWidget):
    """Row above the ribbon, like Pro's title bar: Quick Access Toolbar and
    project name on the left, QGIS's locator centred (Command Search),
    messages on the right."""

    def __init__(self, iface, changes):
        super().__init__(objectName="ArcSkinTitleRow")
        win = iface.mainWindow()
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 2, 6, 2)
        row.setSpacing(2)
        for name in QUICK_ACCESS:
            action = find_action(win, name)
            if action:
                button = QToolButton(autoRaise=True)
                button.setDefaultAction(action)
                button.setToolButtonStyle(
                    Qt.ToolButtonStyle.ToolButtonIconOnly)
                row.addWidget(button)
        self.project = QLabel(objectName="ArcSkinProjectName")
        row.addWidget(self.project)
        row.addStretch(1)
        locator = win.statusBar().findChild(QWidget, "LocatorWidget")
        if locator:
            changes.set(locator, "minimumWidth", 420)
            changes.set(locator, "maximumWidth", 420)
            row.addWidget(locator)  # moved out of the hidden status bar
            changes.add(lambda: iface.statusBarIface().addPermanentWidget(
                locator, 0, QgsStatusBar.Anchor.AnchorLeft))
            _drop_down_results(changes)
        row.addStretch(1)
        messages = find_action(win, "dock:MessageLog")
        if messages:
            button = QToolButton(autoRaise=True)
            button.setDefaultAction(messages)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            row.addWidget(button)
        project = QgsProject.instance()
        for signal in (project.readProject, project.cleared,
                       project.fileNameChanged, project.titleChanged):
            signal.connect(self.show_project)
        self.show_project()

    def show_project(self, *_):
        project = QgsProject.instance()
        name = project.title() or project.baseName() or tr("Untitled")
        self.project.setText(name)


def build_ribbon(iface, changes, toggle_action):
    """Hide the menu bar and toolbars and put the ribbon in their place.

    Toolbar visibility is restored with the saved window state.
    """
    win = iface.mainWindow()
    bars = [b for b in win.findChildren(QToolBar) if b.parent() is win]
    for bar in bars:
        bar.hide()
    changes.set(win.menuBar(), "visible", False)
    tabs = QTabWidget(objectName="ArcSkinRibbon")
    tabs.setCornerWidget(_project_button(changes, win, toggle_action),
                         Qt.Corner.TopLeftCorner)
    for title, groups in RIBBON + [(tr("Add-ins"), None)]:
        if groups is None:
            built = _addin_groups(bars)
        else:
            built = []
            for caption, items in groups:
                buttons = [(b, item[1] == "L") for item in items
                           if (b := _button(iface, changes, *item))]
                if buttons:
                    built.append((caption, buttons))
        if built:
            tabs.addTab(_tab(built), title)
    ribbon = QToolBar("ArcSkin", win, objectName="ArcSkinRibbonBar")
    ribbon.setMovable(False)
    ribbon.setFloatable(False)
    frame = QWidget()
    stack = QVBoxLayout(frame)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(0)
    stack.addWidget(TitleRow(iface, changes))
    stack.addWidget(tabs)
    ribbon.addWidget(frame)
    win.addToolBar(Qt.ToolBarArea.TopToolBarArea, ribbon)
    changes.add(lambda: (win.removeToolBar(ribbon), ribbon.deleteLater()))
