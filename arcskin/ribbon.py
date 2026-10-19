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
    QScrollArea, QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from .basemaps import gallery_menu
from .panes import reset_panes, reset_panes_menu
from .util import pro_icon, tr

LARGE, SMALL = 32, 16
# Core toolbars where plugins put their buttons; shown on the Add-ins tab.
ADDIN_HOSTS = {"mPluginToolBar", "mWebToolBar", "mDatabaseToolBar",
               "mVectorToolBar"}
# Tab -> groups -> items. An item is (action names, size, icon, caption):
# extra action names form the drop-down menu of the button, "menu:<name>"
# puts that QGIS menu (or a QGIS tool button's) there instead, "dock:<name>"
# means the show/hide action of that dock widget, "shapes:<kind>" the shape
# digitizing tools of that kind, "gallery:basemaps" the basemap gallery and
# "panes:reset" the Reset Panes button.
RIBBON = [
    (tr("Map"), [
        (tr("Clipboard"), [
            ("mActionPasteFeatures menu:mMenuPasteAs", "L", "paste",
             tr("Paste")),
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
            ("mActionDraw", "S", "refresh", tr("Refresh")),
            ("mActionShowBookmarks mActionNewBookmark", "L", "bookmarks",
             tr("Bookmarks")),
        ]),
        (tr("Layer"), [
            ("gallery:basemaps", "L", "basemap", tr("Basemap")),
            ("mActionDataSourceManager menu:mAddLayerMenu", "L", "add_data",
             tr("Add Data")),
            ("mActionAddOgrLayer", "S", "add_vector", tr("Vector")),
            ("mActionAddRasterLayer", "S", "add_raster", "Raster"),
            ("mActionAddWmsLayer", "S", "add_wms", "WMS/WMTS"),
        ]),
        (tr("Selection"), [
            ("mActionSelectFeatures menu:mMenuSelect", "L", "select",
             tr("Select")),
            ("mActionSelectByExpression mActionSelectByForm", "L",
             "select_expression", tr("By Attributes")),
            ("mProcessingAlg_native:selectbylocation "
             "mProcessingAlg_native:selectwithindistance", "L",
             "select_location", tr("By Location")),
            ("mActionDeselectAll", "S", "clear_selection", tr("Clear")),
            ("mActionZoomToSelected mActionPanToSelected", "S",
             "zoom_selected", tr("Zoom To")),
            ("mActionInvertSelection", "S", "invert_selection", tr("Invert")),
            ("mActionOpenTable menu:mMenuFilterTable", "S",
             "attribute_table",
             tr("Attribute Table")),
            ("mActionOpenFieldCalc", "S", "field_calculator",
             tr("Calculate Field")),
        ]),
        (tr("Inquiry"), [
            ("mActionIdentify", "L", "identify", tr("Identify")),
            ("mActionMeasure mActionMeasureArea mActionMeasureAngle "
             "mActionMeasureBearing", "L",
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
            ("mActionNewGeoPackageLayer menu:mNewLayerMenu", "L",
             "new_layer", tr("New Layer")),
        ]),
        (tr("Decorations"), [
            ("menu:mMenuDecorations", "L", "decorations", tr("Decorations")),
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
            ("dock:ResultsViewer", "S", "processing_results", tr("Results")),
        ]),
        (tr("Tools"), [
            ("menu:mVectorMenu", "L", "vector_tools", tr("Vector")),
            ("menu:mRasterMenu", "L", "raster_tools", "Raster"),
            ("menu:mDatabaseMenu", "S", "database", tr("Database")),
            ("menu:mWebMenu", "S", "web", "Web"),
            ("menu:mMeshMenu", "S", "mesh", tr("Mesh")),
        ]),
        (tr("Data"), [
            ("mActionOpenTable menu:mMenuFilterTable", "L",
             "attribute_table",
             tr("Attribute Table")),
            ("mActionOpenFieldCalc", "L", "field_calculator",
             tr("Calculate Field")),
        ]),
    ]),
    (tr("View"), [
        (tr("Windows"), [
            ("panes:reset", "L", "reset_panes", tr("Reset Panes")),
            ("menu:mPanelMenu", "L", "panes", tr("Panes")),
            ("dock:Layers", "S", "contents", tr("Contents")),
            ("dock:Browser", "S", "catalog", tr("Catalog")),
            ("dock:ProcessingToolbox", "S", "geoprocessing",
             tr("Geoprocessing")),
            ("dock:LayerStyling", "S", "symbology", tr("Symbology")),
            ("dock:LayerOrder", "S", "layer_order", tr("Layer Order")),
            ("dock:MessageLog", "S", "message_log", tr("Messages")),
            ("dock:AdvancedDigitizingTools", "S", "advanced_digitizing",
             tr("Advanced Digitizing")),
            ("menu:mToolbarMenu", "S", "toolbars", tr("Toolbars")),
        ]),
        (tr("View"), [
            ("mActionNew3DMapCanvas menu:m3DMapViewsMenu", "L", "map_3d",
             tr("3D View")),
            ("dock:Overview", "S", "overview", tr("Overview")),
            ("mActionTemporalController", "S", "temporal", tr("Time")),
        ]),
    ]),
    (tr("Edit"), [
        (tr("Clipboard"), [
            ("mActionPasteFeatures menu:mMenuPasteAs", "L", "paste",
             tr("Paste")),
            ("mActionCutFeatures", "S", "cut", tr("Cut")),
            ("mActionCopyFeatures", "S", "copy", tr("Copy")),
        ]),
        (tr("Manage Edits"), [
            ("mActionToggleEditing", "L", "edit", tr("Edit")),
            ("mActionSaveLayerEdits menu:AllEditsMenu", "L", "save_edits",
             tr("Save")),
            ("mActionRollbackEdits mActionRollbackAllEdits", "L",
             "discard_edits", tr("Discard")),
            ("mActionUndo", "S", "undo", tr("Undo")),
            ("mActionRedo", "S", "redo", tr("Redo")),
        ]),
        (tr("Snapping"), [
            ("EnableSnappingAction menu:SnappingTypeButton", "L", "snapping",
             tr("Snapping")),
            ("menu:SnappingModeButton", "S", "snap_mode", tr("Mode")),
            ("EnableTracingAction", "S", "tracing", tr("Tracing")),
            ("TopologicalEditingAction", "S", "topological_editing",
             tr("Topology")),
            ("IntersectionSnappingAction", "S", "snap_intersection",
             tr("Intersections")),
            ("SelfSnappingAction", "S", "self_snapping", tr("Self-snapping")),
            ("menu:AvoidIntersectionsModeButton", "S", "avoid_overlap",
             tr("Overlap")),
            ("dock:AdvancedDigitizingTools", "S", "advanced_digitizing",
             tr("Advanced Digitizing")),
        ]),
        (tr("Features"), [
            ("mActionAddFeature mActionDigitizeWithSegment "
             "mActionDigitizeWithCurve mActionStreamDigitize "
             "mActionDigitizeWithBezier mActionDigitizeWithNurbs "
             "mActionDigitizeShape", "L", "create_feature", tr("Create")),
            ("mActionVertexTool mActionVertexToolActiveLayer "
             "dock:VertexEditor", "L", "vertex_tool", tr("Modify")),
            ("mActionDeleteSelected", "L", "delete", tr("Delete")),
        ]),
        (tr("Shapes"), [
            ("shapes:circle", "S", "circle", tr("Circle")),
            ("shapes:ellipse", "S", "ellipse", tr("Ellipse")),
            ("shapes:rectangle", "S", "rectangle", tr("Rectangle")),
            ("shapes:regular-polygon", "S", "regular_polygon",
             tr("Polygon")),
        ]),
        (tr("Tools"), [
            ("mActionMoveFeature mActionMoveFeatureCopy "
             "mActionFeatureArray", "S", "move", tr("Move")),
            ("mActionRotateFeature", "S", "rotate", tr("Rotate")),
            ("mActionScaleFeature", "S", "scale", tr("Scale")),
            ("mActionSplitFeatures", "S", "split", tr("Split")),
            ("mActionMergeFeatures", "S", "merge", tr("Merge")),
            ("mActionReshapeFeatures", "S", "reshape", tr("Reshape")),
        ]),
        (tr("Modify"), [
            ("mActionAddPart", "S", "add_part", tr("Add Part")),
            ("mActionDeletePart", "S", "delete_part", tr("Delete Part")),
            ("mActionSplitParts", "S", "split_parts", tr("Split Parts")),
            ("mActionAddRing", "S", "add_ring", tr("Add Ring")),
            ("mActionFillRing", "S", "fill_ring", tr("Fill Ring")),
            ("mActionDeleteRing", "S", "delete_ring", tr("Delete Ring")),
            ("mActionSimplifyFeature", "S", "simplify", tr("Simplify")),
            ("mActionOffsetCurve", "S", "offset", tr("Offset")),
            ("mActionChamferFillet", "S", "fillet", tr("Fillet")),
            ("mActionTrimExtendFeature", "S", "trim_extend",
             tr("Trim/Extend")),
            ("mActionReverseLine", "S", "reverse_line", tr("Reverse")),
            ("mActionMergeFeatureAttributes", "S", "merge_attributes",
             tr("Merge Attributes")),
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
            ("mActionHelpContents menu:mHelpMenu", "L", "help",
             tr("Help")),
        ]),
        (tr("Customize"), [
            ("mActionManagePlugins menu:mPluginMenu", "L", "plugins",
             tr("Plugins")),
            ("mActionOptions", "L", "options", tr("Options")),
        ]),
    ]),
]

# Blue Project button: (action name or "menu:<QGIS menu>", Pro icon or None
# for QGIS's own).
PROJECT_MENU = [
    ("mActionNewProject", "new_project"),
    ("mActionOpenProject", "open_project"),
    ("menu:mRecentProjectsMenu", None),
    ("mActionSaveProject", "save_project"),
    ("mActionSaveProjectAs", "save_as"),
    ("mActionRevertProject", None),
    ("mActionCloseProject", None),
    ("menu:menuImport_Export", None),
    ("mActionProjectProperties", "project_properties"),
    ("mActionOptions", "options"),
    ("menu:mSettingsMenu", None),
]
# Quick Access Toolbar, as in Pro's title row.
QUICK_ACCESS = ["mActionNewProject", "mActionOpenProject",
                "mActionSaveProject", "mActionUndo", "mActionRedo"]


def find_action(win, name):
    """QGIS action by object name; ``dock:<name>`` is a dock's toggle."""
    if name.startswith("dock:"):
        dock = win.findChild(QDockWidget, name[5:])
        return dock.toggleViewAction() if dock else None
    return win.findChild(QAction, name)


def find_menu(win, name):
    """QGIS menu by object name, or the menu of a QGIS tool button."""
    menu = win.findChild(QMenu, name)
    if not menu and (button := win.findChild(QToolButton, name)):
        menu = button.menu()
    return menu


def _shape_actions(win, kind):
    """Shape digitizing tools of a kind ("circle", ...): QGIS gives them no
    object names, only their shape id as data."""
    bar = win.findChild(QToolBar, "mShapeDigitizeToolBar")
    buttons = bar.findChildren(QToolButton) if bar else []
    return [a for b in buttons if b.menu() for a in b.menu().actions()
            if str(a.data()).startswith(kind)]


def restyle(changes, action, icon, caption=None):
    """Give a QGIS action a Pro icon (and short caption) until undone."""
    changes.set(action, "icon", pro_icon(icon))
    if caption:
        changes.set(action, "iconText", caption)


def _button(iface, changes, names, size, icon, caption):
    """Ribbon button for a RIBBON item; None when QGIS lacks the actions."""
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
        if names.startswith("shapes:"):
            actions = _shape_actions(win, names[7:])
        else:
            actions = [a for a in (find_action(win, n)
                                   for n in names.split()) if a]
        menu = next((m for n in names.split() if n.startswith("menu:")
                     if (m := find_menu(win, n[5:]))), None)
        if actions:
            restyle(changes, actions[0], icon, caption)
            button.setDefaultAction(actions[0])
        elif menu:
            button.setText(caption)
            button.setIcon(pro_icon(icon))
        else:
            return None
        if not menu and len(actions) > 1:
            menu = QMenu(button)
            menu.addActions(actions)
        if menu:
            button.setMenu(menu)
            button.setPopupMode(
                QToolButton.ToolButtonPopupMode.MenuButtonPopup if actions
                else QToolButton.ToolButtonPopupMode.InstantPopup
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
    """Ribbon tab page: the groups in a row, separated by thin lines. It
    scrolls sideways in a window narrower than the groups, so the ribbon
    does not set the window's minimum width."""
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
    scroll = QScrollArea(objectName="ArcSkinRibbonPage",
                         widgetResizable=True)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    scroll.setMinimumHeight(page.sizeHint().height()
                            + scroll.horizontalScrollBar().sizeHint().height())
    return scroll


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
        if name.startswith("menu:"):
            submenu = find_menu(win, name[5:])
            if submenu:
                menu.addMenu(submenu)
            continue
        action = find_action(win, name)
        if action:
            if icon:
                restyle(changes, action, icon)
            menu.addAction(action)
    menu.addSeparator()
    qgis_menu = menu.addMenu(tr("QGIS Menu"))
    qgis_menu.addActions(win.menuBar().actions())
    menu.addAction(toggle_action)
    exit_action = find_action(win, "mActionExit")
    if exit_action:
        menu.addSeparator()
        menu.addAction(exit_action)
    button.setMenu(menu)
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    return button


def _drop_down_results(changes):
    """Open the locator's results below the search box, not above it (as
    they would from the status bar). Only once the search box is back in
    the main window: Qt maps the anchor to the window and crashes (Qt 5)
    when the box is not inside it."""
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
        self.locator = win.statusBar().findChild(QWidget, "LocatorWidget")
        if self.locator:
            changes.set(self.locator, "minimumWidth", 420)
            changes.set(self.locator, "maximumWidth", 420)
            row.addWidget(self.locator)  # moved out of the status bar
            changes.add(lambda: iface.statusBarIface().addPermanentWidget(
                self.locator, 0, QgsStatusBar.Anchor.AnchorLeft))
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
        """Project title (or file name) as Pro shows the project's name."""
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
    title = TitleRow(iface, changes)
    stack.addWidget(title)
    stack.addWidget(tabs)
    ribbon.addWidget(frame)
    win.addToolBar(Qt.ToolBarArea.TopToolBarArea, ribbon)
    changes.add(lambda: (win.removeToolBar(ribbon), ribbon.deleteLater()))
    if title.locator:
        _drop_down_results(changes)
