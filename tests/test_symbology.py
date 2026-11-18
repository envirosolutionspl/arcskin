"""Default symbols, colour ramps and label text format."""

import json
import unittest

from qgis.core import (
    Qgis, QgsFillSymbol, QgsFontUtils, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer,
)

import build_color_ramps
from cyanskin import symbology


def memory_layer(geometry):
    layer = QgsVectorLayer(f"{geometry}?crs=EPSG:4326", geometry, "memory")
    assert layer.isValid()
    return layer


class DefaultSymbols(unittest.TestCase):

    def test_a_fresh_layer_has_the_qgis_default_symbol(self):
        for geometry in ("Point", "LineString", "Polygon"):
            with self.subTest(geometry=geometry):
                self.assertTrue(
                    symbology._is_qgis_default(memory_layer(geometry)))

    def test_the_skin_symbol_is_not_taken_for_the_qgis_default(self):
        layer = memory_layer("Polygon")
        layer.setRenderer(QgsSingleSymbolRenderer(symbology.default_symbol(layer)))
        self.assertFalse(symbology._is_qgis_default(layer))

    def test_default_symbol_matches_the_geometry(self):
        expected = {"Point": QgsMarkerSymbol, "LineString": QgsLineSymbol,
                    "Polygon": QgsFillSymbol}
        for geometry, kind in expected.items():
            with self.subTest(geometry=geometry):
                symbol = symbology.default_symbol(memory_layer(geometry))
                self.assertIsInstance(symbol, kind)
                self.assertTrue(symbol.color().isValid())

    def test_polygons_get_a_grey_outline(self):
        symbol = symbology.default_symbol(memory_layer("Polygon"))  # kept alive
        props = symbol.symbolLayer(0).properties()
        self.assertEqual(props["outline_width"], "0.7")
        self.assertEqual(props["outline_width_unit"], "Point")


class ColorRamps(unittest.TestCase):

    def test_ramps_load_with_unique_prefixed_names(self):
        ramps = list(symbology.bundled_ramps())
        names = [name for name, _ in ramps]
        self.assertEqual(len(ramps), len(build_color_ramps.RAMPS))
        self.assertEqual(len(set(names)), len(names), "duplicate names")
        for name, ramp in ramps:
            self.assertTrue(name.startswith(f"{symbology.TAG} "), name)
            self.assertTrue(ramp.color(0.0).isValid(), name)
            self.assertTrue(ramp.color(1.0).isValid(), name)

    def test_bundled_file_is_what_the_script_builds(self):
        bundled = json.loads(symbology.RAMPS.read_text(encoding="utf-8"))
        self.assertEqual(
            [(r["name"], r["group"], r["stops"]) for r in bundled],
            [(n, g, s) for n, g, s in build_color_ramps.RAMPS])

    def test_stops_run_from_0_to_1(self):
        for name, _, stops in build_color_ramps.RAMPS:
            with self.subTest(ramp=name):
                positions = [p for p, _ in stops]
                self.assertEqual((positions[0], positions[-1]), (0.0, 1.0))
                self.assertEqual(positions, sorted(positions))


class TextFormat(unittest.TestCase):

    def test_label_font(self):
        text = symbology.label_text_format()
        if QgsFontUtils.fontFamilyOnSystem("Tahoma"):
            self.assertEqual(text.font().family(), "Tahoma")
        else:  # Linux: no missing font stored in the project
            self.assertEqual(text.font().family(),
                             QgsTextFormat().font().family())
        self.assertEqual(text.size(), 10)
        self.assertEqual(text.sizeUnit(), Qgis.RenderUnit.Points)
        self.assertEqual(text.color().name(), "#000000")
