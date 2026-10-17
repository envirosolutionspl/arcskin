"""Coordinate display units: formatting and parsing round trips."""

import unittest

from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsPointXY, QgsUnitTypes,
)
from qgis.PyQt.QtCore import QLocale

from arcskin import coords

GEOGRAPHIC = QgsCoordinateReferenceSystem("EPSG:4326")
WEB_MERCATOR = QgsCoordinateReferenceSystem("EPSG:3857")
WARSAW = QgsPointXY(21.0122, 52.2297)  # longitude, latitude
# Format -> parse error allowed per angular unit, in degrees (the texts
# carry 6 decimals of a degree, 2 of a second, 1 m of UTM / MGRS).
ANGULAR_TOLERANCE = {"dd": 1e-5, "dms": 1e-5, "ddm": 1e-5, "utm": 2e-5,
                     "mgrs": 2e-5, "usng": 2e-5}
METRES_PER_DEGREE = 111320


class FormatParse(unittest.TestCase):

    def round_trip(self, unit, crs, point, tolerance):
        text = coords.format_point(point, unit, crs)
        back = coords.parse_point(text, unit, crs)
        self.assertAlmostEqual(back.x(), point.x(), delta=tolerance, msg=text)
        self.assertAlmostEqual(back.y(), point.y(), delta=tolerance, msg=text)

    def test_angular_units_on_a_geographic_map(self):
        for unit, tolerance in ANGULAR_TOLERANCE.items():
            with self.subTest(unit=unit):
                self.round_trip(unit, GEOGRAPHIC, WARSAW, tolerance)

    def test_angular_units_on_a_projected_map(self):
        point = coords._transform(WARSAW, GEOGRAPHIC, WEB_MERCATOR)
        for unit, tolerance in ANGULAR_TOLERANCE.items():
            with self.subTest(unit=unit):
                self.round_trip(unit, WEB_MERCATOR, point,
                                tolerance * METRES_PER_DEGREE)

    def test_linear_units_on_a_projected_map(self):
        point = coords._transform(WARSAW, GEOGRAPHIC, WEB_MERCATOR)
        for unit, (_, qgis_unit) in coords.LINEAR.items():
            with self.subTest(unit=unit):
                # the text has two decimals of the unit
                tolerance = 0.006 * QgsUnitTypes.fromUnitToUnitFactor(
                    qgis_unit, Qgis.DistanceUnit.Meters)
                self.round_trip(unit, WEB_MERCATOR, point, tolerance)

    def test_group_separators_of_the_locale_are_understood(self):
        previous = QLocale()
        point = coords._transform(WARSAW, GEOGRAPHIC, WEB_MERCATOR)
        # "500 000" and "500,000" style numbers
        for locale in ("pl_PL", "en_US"):
            QLocale.setDefault(QLocale(locale))
            try:
                # metres: UTM is written to 1 m, km to 0.01 km
                for unit, tolerance in (("utm", 2), ("m", 0.1), ("km", 6),
                                        ("dd", 2)):
                    with self.subTest(locale=locale, unit=unit):
                        self.round_trip(unit, WEB_MERCATOR, point, tolerance)
            finally:
                QLocale.setDefault(previous)

    def test_linear_units_fall_back_to_degrees_on_a_geographic_map(self):
        text = coords.format_point(WARSAW, "km", GEOGRAPHIC)
        self.assertIn("°", text)
        back = coords.parse_point(text, "km", GEOGRAPHIC)
        self.assertAlmostEqual(back.x(), WARSAW.x(), delta=1e-5)

    def test_mgrs_outside_its_latitude_range(self):
        self.assertEqual(
            coords.format_point(QgsPointXY(0, 86), "mgrs", GEOGRAPHIC), "—")

    def test_hemisphere_letters_decide_the_order(self):
        point = coords.parse_point("52.2297 N 21.0122 E", "dd", GEOGRAPHIC)
        self.assertAlmostEqual(point.x(), 21.0122)
        self.assertAlmostEqual(point.y(), 52.2297)

    def test_degrees_minutes_seconds_as_plain_numbers(self):
        point = coords.parse_point("21 0 43.92 52 13 46.92", "dms",
                                   GEOGRAPHIC)
        self.assertAlmostEqual(point.x(), 21.0122, delta=1e-5)
        self.assertAlmostEqual(point.y(), 52.2297, delta=1e-5)

    def test_invalid_text_raises(self):
        for unit, text in (("dd", "abc"), ("dd", "200 10"), ("dd", ""),
                           ("utm", "34 500000 5800000"), ("mgrs", "99XYZ")):
            with self.subTest(unit=unit, text=text):
                with self.assertRaises(ValueError):
                    coords.parse_point(text, unit, GEOGRAPHIC)

    def test_unit_names_and_validity(self):
        for unit in list(coords.ANGULAR) + list(coords.LINEAR):
            self.assertTrue(coords.is_valid(unit))
            self.assertTrue(coords.unit_name(unit))
        self.assertFalse(coords.is_valid("furlong"))
