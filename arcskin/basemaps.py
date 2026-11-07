"""Basemap gallery: one click adds a basemap under all other layers.

Picking a basemap replaces the previous one, which always sits at the
bottom of the layer tree. All basemaps are open services that need no API
key: OpenStreetMap and its styles, OpenFreeMap vector tiles, EOX maps.
"""

import json
import re

from qgis.core import (
    QgsBlockingNetworkRequest, QgsProject, QgsRasterLayer, QgsVectorTileLayer,
)
from qgis.PyQt.QtCore import QSize, Qt, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import (
    QGridLayout, QMenu, QToolButton, QWidget, QWidgetAction,
)

from .util import pro_icon, tr

MARKER = "arcskin/basemap"  # custom property of layers added here
OPENFREEMAP = "https://tiles.openfreemap.org"
OPENFREEMAP_CREDITS = ("OpenFreeMap © OpenMapTiles "
                       "Data from © OpenStreetMap contributors")


def _xyz(url, zmax):
    """QGIS XYZ tile layer URI for a tile URL template."""
    return f"type=xyz&url={url}&zmin=0&zmax={zmax}"


def _openfreemap(style):
    """URI of an OpenFreeMap vector tile style (completed in set_basemap)."""
    return f"styleUrl={OPENFREEMAP}/styles/{style}"


# (name, thumbnail icon, provider URI or None, attribution).
# Only services with worldwide coverage that need no API key.
BASEMAPS = [
    ("Sentinel-2 Cloudless", "basemap_sentinel",
     _xyz("https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/"
          "{z}/{y}/{x}.jpg", 15),
     "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH "
     "(Contains modified Copernicus Sentinel data 2016) | CC BY 4.0"),
    (tr("Topographic"), "basemap_topo",
     _xyz("https://tile.opentopomap.org/{z}/{x}/{y}.png", 17),
     "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)"),
    ("OpenStreetMap", "basemap_osm",
     _xyz("https://tile.openstreetmap.org/{z}/{x}/{y}.png", 19),
     "© OpenStreetMap contributors"),
    (tr("Humanitarian"), "basemap_hot",
     _xyz("https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", 19),
     "© OpenStreetMap contributors, tiles style by Humanitarian "
     "OpenStreetMap Team hosted by OpenStreetMap France"),
    (tr("Terrain"), "basemap_terrain",
     _xyz("https://tiles.maps.eox.at/wmts/1.0.0/terrain-light_3857/default/"
          "g/{z}/{y}/{x}.jpg", 16),
     "Terrain Light { Data © OpenStreetMap contributors and others, "
     "Rendering © EOX } https://maps.eox.at"),
    (tr("Light"), "basemap_light", _openfreemap("positron"),
     OPENFREEMAP_CREDITS),
    (tr("Dark"), "basemap_dark", _openfreemap("dark"), OPENFREEMAP_CREDITS),
    (tr("None"), "basemap_none", None, None),
]


def _openfreemap_layer(uri, name):
    """Vector tile layer for an OpenFreeMap style, or None when offline.

    The tile address carries the date of the current OpenFreeMap build, so
    it is read from its TileJSON when the basemap is picked.
    """
    # shortcut: blocks the UI for the small TileJSON request; fine for a click
    request = QgsBlockingNetworkRequest()
    error = request.get(QNetworkRequest(QUrl(f"{OPENFREEMAP}/planet")))
    if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
        return None
    try:
        tiles = json.loads(bytes(request.reply().content()))
        uri = (f"type=xyz&url={tiles['tiles'][0]}&zmin=0"
               f"&zmax={tiles['maxzoom']}&{uri}")
    except (ValueError, KeyError, IndexError):
        return None
    layer = QgsVectorTileLayer(uri, name)
    if layer.isValid():
        layer.loadDefaultStyle()  # the style behind styleUrl
        for part in (layer.renderer(), layer.labeling()):
            if part is not None:
                part.setStyles([_fix_filter(s) for s in part.styles()])
        layer.triggerRepaint()
    return layer


def _fix_filter(style):
    """QGIS converts MapLibre's ["geometry-type"] filter to an empty field
    name, which hides every feature; the style's own geometry type already
    makes that check."""
    style.setFilterExpression(re.sub(r'""\s+IN\s+\([^)]*\)', "TRUE",
                                     style.filterExpression()))
    return style


def set_basemap(iface, name, uri, attribution):
    """Replace the current basemap with ``uri`` (``None`` only removes)."""
    project = QgsProject.instance()
    old = [lid for lid, layer in project.mapLayers().items()
           if layer.customProperty(MARKER)]
    project.removeMapLayers(old)
    if uri is None:
        return
    if uri.startswith("styleUrl="):
        layer = _openfreemap_layer(uri, name)
    else:
        layer = QgsRasterLayer(uri, name, "wms")
    if layer is None or not layer.isValid():
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
