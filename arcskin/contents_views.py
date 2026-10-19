"""Contents pane "List By" views, as in ArcGIS Pro's TOC.

Drawing Order is QGIS's own layer tree. The other views are lists of the
project's layers with one Pro-style check box each:

* Data Source - layers grouped by file, database or service,
* Selection - selected feature count; clicking makes the layer active,
* Editing - editable (not read-only),
* Snapping - snapping to the layer (switches snapping to per-layer mode),
* Labeling - labels on.

Raster ramps get Pro's short "Value" legend (see RasterLegend).
"""

from pathlib import Path

from qgis.core import (
    Qgis, QgsColorRampLegendNode, QgsIconUtils, QgsMapLayer,
    QgsNumericFormatContext, QgsProject, QgsProviderRegistry, QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QCoreApplication, QObject, QSize, Qt, QTimer
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QToolButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .util import pro_icon, tr

# key -> (icon, tooltip, heading)
VIEWS = {
    "drawing_order": ("layer_order", tr("List By Drawing Order"),
                      tr("Drawing Order")),
    "data_source": ("add_data", tr("List By Data Source"),
                    tr("Data Source")),
    "selection": ("select", tr("List By Selection"), tr("Selection")),
    "editing": ("edit", tr("List By Editing"), tr("Editing")),
    "snapping": ("snapping", tr("List By Snapping"), tr("Snapping")),
    "labeling": ("labeling", tr("List By Labeling"), tr("Labeling")),
}
LAYER_ROLE = Qt.ItemDataRole.UserRole


def _source_group(layer):
    """Name of the file, database or service a layer comes from."""
    parts = QgsProviderRegistry.instance().decodeUri(
        layer.providerType(), layer.source())
    path = parts.get("path") or parts.get("url") or parts.get("dbname")
    if path:
        return str(Path(path).name) if "://" not in str(path) else str(path)
    return layer.providerType()


class ContentsViews(QWidget):
    """Row of List By buttons switching the Contents pane's view."""

    def __init__(self, iface, layer_tree_view, parent_layout):
        super().__init__(objectName="ArcSkinContentsViews")
        self.iface = iface
        self.layer_tree_view = layer_tree_view
        self.view = "drawing_order"
        self.tree = QTreeWidget(objectName="ArcSkinContentsList",
                                headerHidden=True)
        self.tree.hide()
        self.tree.itemChanged.connect(self._toggled)
        self.tree.itemClicked.connect(self._clicked)
        parent_layout.addWidget(self.tree)
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 0, 4, 2)
        row.setSpacing(1)
        group = QButtonGroup(self)
        self.buttons = {}
        for key, (icon, tip, _) in VIEWS.items():
            button = QToolButton(autoRaise=True, checkable=True,
                                 toolTip=tip)
            button.setIcon(pro_icon(icon))
            button.setIconSize(QSize(20, 20))
            button.setChecked(key == self.view)
            button.clicked.connect(lambda _=False, k=key: self.show_view(k))
            group.addButton(button)
            row.addWidget(button)
            self.buttons[key] = button
        row.addStretch()
        self.header = self._header()
        project = QgsProject.instance()
        for signal in (project.readProject, project.cleared,
                       project.titleChanged, project.fileNameChanged):
            signal.connect(self.show_map_name)
        for signal in (project.layersAdded, project.layersRemoved,
                       iface.mapCanvas().selectionChanged):
            signal.connect(self.refresh)

    def _header(self):
        """View heading and the map row, like the top of Pro's Contents."""
        header = QWidget(objectName="ArcSkinContentsHeader")
        box = QVBoxLayout(header)
        box.setContentsMargins(8, 6, 4, 2)
        box.setSpacing(4)
        self.heading = QLabel(VIEWS[self.view][2],
                              objectName="ArcSkinContentsHeading")
        map_row = QHBoxLayout()
        map_icon = QLabel()
        map_icon.setPixmap(pro_icon("new_map").pixmap(16, 16))
        self.map_name = QLabel(objectName="ArcSkinContentsMap")
        map_row.addWidget(map_icon)
        map_row.addWidget(self.map_name, 1)
        box.addWidget(self.heading)
        box.addLayout(map_row)
        self.show_map_name()
        return header

    def show_map_name(self, *_):
        """The project's title (or file name) heads the layer list."""
        project = QgsProject.instance()
        self.map_name.setText(project.title() or project.baseName()
                              or tr("Map"))

    def show_view(self, key):
        """Switch to the List By view ``key``."""
        self.view = key
        self.buttons[key].setChecked(True)
        self.heading.setText(VIEWS[key][2])
        own = key != "drawing_order"
        self.layer_tree_view.setVisible(not own)
        self.tree.setVisible(own)
        self.refresh()

    def refresh(self, *_):
        """Rebuild the list of the current view from the project."""
        if self.view == "drawing_order" or not self.tree.isVisible():
            return
        self.tree.blockSignals(True)
        self.tree.clear()
        layers = [node.layer() for node in
                  QgsProject.instance().layerTreeRoot().findLayers()
                  if node.layer()]
        if self.view == "data_source":
            groups = {}
            for layer in layers:
                name = _source_group(layer)
                if name not in groups:
                    groups[name] = QTreeWidgetItem(self.tree, [name])
                    groups[name].setIcon(0, pro_icon("catalog"))
                self._layer_item(groups[name], layer)
            self.tree.expandAll()
        else:
            for layer in layers:
                if isinstance(layer, QgsVectorLayer):
                    self._layer_item(self.tree, layer)
        self.tree.blockSignals(False)

    def _layer_item(self, parent, layer):
        """One row for ``layer``, with the check box of the current view."""
        item = QTreeWidgetItem(parent, [layer.name()])
        item.setIcon(0, QgsIconUtils.iconForLayer(layer))
        item.setData(0, LAYER_ROLE, layer.id())
        state = {
            "editing": lambda: not layer.readOnly(),
            "snapping": lambda: QgsProject.instance().snappingConfig()
            .individualLayerSettings(layer).enabled(),
            "labeling": lambda: layer.labelsEnabled(),
        }.get(self.view)
        if state:
            item.setCheckState(0, Qt.CheckState.Checked if state()
                               else Qt.CheckState.Unchecked)
        if self.view == "selection":
            count = layer.selectedFeatureCount()
            item.setText(0, f"{layer.name()}  ({count})")
        return item

    def _layer(self, item):
        layer_id = item.data(0, LAYER_ROLE)
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def _clicked(self, item, _column):
        layer = self._layer(item)
        if isinstance(layer, QgsMapLayer):
            self.iface.setActiveLayer(layer)

    def _toggled(self, item, _column):
        """Apply a check box change to the layer."""
        layer = self._layer(item)
        if not isinstance(layer, QgsVectorLayer):
            return
        on = item.checkState(0) == Qt.CheckState.Checked
        if self.view == "editing":
            layer.setReadOnly(not on)
        elif self.view == "labeling":
            layer.setLabelsEnabled(on)
            layer.triggerRepaint()
        elif self.view == "snapping":
            project = QgsProject.instance()
            config = project.snappingConfig()
            settings = config.individualLayerSettings(layer)
            settings.setEnabled(on)
            config.setIndividualLayerSettings(layer, settings)
            config.setMode(Qgis.SnappingMode.AdvancedConfiguration)
            project.setSnappingConfig(config)

    def remove(self):
        """Back to QGIS's layer tree alone."""
        self.layer_tree_view.show()
        for widget in (self.tree, self.header, self):
            widget.hide()
            widget.deleteLater()


# --- context menu icons ---------------------------------------------------

# Layer context menu entries without (Pro) icons: QGIS source text in its
# translation context, or an action object name -> Pro icon.
MENU_ICONS = {
    ("QgsLayerTreeViewDefaultActions", "&Zoom to Layer(s)"): "zoom_layer",
    ("QgsLayerTreeViewDefaultActions", "Zoom to &Selection"): "zoom_selected",
    ("QgsLayerTreeViewDefaultActions", "Show in &Overview"): "overview",
    ("QgsLayerTreeViewDefaultActions", "Show Feature &Count"): "statistics",
    ("QgsLayerTreeViewDefaultActions", "Re&name Layer"): "multi_edit",
    ("QgsLayerTreeViewDefaultActions", "Move to &Top"): "layer_order",
    ("QgsLayerTreeViewDefaultActions", "Move to &Bottom"): "layer_order",
    ("QgsAppLayerTreeViewMenuProvider", "Show &Labels"): "labeling",
    ("QgsAppLayerTreeViewMenuProvider", "&Duplicate Layer"): "copy",
    ("QgsAppLayerTreeViewMenuProvider", "&Remove Layer…"): "remove_layer",
    ("QgsAppLayerTreeViewMenuProvider", "Open &Attribute Table"):
        "attribute_table",
    ("QgsAppLayerTreeViewMenuProvider", "&Filter…"): "filter",
    ("QgsAppLayerTreeViewMenuProvider", "Execute SQL…"): "add_data",
    ("QgsAppLayerTreeViewMenuProvider", "Styles"): "symbology",
    ("QgsAppLayerTreeViewMenuProvider", "Layer CRS"): "coordinates",
    ("QgsAppLayerTreeViewMenuProvider", "Add Layer Notes…"): "message_log",
    ("QgsAppLayerTreeViewMenuProvider", "&Properties…"):
        "project_properties",
    ("QgsAppLayerTreeViewMenuProvider", "C&hange Data Source…"): "add_data",
    ("QgsAppLayerTreeViewMenuProvider", "E&xport"): "export_image",
    "mActionSetLayerScaleVisibility": "zoom_in",
    "mActionCopyLayer": "copy",
    "mActionToggleEditing": "edit",
    "mActionLayerSaveAs": "save_as",
    "mActionLayerProperties": "project_properties",
}


def _menu_key(text):
    """Menu text without accelerators, for matching across translations."""
    return text.replace("&", "").replace("...", "…").strip().lower()


class LayerMenuIcons(QObject):
    """Adds Pro icons to the Contents context menu each time it opens."""

    def __init__(self, view, changes):
        super().__init__(view)
        self.view = view
        self.icons = {}
        self.prefixes = []  # menu copies of app actions may differ slightly
        win = view.window()
        for key, icon in MENU_ICONS.items():
            if isinstance(key, tuple):
                self.icons[_menu_key(QCoreApplication.translate(*key))] = icon
                continue
            self.icons[key] = icon
            action = win.findChild(QAction, key)
            if action and action.text():
                self.prefixes.append((_menu_key(action.text())[:20], icon))
        self.saved = {}  # shared QGIS actions: id -> (action, old icon)
        view.contextMenuAboutToShow.connect(self.dress)
        changes.add(self.stop)

    def dress(self, menu):
        """Give the menu's entries Pro icons (QGIS's are kept for undo)."""
        for action in menu.actions():
            text = _menu_key(action.text())
            icon = (self.icons.get(action.objectName())
                    or self.icons.get(text)
                    or next((i for p, i in self.prefixes
                             if text.startswith(p)), None))
            if not icon:
                continue
            if action.objectName() and id(action) not in self.saved:
                self.saved[id(action)] = (action, action.icon())
            action.setIcon(pro_icon(icon))

    def stop(self):
        self.view.contextMenuAboutToShow.disconnect(self.dress)
        for action, icon in self.saved.values():
            if not sip.isdeleted(action):
                action.setIcon(icon)
        self.deleteLater()


# --- raster legend ----------------------------------------------------------

RAMP_PATCH = QSize(16, 36)  # about two text rows, as in Pro


class RasterLegend(QObject):
    """Pro-style legend of stretched single band rasters.

    Pro lists "Value" and a short gradient patch with "High : max" and
    "Low : min" beside it, where QGIS shows the band name and a tall ramp.
    Only the legend nodes shown in the Contents pane change: nothing is
    stored in the project, and QGIS rebuilds its own nodes on undo.
    """

    def __init__(self, view, changes):
        super().__init__(view)
        self.model = view.layerTreeModel()
        self.timer = QTimer(self, singleShot=True, interval=0)
        self.timer.timeout.connect(self.dress)
        self.model.rowsInserted.connect(self.timer.start)
        self.model.modelReset.connect(self.timer.start)
        changes.add(self.stop)  # before dressing: it may fail half-way
        self.dress()

    def _raster_nodes(self):
        return [node for node in
                QgsProject.instance().layerTreeRoot().findLayers()
                if isinstance(node.layer(), QgsRasterLayer)]

    def dress(self):
        """Pro's "Value" label and short ramp on every raster legend."""
        number = QgsNumericFormatContext()
        for node in self._raster_nodes():
            legend = self.model.layerLegendNodes(node)
            ramps = [n for n in legend
                     if isinstance(n, QgsColorRampLegendNode)]
            if not ramps:
                continue
            for item in legend[:legend.index(ramps[0])]:
                if not item.userLabel():
                    item.setUserLabel(tr("Value"))
            for ramp in ramps:
                settings = ramp.settings()
                if not (settings.maximumLabel() or settings.minimumLabel()):
                    text = settings.numericFormat().formatDouble
                    settings.setMaximumLabel(tr("High : {}").format(
                        text(ramp.maximum(), number)))
                    settings.setMinimumLabel(tr("Low : {}").format(
                        text(ramp.minimum(), number)))
                    ramp.setSettings(settings)
                # Invalidating resets the size: shrink after it, then redraw.
                # (QGIS 3 has the old name of the method.)
                getattr(ramp, "invalidateDisplayData",
                        ramp.invalidateMapBasedData)()
                ramp.setIconSize(RAMP_PATCH)
                ramp.dataChanged.emit()

    def stop(self):
        self.model.rowsInserted.disconnect(self.timer.start)
        self.model.modelReset.disconnect(self.timer.start)
        self.timer.stop()
        for node in self._raster_nodes():
            self.model.refreshLayerLegend(node)
        self.deleteLater()
