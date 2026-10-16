"""Build the demo project demo/arcskin_demo.qgz (run inside QGIS).

In the QGIS Python console:

    exec(open(r"<repo>/scripts/build_demo.py", encoding="utf-8").read())

Vector data: Natural Earth (public domain) from QGIS's bundled
world_map.gpkg. Raster: distance from the coast computed from it.
"""

import re
import zipfile
from pathlib import Path

import processing
from qgis.core import (
    Qgis, QgsApplication, QgsCategorizedSymbolRenderer, QgsColorRampShader,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFillSymbol,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemScaleBar,
    QgsLayoutPoint, QgsLayoutSize, QgsLineSymbol, QgsMapThemeCollection,
    QgsMarkerSymbol,
    QgsPalLayerSettings, QgsPrintLayout, QgsProject, QgsProperty,
    QgsRasterLayer, QgsRasterShader, QgsReferencedRectangle,
    QgsRendererCategory,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorFileWriter,
    QgsVectorLayer, QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import QDockWidget

REPO = Path(globals().get("REPO", Path(__file__).resolve().parent.parent
                          if "__file__" in globals() else "."))
DEMO = REPO / "demo"
DATA = DEMO / "data"
GPKG = DATA / "arcskin_demo.gpkg"
RASTER = DATA / "distance_from_coast.tif"
SOURCE = Path(QgsApplication.pkgDataPath()) / "resources" / "data" / \
    "world_map.gpkg"
KM_PER_DEGREE = 111.32
# Climate zone from the latitude of a country's interior point.
ZONES = ["Polar", "Temperate (north)", "Subtropical (north)", "Tropical",
         "Subtropical (south)", "Temperate (south)"]
ZONE_FORMULA = """
with_variable('lat', y(point_on_surface($geometry)),
  CASE WHEN abs(@lat) >= 66.5 THEN 'Polar'
       WHEN @lat >= 35 THEN 'Temperate (north)'
       WHEN @lat >= 23.5 THEN 'Subtropical (north)'
       WHEN @lat > -23.5 THEN 'Tropical'
       WHEN @lat > -35 THEN 'Subtropical (south)'
       ELSE 'Temperate (south)' END)"""
# Pastel unique-value colors in the style of Pro's default scheme.
ZONE_COLORS = ["#BEE8FF", "#D3FFBE", "#FFFFBE", "#FFBEBE", "#FFD37F",
               "#C29ED7"]


def save(layer, name):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.layerName = name
    options.actionOnExistingFile = (
        QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
        if GPKG.exists()
        else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile)
    QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(GPKG), QgsProject.instance().transformContext(), options)


def build_data():
    QgsProject.instance().clear()  # release files of an open demo project
    DATA.mkdir(parents=True, exist_ok=True)
    for path in (GPKG, RASTER):
        path.unlink(missing_ok=True)
    countries = processing.run("native:simplifygeometries", {
        "INPUT": f"{SOURCE}|layername=countries", "METHOD": 0,
        "TOLERANCE": 0.02, "OUTPUT": "memory:"})["OUTPUT"]
    countries = processing.run("native:fieldcalculator", {
        "INPUT": countries, "FIELD_NAME": "area_km2", "FIELD_TYPE": 1,
        "FIELD_LENGTH": 12, "FIELD_PRECISION": 0,
        "FORMULA": "area(transform($geometry, 'EPSG:4326', 'EPSG:6933'))"
                   " / 1000000",
        "OUTPUT": "memory:"})["OUTPUT"]
    countries = processing.run("native:fieldcalculator", {
        "INPUT": countries, "FIELD_NAME": "climate_zone", "FIELD_TYPE": 2,
        "FIELD_LENGTH": 30, "FIELD_PRECISION": 0, "FORMULA": ZONE_FORMULA,
        "OUTPUT": "memory:"})["OUTPUT"]
    save(countries, "countries")
    points = processing.run("native:pointonsurface", {
        "INPUT": countries, "ALL_PARTS": False,
        "OUTPUT": "memory:"})["OUTPUT"]
    save(points, "country_labels")
    borders = QgsVectorLayer(f"{SOURCE}|layername=disputed_borders", "b")
    save(borders, "disputed_borders")
    land = processing.run("gdal:rasterize", {
        "INPUT": f"{GPKG}|layername=countries", "BURN": 1, "UNITS": 1,
        "WIDTH": 0.2, "HEIGHT": 0.2, "EXTENT": "-180,180,-90,90 [EPSG:4326]",
        "DATA_TYPE": 0, "INIT": 0, "OUTPUT": "TEMPORARY_OUTPUT"})["OUTPUT"]
    distance = processing.run("gdal:proximity", {
        "INPUT": land, "BAND": 1, "VALUES": "1", "UNITS": 0,
        "DATA_TYPE": 5, "OUTPUT": "TEMPORARY_OUTPUT"})["OUTPUT"]
    processing.run("gdal:rastercalculator", {
        "INPUT_A": distance, "BAND_A": 1,
        "FORMULA": f"A * {KM_PER_DEGREE}", "NO_DATA": 0, "RTYPE": 2,
        "OPTIONS": "COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9",
        "OUTPUT": str(RASTER)})


def style_countries(layer):
    """Unique values in pastel colors with a 0.7 pt grey outline (Pro)."""
    categories = []
    for zone, color in zip(ZONES, ZONE_COLORS):
        symbol = QgsFillSymbol.createSimple(
            {"color": color, "outline_color": "110,110,110,255",
             "outline_width": "0.7", "outline_width_unit": "Point"})
        categories.append(QgsRendererCategory(zone, symbol, zone))
    layer.setRenderer(QgsCategorizedSymbolRenderer("climate_zone",
                                                   categories))


def style_points(layer):
    layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": "#4a4a4a", "outline_color": "#ffffff",
         "size": "1.6"})))
    settings = QgsPalLayerSettings()
    settings.fieldName = "NAME"
    text = QgsTextFormat()  # Pro's default label symbol
    text.setFont(QFont("Tahoma"))
    text.setSize(10)
    text.setSizeUnit(Qgis.RenderUnit.Points)
    text.setColor(QColor("#000000"))
    settings.setFormat(text)
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Show,
        QgsProperty.fromExpression('"area_km2" > 400000'))
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def style_raster(layer):
    shader = QgsColorRampShader(0, 2000)
    shader.setColorRampType(QgsColorRampShader.Type.Interpolated)
    shader.setColorRampItemList([
        QgsColorRampShader.ColorRampItem(1, QColor("#d4e8f5"), "1"),
        QgsColorRampShader.ColorRampItem(500, QColor("#7fb3d9"), "500"),
        QgsColorRampShader.ColorRampItem(1500, QColor("#2f6ea8"), "1500"),
        QgsColorRampShader.ColorRampItem(2500, QColor("#173c66"), "2500"),
    ])
    legend = shader.legendSettings()  # Pro-style "High : / Low :" labels
    legend.setMaximumLabel("High : 2 500")
    legend.setMinimumLabel("Low : 1")
    shader.setLegendSettings(legend)
    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(shader)
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1,
                                                raster_shader)
    renderer.setClassificationMin(1)
    renderer.setClassificationMax(2500)
    layer.setRenderer(renderer)


def build_layout(project, map_layers, extent_layer):
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("World overview")
    title = QgsLayoutItemLabel(layout)
    title.setText("ArcSkin demo — world overview")
    title_format = QgsTextFormat()
    title_format.setFont(QFont("Tahoma"))
    title_format.setSize(20)
    title.setTextFormat(title_format)
    title.attemptMove(QgsLayoutPoint(10, 8))
    title.attemptResize(QgsLayoutSize(200, 12))
    layout.addLayoutItem(title)
    item = QgsLayoutItemMap(layout)
    item.attemptMove(QgsLayoutPoint(10, 24))
    item.attemptResize(QgsLayoutSize(210, 176))
    item.setLayers(map_layers)
    to_map = QgsCoordinateTransform(extent_layer.crs(), project.crs(), project)
    item.zoomToExtent(to_map.transformBoundingBox(extent_layer.extent()))
    layout.addLayoutItem(item)
    legend = QgsLayoutItemLegend(layout)
    legend.setLinkedMap(item)
    legend.setTitle("Legend")
    legend.attemptMove(QgsLayoutPoint(225, 24))
    layout.addLayoutItem(legend)
    bar = QgsLayoutItemScaleBar(layout)
    bar.setStyle("Single Box")
    bar.setLinkedMap(item)
    bar.setUnits(Qgis.DistanceUnit.Kilometers)
    bar.applyDefaultSize()
    bar.attemptMove(QgsLayoutPoint(10, 195))
    layout.addLayoutItem(bar)
    project.layoutManager().addLayout(layout)


def build_views(project, themes, extent):
    """Map themes, and a map view showing each one: Pro-like view tabs.

    QGIS saves the open map views with the project and reopens them.
    Needs the QGIS window (``iface``); without it only themes are made.
    """
    collection = project.mapThemeCollection()
    for name, layers in themes.items():
        record = QgsMapThemeCollection.MapThemeRecord()
        record.setLayerRecords(
            [QgsMapThemeCollection.MapThemeLayerRecord(layer)
             for layer in layers])
        collection.insert(name, record)
    iface = globals().get("iface")
    if iface is None:
        return
    win = iface.mainWindow()
    catalog = win.findChild(QDockWidget, "Browser")
    for name in themes:
        iface.closeMapCanvas(name)  # left from an earlier build
        canvas = iface.createNewMapCanvas(name)
        canvas.setTheme(name)
        canvas.setDestinationCrs(project.crs())
        canvas.setExtent(extent)
        canvas.refresh()
        dock = canvas.parent()
        while not isinstance(dock, QDockWidget):
            dock = dock.parent()
        if catalog:  # behind the Catalog pane until its tab is clicked
            win.tabifyDockWidget(catalog, dock)
    if catalog:
        catalog.raise_()


def build_project():
    project = QgsProject.instance()
    project.clear()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:8857"))  # Equal Earth
    project.setTitle("ArcSkin demo")
    raster = QgsRasterLayer(str(RASTER), "Distance from coast (km)")
    style_raster(raster)
    countries = QgsVectorLayer(f"{GPKG}|layername=countries", "Countries")
    style_countries(countries)
    borders = QgsVectorLayer(f"{GPKG}|layername=disputed_borders",
                             "Disputed borders")
    borders.renderer().setSymbol(QgsLineSymbol.createSimple(
        {"color": "#d0352b", "width": "0.4", "line_style": "dash"}))
    points = QgsVectorLayer(f"{GPKG}|layername=country_labels",
                            "Country names")
    style_points(points)
    for layer in (raster, countries, borders, points):
        project.addMapLayer(layer)
    build_layout(project, [points, borders, countries, raster], countries)
    to_map = QgsCoordinateTransform(countries.crs(), project.crs(), project)
    world = QgsReferencedRectangle(
        to_map.transformBoundingBox(countries.extent()), project.crs())
    project.viewSettings().setDefaultViewExtent(world)
    build_views(project, {"Climate zones": [points, borders, countries],
                          "Distance from coast": [raster]}, world)
    if "iface" in globals():  # QGIS saves the open canvas extent too
        globals()["iface"].mapCanvas().setExtent(world)
    project.write(str(DEMO / "arcskin_demo.qgz"))
    _without_local_paths(DEMO / "arcskin_demo.qgz")


def _without_local_paths(path):
    """Relative data paths and no user name in the saved project (QGIS
    writes absolute paths in map themes and GPS settings)."""
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    for name in files:
        if name.endswith(".qgs"):
            text = files[name].decode("utf-8")
            for folder in {str(DEMO.resolve()), DEMO.resolve().as_posix()}:
                text = re.sub(re.escape(folder) + r"[\\/]", "./", text)
            text = re.sub(r' saveUser(Full)?="[^"]*"', "", text)
            files[name] = text.encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)


build_data()
build_project()
print("demo written to", DEMO)
