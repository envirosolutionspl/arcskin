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


def _esri(service, zmax):
    """XYZ URI of an Esri ArcGIS Online tile service (no API key needed).

    ``zmax`` is the last level with data in Europe; QGIS upsamples beyond
    it instead of showing Esri's "Map data not yet available" tiles.
    """
    return _xyz("https://services.arcgisonline.com/ArcGIS/rest/services/"
                f"{service}/MapServer/tile/{{z}}/{{y}}/{{x}}", zmax)


# (name, thumbnail icon, XYZ provider URI or None, attribution).
# Only services with worldwide coverage that need no API key.
BASEMAPS = [
    (tr("Imagery"), "basemap_imagery",
     _esri("World_Imagery", 19),
     "Esri, Vantor, Earthstar Geographics, and the GIS User Community"),
    ("Sentinel-2 Cloudless", "basemap_sentinel",
     _xyz("https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/"
          "{z}/{y}/{x}.jpg", 15),
     "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH "
     "(Contains modified Copernicus Sentinel data 2016) | CC BY 4.0"),
    (tr("Streets"), "basemap_streets",
     _esri("World_Street_Map", 19),
     "Esri, HERE, Garmin, USGS, © OpenStreetMap contributors, "
     "and the GIS User Community"),
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
     _esri("World_Terrain_Base", 9),
     "Esri, USGS, NOAA"),
    (tr("Hillshade"), "basemap_hillshade",
     _esri("Elevation/World_Hillshade", 16),
     "Esri, Vantor, Airbus DS, USGS, NGA, NASA, CGIAR, and the GIS user "
     "community"),
    (tr("Oceans"), "basemap_oceans",
     _esri("Ocean/World_Ocean_Base", 10),
     "Esri, Garmin, GEBCO, NOAA NGDC, and other contributors"),
    (tr("National Geographic Style"), "basemap_natgeo",
     _esri("NatGeo_World_Map", 12),
     "National Geographic, Esri, Garmin, HERE, UNEP-WCMC, USGS, NASA, ESA, "
     "METI, NRCAN, GEBCO, NOAA, increment P Corp."),
    (tr("Light Gray Canvas"), "basemap_light",
     _esri("Canvas/World_Light_Gray_Base", 16),
     "Esri, HERE, Garmin, © OpenStreetMap contributors, "
     "and the GIS user community"),
    (tr("Dark Gray Canvas"), "basemap_dark",
     _esri("Canvas/World_Dark_Gray_Base", 16),
     "Esri, HERE, Garmin, © OpenStreetMap contributors, "
     "and the GIS user community"),
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
