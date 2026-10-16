"""Generate arcskin/resources/qgis_theme: every QGIS icon in the Pro style.

Run with QGIS's Python (the icons live in QGIS's compiled Qt resources):

    C:\\OSGeo4W\\bin\\python-qgis.bat scripts\\build_icon_theme.py

Each SVG icon of QGIS's default theme is flattened (gradients become solid
colours), recoloured to the Pro palette and given Pro's light, tinted
outlines instead of dark ones (``soften``, also used on the hand-drawn
icons). Hand-drawn icons are then copied
on top: ``resources/icons/theme_overrides/*.svg`` under their own (QGIS)
names, and the ribbon icons from ``resources/icons/pro`` under the QGIS
names listed in PRO_AS_QGIS. QGIS's icons are GPL-2.0-or-later, like this
plugin.
"""

import colorsys
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "arcskin" / "resources" / "icons"
OUT = ROOT / "arcskin" / "resources" / "qgis_theme"
SOURCE = ":/images/themes/default"

# Colour family -> (light, mid, dark) Pro palette tones.
FAMILIES = {
    "red": ("#f6c3bf", "#d0352b", "#9a2018"),
    "orange": ("#fbd9b0", "#f0a050", "#c0601a"),
    "yellow": ("#fbe7a6", "#f2b822", "#b08300"),
    "green": ("#cfe3b4", "#3a9e3a", "#23702a"),
    "blue": ("#c8e3f6", "#007ac2", "#005e95"),
    "purple": ("#e3d8f3", "#8a63c4", "#5a3d8a"),
}
NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000",
         "green": "#008000", "blue": "#0000ff", "yellow": "#ffff00",
         "gray": "#808080", "grey": "#808080", "orange": "#ffa500"}

# Ribbon icon (resources/icons/pro/<key>.svg) -> QGIS theme icon names.
PRO_AS_QGIS = {
    "pan": ["mActionPan.svg"],
    "zoom_in": ["mActionZoomIn.svg"],
    "zoom_out": ["mActionZoomOut.svg"],
    "full_extent": ["mActionZoomFullExtent.svg"],
    "zoom_layer": ["mActionZoomToLayer.svg"],
    "prev_extent": ["mActionZoomLast.svg"],
    "next_extent": ["mActionZoomNext.svg"],
    "zoom_selected": ["mActionZoomToSelected.svg"],
    "pan_selected": ["mActionPanToSelected.svg"],
    "identify": ["mActionIdentify.svg"],
    "measure": ["mActionMeasure.svg"],
    "measure_area": ["mActionMeasureArea.svg"],
    "select": ["mActionSelectRectangle.svg"],
    "select_expression": ["mIconExpressionSelect.svg"],
    "select_all": ["mActionSelectAll.svg"],
    "clear_selection": ["mActionDeselectAll.svg"],
    "invert_selection": ["mActionInvertSelection.svg"],
    "new_project": ["mActionFileNew.svg"],
    "open_project": ["mActionFileOpen.svg"],
    "save_project": ["mActionFileSave.svg"],
    "save_as": ["mActionFileSaveAs.svg"],
    "project_properties": ["mActionProjectProperties.svg"],
    "options": ["mActionOptions.svg"],
    "exit": ["mActionFileExit.svg"],
    "new_map": ["mActionNewMap.svg"],
    "new_layout": ["mActionNewLayout.svg"],
    "layout_manager": ["mActionLayoutManager.svg"],
    "add_data": ["mActionDataSourceManager.svg"],
    "add_vector": ["mActionAddOgrLayer.svg"],
    "add_raster": ["mActionAddRasterLayer.svg"],
    "add_wms": ["mActionAddWmsLayer.svg"],
    "add_csv": ["mActionAddDelimitedTextLayer.svg"],
    "style_manager": ["mActionStyleManager.svg",
                      "propertyicons/stylepreset.svg"],
    "bookmarks": ["mActionShowBookmarks.svg"],
    "new_bookmark": ["mActionNewBookmark.svg"],
    "statistics": ["algorithms/mAlgorithmBasicStatistics.svg"],
    "map_tips": ["mActionMapTips.svg"],
    "label_move": ["mActionMoveLabel.svg"],
    "field_calculator": ["mActionCalculateField.svg"],
    "attribute_table": ["mActionOpenTable.svg",
                        "propertyicons/attributes.svg"],
    "toolbox": ["processingAlgorithm.svg"],
    "model_builder": ["processingModel.svg"],
    "history": ["mIconHistory.svg", "mActionHistory.svg"],
    "edit": ["mActionToggleEditing.svg"],
    "save_edits": ["mActionSaveEdits.svg"],
    "undo": ["mActionUndo.svg"],
    "redo": ["mActionRedo.svg"],
    "vertex_tool": ["mActionVertexTool.svg"],
    "delete": ["mActionDeleteSelected.svg"],
    "move": ["mActionMoveFeature.svg"],
    "rotate": ["mActionRotateFeature.svg"],
    "scale": ["mActionScaleFeature.svg"],
    "split": ["mActionSplitFeatures.svg"],
    "merge": ["mActionMergeFeatures.svg"],
    "reshape": ["mActionReshape.svg"],
    "snapping": ["mIconSnapping.svg"],
    "cut": ["mActionEditCut.svg"],
    "copy": ["mActionEditCopy.svg"],
    "paste": ["mActionEditPaste.svg"],
    "multi_edit": ["mActionMultiEdit.svg"],
    "export_image": ["mActionSaveMapAsImage.svg"],
    "export_pdf": ["mActionSaveAsPDF.svg"],
    "print": ["mActionFilePrint.svg"],
    "help": ["mActionHelpContents.svg"],
    "plugins": ["mActionShowPluginManager.svg"],
    "refresh": ["mActionRefresh.svg"],
    "filter": ["mActionFilter2.svg"],
    "add_group": ["mActionAddGroup.svg"],
    "expand_all": ["mActionExpandTree.svg"],
    "collapse_all": ["mActionCollapseTree.svg"],
    "remove_layer": ["mActionRemoveLayer.svg"],
    "map_3d": ["mActionNew3DMap.svg", "3d.svg"],
    "temporal": ["propertyicons/temporal.svg"],
    "message_log": ["mMessageLog.svg"],
    "python": ["console/mIconRunConsole.svg"],
    "python_script": ["processingScript.svg", "mIconPythonFile.svg"],
    "symbology": ["propertyicons/symbology.svg"],
    # Layer Styling / Properties pages
    "labeling": ["labelingSingle.svg"],
    "transparency": ["propertyicons/transparency.svg"],
    "histogram": ["propertyicons/histogram.svg"],
    "shading": ["mShadingRenderer.svg"],
    "mask": ["propertyicons/labelmask.svg"],
    "diagram": ["propertyicons/diagram.svg"],
}

HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
GRADIENT = re.compile(
    r"<(linear|radial)Gradient\b([^>]*?)(/>|>(.*?)</\1Gradient>)", re.S)
JUNK = re.compile(r"<metadata\b.*?</metadata>|<!--.*?-->"
                  r"|<sodipodi:namedview\b.*?(?:/>|</sodipodi:namedview>)",
                  re.S)


def _rgb(colour):
    colour = NAMED.get(colour.lower(), colour).lstrip("#")
    if len(colour) == 3:
        colour = "".join(c * 2 for c in colour)
    return tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))


def pro_colour(colour):
    """Map any colour to the nearest tone of the Pro palette."""
    hue, light, sat = colorsys.rgb_to_hls(*_rgb(colour))
    if sat < 0.2 or light > 0.95 or light < 0.06:
        for limit, grey in ((0.93, "#ffffff"), (0.75, "#dfdfdf"),
                            (0.5, "#959595")):
            if light > limit:
                return grey
        return "#4a4a4a"
    hue *= 360
    for limit, family in ((15, "red"), (40, "orange"), (70, "yellow"),
                          (165, "green"), (255, "blue"), (330, "purple")):
        if hue < limit:
            break
    else:
        family = "red"
    tone = 0 if light > 0.72 else 2 if light < 0.3 else 1
    return FAMILIES[family][tone]


def flatten(svg):
    """Replace gradient fills by their average colour, recolour, strip."""
    svg = JUNK.sub("", svg)
    stops, links = {}, {}
    for match in GRADIENT.finditer(svg):
        attrs, body = match.group(2), match.group(4) or ""
        gid = re.search(r'\bid="([^"]+)"', attrs)
        if not gid:
            continue
        href = re.search(r'href="#([^"]+)"', attrs)
        if href:
            links[gid.group(1)] = href.group(1)
        found = re.findall(r'stop-color[:=]\s*"?\s*(#[0-9a-fA-F]{3,6})', body)
        if found:
            stops[gid.group(1)] = found

    def average(gid, depth=0):
        if gid in stops:
            rgbs = [_rgb(c) for c in stops[gid]]
            mean = [sum(c[i] for c in rgbs) / len(rgbs) for i in range(3)]
            return "#" + "".join(f"{round(v * 255):02x}" for v in mean)
        if gid in links and depth < 5:
            return average(links[gid], depth + 1)
        return None

    svg = re.sub(r"url\(#([^)]+)\)",
                 lambda m: average(m.group(1)) or m.group(0), svg)
    svg = HEX.sub(lambda m: pro_colour(m.group(0)), svg)
    return re.sub(r'(fill|stroke)(="|:\s*)(black|white)\b',
                  lambda m: m.group(1) + m.group(2)
                  + pro_colour(m.group(3)), svg)


DARK = "#4a4a4a"
SHAPE = re.compile(
    r"<(g|path|rect|circle|ellipse|polygon|polyline|line)\b([^>]*?)(/?)>")


def _hex(rgb):
    return "#" + "".join(f"{round(c * 255):02x}" for c in rgb)


def _outline(fill):
    """Pro-like outline for a shape filled with ``fill``: thin and tinted
    (gold on yellow, dark red on red, ...), light grey on white."""
    if fill in (None, "none"):
        return "#6b6b6b", None  # line art: a lighter grey
    hue, light, sat = colorsys.rgb_to_hls(*_rgb(fill))
    if light > 0.9:
        return "#8f8f8f", "1.5"
    if sat < 0.12:
        grey = colorsys.hls_to_rgb(hue, max(light - 0.18, 0), sat)
        return _hex(grey), "1.5"
    tint = colorsys.hls_to_rgb(hue, light * 0.62, min(sat, 0.85))
    return _hex(tint), "1.5"


def soften(svg):
    """Replace the dark outlines (and dark fills) of an icon by Pro's
    lighter, tinted ones."""
    def shape(match):
        name, attrs, close = match.groups()
        low = attrs.lower()
        if f'stroke="{DARK}"' not in low and f"stroke:{DARK}" not in low:
            return match.group(0)
        fill = re.search(r'fill[=:]"?(#[0-9a-fA-F]{6}|none)', attrs)
        fill = fill.group(1).lower() if fill else None
        stroke, width = _outline("#666666" if fill == DARK else fill)
        attrs = re.sub(r'(stroke[=:]"?)' + DARK, r"\g<1>" + stroke, attrs,
                       flags=re.I)
        if width and "stroke-width" not in low:
            attrs += f' stroke-width="{width}"'
        return f"<{name}{attrs}{close}>"
    svg = SHAPE.sub(shape, svg)
    return re.sub(r'(fill[=:]"?)' + DARK, r"\g<1>#666666", svg, flags=re.I)


def main():
    from qgis.core import QgsApplication
    from qgis.PyQt.QtCore import QDirIterator, QFile

    app = QgsApplication([], False)
    app.initQgis()
    for old in OUT.rglob("*.svg"):  # folders stay
        old.unlink()
    icons = OUT / "icons"
    names = set()
    it = QDirIterator(SOURCE, QDirIterator.IteratorFlag.Subdirectories)
    while it.hasNext():
        path = it.next()
        if not path.endswith(".svg"):
            continue
        name = path[len(SOURCE) + 1:]
        names.add(name)
        source = QFile(path)
        source.open(QFile.OpenModeFlag.ReadOnly)
        target = icons / name
        target.parent.mkdir(parents=True, exist_ok=True)
        text = bytes(source.readAll()).decode("utf-8", "replace")
        target.write_text(soften(flatten(text)), encoding="utf-8")
    for svg in (ICONS / "theme_overrides").glob("*.svg"):
        shutil.copy(svg, icons / svg.name)
    for key, targets in PRO_AS_QGIS.items():
        for name in targets:
            if name not in names:
                print("not a QGIS icon:", name)
            (icons / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ICONS / "pro" / f"{key}.svg", icons / name)
    (OUT / "style.qss").write_text("/* ArcSkin icon theme */\n")
    (OUT / "variables.qss").write_text("")
    print(f"{len(names)} QGIS icons restyled into {OUT}")
    app.exitQgis()


if __name__ == "__main__":
    main()
