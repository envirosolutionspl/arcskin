"""Pro default symbols, colour ramps and label text format."""

import unittest

from qgis.core import (
    Qgis, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer, QgsVectorLayer,
)

from arcskin import symbology


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

    def test_a_pro_symbol_is_not_taken_for_the_default(self):
        layer = memory_layer("Polygon")
        layer.setRenderer(QgsSingleSymbolRenderer(symbology.pro_symbol(layer)))
        self.assertFalse(symbology._is_qgis_default(layer))

    def test_pro_symbol_matches_the_geometry(self):
        expected = {"Point": QgsMarkerSymbol, "LineString": QgsLineSymbol,
                    "Polygon": QgsFillSymbol}
        for geometry, kind in expected.items():
            with self.subTest(geometry=geometry):
                symbol = symbology.pro_symbol(memory_layer(geometry))
                self.assertIsInstance(symbol, kind)
                self.assertTrue(symbol.color().isValid())

    def test_polygons_get_pro_outline(self):
        symbol = symbology.pro_symbol(memory_layer("Polygon"))  # kept alive
        props = symbol.symbolLayer(0).properties()
        self.assertEqual(props["outline_width"], "0.7")
        self.assertEqual(props["outline_width_unit"], "Point")


class ColorRamps(unittest.TestCase):

    def test_ramps_load_with_unique_prefixed_names(self):
        ramps = list(symbology.pro_ramps())
        names = [name for name, _ in ramps]
        self.assertGreaterEqual(len(ramps), 100)
        self.assertEqual(len(set(names)), len(names), "duplicate names")
        for name, ramp in ramps:
            self.assertTrue(name.startswith(f"{symbology.TAG} "), name)
            self.assertTrue(ramp.color(0.0).isValid(), name)
            self.assertTrue(ramp.color(1.0).isValid(), name)


class TextFormat(unittest.TestCase):

    def test_pro_label_font(self):
        text = symbology.pro_text_format()
        self.assertEqual(text.font().family(), "Tahoma")
        self.assertEqual(text.size(), 10)
        self.assertEqual(text.sizeUnit(), Qgis.RenderUnit.Points)
        self.assertEqual(text.color().name(), "#000000")
