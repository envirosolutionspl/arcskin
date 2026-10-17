"""Pro-like default symbology for new vector layers.

* New layer colors come from a pastel "Basic Random"-like palette (the tones
  of the Pro color picker), through QGIS's random style color scheme.
* The same palette is the project's default color ramp, used e.g. for
  categorized (unique values) renderers.
* A layer added with QGIS's default single symbol gets Pro's defaults:
  polygons with a 0.7 pt grey outline, 1 pt lines, 4 pt circle markers.
* Selected features are cyan on the map, Pro's default selection color
  (the attribute table uses the same cyan).
* New labels use Pro's default text symbol: Tahoma 10 pt, black.
* Pro-like color ramps (resources/color_ramps.json) are added to the QGIS
  style, tagged "ArcSkin", for classifying vector layers and stretching
  rasters.
"""

import json
from pathlib import Path

from qgis.core import (
    Qgis, QgsApplication, QgsColorScheme, QgsFillSymbol, QgsGradientColorRamp,
    QgsGradientStop, QgsLimitedRandomColorRamp, QgsLineSymbol,
    QgsMarkerSymbol, QgsPresetSchemeColorRamp, QgsProject,
    QgsSingleSymbolRenderer, QgsStyle, QgsSymbol, QgsTextFormat,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QColor, QFont

RAMP_NAME = "ArcSkin Basic Random"
RAMPS = Path(__file__).resolve().parent / "resources" / "color_ramps.json"
TAG = "ArcSkin"
PALETTE = ["#FFBEE8", "#FFBEBE", "#FFD37F", "#89CD66", "#C29ED7", "#D3FFBE",
           "#FFFFBE", "#BEE8FF", "#D7C29E", "#BED2FF", "#FFEBBE", "#BEFFE8",
           "#E8BEFF", "#A3FF73", "#73DFFF", "#FF7F7F", "#CDAA66", "#E1E1E1"]
OUTLINE = "110,110,110,255"
SELECTION = QColor(0, 255, 255)
# Symbol properties QGIS draws at random for a new layer.
RANDOM_KEYS = {"color", "line_color"}


class ProColorScheme(QgsColorScheme):
    """Pastel palette QGIS picks new layer colors from."""

    def schemeName(self):  # noqa: N802 (QGIS API name)
        return RAMP_NAME

    def fetchColors(self, context="", base_color=QColor()):  # noqa: N802
        return [(QColor(c), c) for c in PALETTE]

    def clone(self):
        return ProColorScheme()


def _ramp():
    return QgsPresetSchemeColorRamp([QColor(c) for c in PALETTE])


def _is_qgis_default(layer):
    """Whether ``layer`` still has the single symbol QGIS gave it: the
    default symbol of its geometry type, in whatever random colour."""
    renderer = layer.renderer()
    if not isinstance(renderer, QgsSingleSymbolRenderer):
        return False
    symbol = renderer.symbol()
    default = QgsSymbol.defaultSymbol(layer.geometryType())
    if (symbol is None or default is None
            or symbol.symbolLayerCount() != default.symbolLayerCount()):
        return False

    def fingerprint(sym):
        return {key: value
                for key, value in sym.symbolLayer(0).properties().items()
                if key not in RANDOM_KEYS}
    return fingerprint(symbol) == fingerprint(default)


def pro_symbol(layer):
    """Pro default symbol for ``layer``'s geometry, in a palette color."""
    color = QgsApplication.colorSchemeRegistry().fetchRandomStyleColor()
    rgb = f"{color.red()},{color.green()},{color.blue()},255"
    geometry = layer.geometryType()
    if geometry == Qgis.GeometryType.Polygon:
        return QgsFillSymbol.createSimple(
            {"color": rgb, "outline_color": OUTLINE, "outline_width": "0.7",
             "outline_width_unit": "Point"})
    if geometry == Qgis.GeometryType.Line:
        return QgsLineSymbol.createSimple(
            {"color": rgb, "width": "1", "width_unit": "Point"})
    return QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": rgb, "size": "4", "size_unit": "Point",
         "outline_color": OUTLINE, "outline_width": "0.4",
         "outline_width_unit": "Point"})


def pro_ramps():
    """(name, QGIS color ramp) of each of Pro's color ramps."""
    for item in json.loads(RAMPS.read_text(encoding="utf-8")):
        if "stops" in item:
            stops = [QgsGradientStop(p, QColor(c)) for p, c in item["stops"]]
            ramp = QgsGradientColorRamp(stops[0].color, stops[-1].color,
                                        False, stops[1:-1])
        elif "colors" in item:
            ramp = QgsPresetSchemeColorRamp([QColor(c)
                                             for c in item["colors"]])
        else:  # Pro: hue 0-360, saturation and value 0-100
            h1, h2, s1, s2, v1, v2 = item["random"]
            ramp = QgsLimitedRandomColorRamp(
                10, h1, min(h2, 359), round(s1 * 2.55), round(s2 * 2.55),
                round(v1 * 2.55), round(v2 * 2.55))
        yield f"{TAG} {item['name']}", ramp


def pro_text_format():
    """Pro's default label text symbol: Tahoma 10 pt, black."""
    text = QgsTextFormat()
    text.setFont(QFont("Tahoma"))
    text.setSize(10)
    text.setSizeUnit(Qgis.RenderUnit.Points)
    text.setColor(QColor(0, 0, 0))
    return text


def _set_project_defaults(ramp, text):
    """Project default color ramp and text format, without marking the
    project modified."""
    project = QgsProject.instance()
    dirty = project.isDirty()
    project.styleSettings().setDefaultColorRamp(ramp)
    project.styleSettings().setDefaultTextFormat(text)
    project.setDirty(dirty)


class ProSymbology:
    """Installs the palette and restyles freshly added default layers."""

    def __init__(self, changes, canvas):
        self.canvas = canvas
        previous_selection = canvas.selectionColor()
        canvas.setSelectionColor(SELECTION)
        registry = QgsApplication.colorSchemeRegistry()
        scheme = ProColorScheme()
        registry.addColorScheme(scheme)
        previous = registry.randomStyleColorScheme()
        registry.setRandomStyleColorScheme(scheme)
        style = QgsStyle.defaultStyle()
        ramps = [(RAMP_NAME, _ramp()), *pro_ramps()]
        # Ramps from the previous QGIS session are still in the style (they
        # are not removed at quit): adding them again would take seconds.
        entity = QgsStyle.StyleEntity.ColorrampEntity
        existing = set(style.colorRampNames())
        tag = style.tagId(TAG)
        tagged = set(style.symbolsWithTag(entity, tag)) if tag else set()
        for name, ramp in ramps:
            if name not in existing:
                style.addColorRamp(name, ramp, True)
            if name not in tagged:
                style.tagSymbol(entity, name, [TAG])
        project = QgsProject.instance()
        settings = project.styleSettings()
        previous_ramp = settings.defaultColorRamp()
        previous_ramp = previous_ramp.clone() if previous_ramp else None
        previous_text = QgsTextFormat(settings.defaultTextFormat())
        self.set_project_style()
        project.readProject.connect(self.set_project_style)
        project.readProject.connect(self.set_selection_color)
        project.cleared.connect(self.set_project_style)
        project.layersAdded.connect(self.restyle)

        def undo():
            canvas.setSelectionColor(previous_selection)
            project.readProject.disconnect(self.set_selection_color)
            for signal, slot in ((project.readProject, self.set_project_style),
                                 (project.cleared, self.set_project_style),
                                 (project.layersAdded, self.restyle)):
                signal.disconnect(slot)
            _set_project_defaults(previous_ramp, previous_text)
            registry.setRandomStyleColorScheme(previous)
            registry.removeColorScheme(scheme)
            for name, _ in ramps:
                style.removeColorRamp(name)
            tag = style.tagId(TAG)
            if tag:
                style.remove(QgsStyle.StyleEntity.TagEntity, tag)

        changes.add(undo)

    def set_selection_color(self, *_):
        """Pro's cyan selection, also for a project just read."""
        # QGIS applies the project's own selection color after reading it.
        QTimer.singleShot(0, lambda: self.canvas.setSelectionColor(SELECTION))

    @staticmethod
    def set_project_style(*_):
        """Pro's palette and label font as the project's defaults."""
        _set_project_defaults(_ramp(), pro_text_format())

    @staticmethod
    def restyle(layers):
        """Give layers added with QGIS's default symbol Pro's default."""
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.isSpatial() \
                    and _is_qgis_default(layer):
                layer.setRenderer(QgsSingleSymbolRenderer(pro_symbol(layer)))
                layer.triggerRepaint()
