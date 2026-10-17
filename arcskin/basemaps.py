"""Basemap gallery, the counterpart of ArcGIS Pro's Basemap button.

Picking a basemap replaces the previous one, which always sits at the
bottom of the layer tree, like in Pro.
"""

from qgis.core import QgsProject, QgsRasterLayer
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (
    QGridLayout, QMenu, QToolButton, QWidget, QWidgetAction,
)

from .util import pro_icon, tr

MARKER = "arcskin/basemap"  # custom property of layers added here


def _xyz(url, zmax):
    """QGIS XYZ tile layer URI for a tile URL template."""
    return f"type=xyz&url={url}&zmin=0&zmax={zmax}"


# (name, thumbnail icon, XYZ provider URI or None, attribution).
# Only services with worldwide coverage.
BASEMAPS = [
    (tr("Topographic"), "basemap_topo",
     _xyz("https://tile.opentopomap.org/{z}/{x}/{y}.png", 17),
     "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)"),
    ("OpenStreetMap", "basemap_osm",
     _xyz("https://tile.openstreetmap.org/{z}/{x}/{y}.png", 19),
     "© OpenStreetMap contributors"),
    (tr("Imagery"), "basemap_imagery",
     _xyz("https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/"
          "{z}/{y}/{x}.jpg", 15),
     "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH "
     "(Contains modified Copernicus Sentinel data 2016) | CC BY 4.0"),
    (tr("Light Gray Canvas"), "basemap_light",
     _xyz("https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png", 20),
     "© OpenStreetMap contributors © CARTO"),
    (tr("Dark Gray Canvas"), "basemap_dark",
     _xyz("https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", 20),
     "© OpenStreetMap contributors © CARTO"),
    (tr("None"), "basemap_none", None, None),
]


def set_basemap(iface, name, uri, attribution):
    """Replace the current basemap with ``uri`` (``None`` only removes)."""
    project = QgsProject.instance()
    old = [lid for lid, layer in project.mapLayers().items()
           if layer.customProperty(MARKER)]
    project.removeMapLayers(old)
    if uri is None:
        return
    layer = QgsRasterLayer(uri, name, "wms")
    if not layer.isValid():
        iface.messageBar().pushWarning(
            "ArcSkin", tr("Basemap “{}” is unavailable.").format(name)
        )
        return
    layer.setCustomProperty(MARKER, True)
    metadata = layer.metadata()
    metadata.setRights([attribution])
    layer.setMetadata(metadata)
    project.addMapLayer(layer, False)
    root = project.layerTreeRoot()
    root.insertLayer(len(root.children()), layer)


def gallery_menu(iface, parent):
    """Drop-down gallery of basemap thumbnails, three per row."""
    menu = QMenu(parent)
    grid_widget = QWidget(menu)
    grid = QGridLayout(grid_widget)
    for i, (name, thumb, uri, attribution) in enumerate(BASEMAPS):
        button = QToolButton(text=name, autoRaise=True)
        button.setIcon(pro_icon(thumb))
        button.setIconSize(QSize(64, 48))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.clicked.connect(
            lambda _=False, a=(name, uri, attribution): (
                menu.close(), set_basemap(iface, *a)
            )
        )
        grid.addWidget(button, i // 3, i % 3)
    buttons = grid_widget.findChildren(QToolButton)
    width = max(b.sizeHint().width() for b in buttons)
    for button in buttons:  # equal columns, whatever the caption length
        button.setFixedWidth(width)
    action = QWidgetAction(menu)
    action.setDefaultWidget(grid_widget)
    menu.addAction(action)
    return menu
