"""Basemap gallery: open services only, vector tile styles that draw."""

import unittest

from qgis.core import QgsVectorTileBasicRendererStyle

from arcskin import basemaps


class Services(unittest.TestCase):

    def test_no_esri_services(self):
        for name, _, uri, credits in basemaps.BASEMAPS:
            with self.subTest(name=name):
                self.assertNotIn("arcgis", (uri or "").lower())
                self.assertNotIn("esri", (credits or "").lower())

    def test_every_basemap_has_credits(self):
        for name, _, uri, credits in basemaps.BASEMAPS:
            if uri:
                self.assertTrue(credits, name)


class VectorTileFilter(unittest.TestCase):

    def fixed(self, expression):
        style = QgsVectorTileBasicRendererStyle("water", "water")
        style.setFilterExpression(expression)
        return basemaps._fix_filter(style).filterExpression()

    def test_geometry_type_check_without_field_is_dropped(self):
        # QGIS turns MapLibre's ["geometry-type"] into an empty field name,
        # which hid every polygon and line of the OpenFreeMap styles.
        self.assertEqual(
            self.fixed("(\"\" IN ('MultiPolygon', 'Polygon')) AND "
                       "(\"brunnel\" IS NOT 'tunnel')"),
            "(TRUE) AND (\"brunnel\" IS NOT 'tunnel')")

    def test_other_filters_are_kept(self):
        self.assertEqual(self.fixed("\"class\" IN ('wood', 'forest')"),
                         "\"class\" IN ('wood', 'forest')")
