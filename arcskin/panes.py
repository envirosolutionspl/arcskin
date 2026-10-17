"""Dock panes arranged and dressed like ArcGIS Pro.

* Contents (Layers): search box, Pro icons on its toolbar,
* Catalog (Browser): Project / Favorites / All tabs, permanent search box,
* Geoprocessing (Processing toolbox): "Find tools", toolbox and tool icons,
* Symbology (Layer Styling): its Pro title kept, Pro page and undo icons.

Dock positions come back with the saved window state; everything else is
reverted through :class:`~.util.Changes`.
"""

from qgis.core import QgsLayerTreeModel, QgsLayerTreeNode
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QModelIndex, QObject, Qt, QTimer
from qgis.PyQt.QtGui import QAction, QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QApplication, QDockWidget, QHBoxLayout, QLineEdit, QListWidget, QMenu,
    QStyledItemDelegate, QTabBar, QToolBar, QToolButton, QTreeView, QWidget,
)
from qgis.gui import QgsBrowserTreeView

from .contents_views import ContentsViews, LayerMenuIcons, RasterLegend
from .icon_theme import swap_icons
from .util import pro_icon, tr

LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
RIGHT = Qt.DockWidgetArea.RightDockWidgetArea

# Dock object name -> (Pro title, area, dock to tabify with).
PANES = {
    "Layers": (tr("Contents"), LEFT, None),
    "Browser": (tr("Catalog"), RIGHT, None),
    "ProcessingToolbox": (tr("Geoprocessing"), RIGHT, "Browser"),
    "LayerStyling": (tr("Symbology"), RIGHT, "Browser"),
}
# Icons for the Layers toolbar, in QGIS's button order.
CONTENTS_ICONS = ["symbology", "add_group", "visibility", "filter",
                  "filter_expression", "expand_all", "collapse_all",
                  "remove_layer"]
CATALOG_ICONS = {"mActionAddLayers": "add_data", "mActionRefresh": "refresh",
                 "mActionShowFilter": "filter",
                 "mActionCollapse": "collapse_all",
                 "mActionPropertiesWidget": "project_properties"}
# Catalog tab -> browser item class shown as the tree root (None: all).
CATALOG_TABS = [(tr("Project"), "QgsProjectHomeItem"),
                (tr("Favorites"), "QgsFavoritesItem"),
                (tr("All"), None)]


class ActivePane(QObject):
    """Marks the pane holding the focus: Pro draws its title and frame blue
    (style sheet rule ``QDockWidget[arcskinActive="true"]``)."""

    PROPERTY = "arcskinActive"

    def __init__(self, win, changes):
        super().__init__(win)
        self.current = None
        QApplication.instance().focusChanged.connect(self.focus_changed)
        self.mark(win.findChild(QDockWidget, "Layers"))
        changes.add(self.stop)

    def focus_changed(self, _old, new):
        while new is not None and not isinstance(new, QDockWidget):
            new = new.parentWidget()
        if new is not None:
            self.mark(new)

    def _set(self, dock, on):
        if dock is not None and not sip.isdeleted(dock):
            dock.setProperty(self.PROPERTY, on)
            dock.style().unpolish(dock)
            dock.style().polish(dock)
            dock.update()

    def mark(self, dock):
        if dock is not self.current:
            self._set(self.current, False)
            self._set(dock, True)
            self.current = dock

    def stop(self):
        QApplication.instance().focusChanged.disconnect(self.focus_changed)
        self._set(self.current, False)
        self.deleteLater()


class ToolboxDelegate(QStyledItemDelegate):
    """Toolbox icon for groups, tool icon for algorithms, as in Pro."""

    def initStyleOption(self, option, index):  # noqa: N802 (Qt API name)
        super().initStyleOption(option, index)
        has_children = index.model().hasChildren(index)
        option.icon = pro_icon("toolbox" if has_children else "tool")


def _search_row(changes, dock, placeholder, on_text, filters=()):
    """Search box (with a filter drop-down) above the dock's toolbar."""
    row = QWidget(objectName="ArcSkinPaneSearch")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(4, 4, 4, 2)
    layout.setSpacing(2)
    if filters:
        button = QToolButton(autoRaise=True, toolTip=tr("Filter"))
        button.setIcon(pro_icon("filter"))
        menu = QMenu(button)
        for group in filters:
            menu.addActions(group)
            menu.addSeparator()
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(button)
    search = QLineEdit(placeholderText=placeholder, clearButtonEnabled=True)
    search.addAction(pro_icon("search"),
                     QLineEdit.ActionPosition.LeadingPosition)
    search.textChanged.connect(on_text)
    layout.addWidget(search)
    dock.widget().layout().insertWidget(0, row)
    changes.add(lambda: (row.hide(), row.deleteLater()))


def _dress_contents(changes, iface, dock):
    """Contents pane: search row with the legend filters, List By views,
    Pro legend and context menu icons, regular fonts, no toolbar."""
    bar = dock.findChild(QToolBar)
    filters = []
    for action, icon in zip(bar.actions() if bar else [], CONTENTS_ICONS):
        widget = bar.widgetForAction(action)
        target = widget if isinstance(widget, QToolButton) else action
        changes.set(target, "icon", pro_icon(icon))
        if icon.startswith("filter") and widget and widget.menu():
            # Legend filters move to the drop-down next to the search box.
            filters.append(widget.menu().actions())
            changes.set(action, "visible", False)
    proxy = iface.layerTreeView().proxyModel()
    _search_row(changes, dock, tr("Search layers"), proxy.setFilterText,
                filters)
    layout = dock.widget().layout()
    views = ContentsViews(iface, iface.layerTreeView(), layout)
    layout.insertWidget(1, views)  # under the search row, as in Pro
    layout.insertWidget(2, views.header)
    changes.add(views.remove)
    LayerMenuIcons(iface.layerTreeView(), changes)
    RasterLegend(iface.layerTreeView(), changes)
    # Pro has no toolbar here: these tools are on the ribbon and the
    # context menu (the legend filters moved next to the search box).
    if bar:
        changes.set(bar, "visible", False)
    changes.add(lambda: proxy.setFilterText(""))
    # Pro's Contents: regular-weight names, check boxes on layers only.
    model = iface.layerTreeView().layerTreeModel()
    for kind in (QgsLayerTreeNode.NodeType.NodeLayer,
                 QgsLayerTreeNode.NodeType.NodeGroup):
        font = model.layerTreeNodeFont(kind)
        regular = QFont(font)
        regular.setBold(False)
        model.setLayerTreeNodeFont(kind, regular)
        changes.add(lambda k=kind, f=font: model.setLayerTreeNodeFont(k, f))
    legend_checks = QgsLayerTreeModel.Flag.AllowLegendChangeState
    if model.testFlag(legend_checks):
        model.setFlag(legend_checks, False)
        changes.add(lambda: model.setFlag(legend_checks, True))
    iface.layerTreeView().viewport().update()


def _dress_catalog(changes, dock):
    """Catalog pane: Pro icons, a permanent search box and the Project /
    Favorites / All tabs, each showing a part of the Browser tree."""
    for name, icon in CATALOG_ICONS.items():
        action = dock.findChild(QAction, name)
        if action:
            changes.set(action, "icon", pro_icon(icon))
    show_filter = dock.findChild(QAction, "mActionShowFilter")
    search = dock.findChild(QLineEdit, "mLeFilter")
    if show_filter and search:
        changes.set(show_filter, "checked", True)
        changes.set(search, "placeholderText", tr("Search catalog"))
    tree = dock.findChild(QgsBrowserTreeView)
    if tree is None:
        return
    tabs = QTabBar(objectName="ArcSkinPaneTabs", drawBase=False,
                   expanding=False)
    for title, _ in CATALOG_TABS:
        tabs.addTab(title)

    def show_tab(i):
        root = QModelIndex()
        wanted = CATALOG_TABS[i][1]
        proxy, model = tree.model(), tree.browserModel()
        for row in range(proxy.rowCount() if wanted else 0):
            index = proxy.index(row, 0)
            item = model.dataItem(proxy.mapToSource(index))
            # Qt's class name: sip often wraps a base class (directory).
            if item.metaObject().className() == wanted:
                root = index
        tree.setRootIndex(root)

    tabs.currentChanged.connect(show_tab)
    dock.widget().layout().insertWidget(0, tabs)
    tabs.setCurrentIndex(len(CATALOG_TABS) - 1)
    changes.add(lambda: (tree.setRootIndex(QModelIndex()), tabs.hide(),
                         tabs.deleteLater()))


def _dress_symbology(changes, dock):
    """Pro undo / redo icons (QGIS sets its own resource icons there) and
    Pro page icons, also for icons QGIS loaded before the icon theme."""
    for name, icon in (("mUndoButton", "undo"), ("mRedoButton", "redo")):
        button = dock.findChild(QToolButton, name)
        if button:
            changes.set(button, "icon", pro_icon(icon))
    pages = dock.findChild(QListWidget, "mOptionsListWidget")
    if pages is None:
        return

    def dress_items():
        items = [pages.item(row) for row in range(pages.count())]
        swap_icons(items)
        for item in items:  # Pro keeps the colours of the current page
            icon = item.icon()
            icon.addPixmap(icon.pixmap(pages.iconSize()),
                           QIcon.Mode.Selected)
            item.setIcon(icon)

    def dress(*_):  # the page list is rebuilt for every layer
        QTimer.singleShot(0, lambda: sip.isdeleted(pages) or dress_items())

    pages.model().rowsInserted.connect(dress)
    dress()
    changes.add(lambda: sip.isdeleted(pages)
                or pages.model().rowsInserted.disconnect(dress))


def _dress_toolbox(changes, dock):
    """Geoprocessing pane: toolbox and tool icons, Pro's search prompt."""
    tree = dock.findChild(QTreeView)
    if tree:
        changes.set(tree, "itemDelegate", ToolboxDelegate(tree))
    search = dock.findChild(QLineEdit, "searchBox")
    if search:
        changes.set(search, "placeholderText", tr("Find Tools"))


# Reset Panes modes: key -> (menu text, docks to show, dock in front,
# docks tabbed with the Catalog for this mode).
RESET_MODES = {
    "mapping": (tr("Reset Panes for Mapping (Default)"),
                ["Layers", "Browser"], "Browser", []),
    "editing": (tr("Reset Panes for Editing"),
                ["Layers", "Browser", "AdvancedDigitizingTools",
                 "VertexEditor"], "AdvancedDigitizingTools",
                ["AdvancedDigitizingTools", "VertexEditor"]),
    "geoprocessing": (tr("Reset Panes for Geoprocessing"),
                      ["Layers", "Browser", "ProcessingToolbox"],
                      "ProcessingToolbox", []),
}


def reset_panes(win, mode="mapping", close_others=True):
    """Dock the panes where Pro has them, like View > Reset Panes."""
    docks = {d.objectName(): d for d in win.findChildren(QDockWidget)}
    _, visible, front, extra = RESET_MODES[mode]
    placement = {name: (area, tab_with)
                 for name, (_, area, tab_with) in PANES.items()}
    placement.update({name: (RIGHT, "Browser") for name in extra})
    for name, (area, tab_with) in placement.items():
        if name in docks:
            win.addDockWidget(area, docks[name])
            if tab_with in docks:
                win.tabifyDockWidget(docks[tab_with], docks[name])
    for name, dock in docks.items():
        if name in visible:
            dock.show()
        elif close_others and dock.isVisible() and not dock.isFloating():
            dock.close()
    if front in docks:
        docks[front].raise_()


def reset_panes_menu(win, parent):
    """Drop-down with the Reset Panes modes."""
    menu = QMenu(parent)
    for mode, (text, _, _, _) in RESET_MODES.items():
        menu.addAction(text, lambda m=mode: reset_panes(win, m))
    return menu


def arrange_panes(iface, changes):
    """Rename, dock and dress the panes like ArcGIS Pro."""
    win = iface.mainWindow()
    for name, (title, _, _) in PANES.items():
        dock = win.findChild(QDockWidget, name)
        if dock:
            changes.set(dock, "windowTitle", title)
            # QGIS renames some panes itself (Layer Styling on every layer).
            keep = (lambda text, d=dock, t=title:
                    text == t or d.setWindowTitle(t))
            dock.windowTitleChanged.connect(keep)
            changes.add(lambda d=dock, k=keep:
                        d.windowTitleChanged.disconnect(k))
    dressing = {"Layers": lambda d: _dress_contents(changes, iface, d),
                "Browser": lambda d: _dress_catalog(changes, d),
                "ProcessingToolbox": lambda d: _dress_toolbox(changes, d),
                "LayerStyling": lambda d: _dress_symbology(changes, d)}
    for name, dress in dressing.items():
        dock = win.findChild(QDockWidget, name)
        if dock:
            dress(dock)
    reset_panes(win, close_others=False)
    ActivePane(win, changes)
