"""metadata.txt as the QGIS plugin repository expects it."""

import configparser
import re
import unittest

import package
from arcskin.plugin import PLUGIN_DIR

REQUIRED = ("name", "qgisMinimumVersion", "description", "about", "version",
            "author", "email", "repository")


class Metadata(unittest.TestCase):

    def setUp(self):
        config = configparser.ConfigParser()
        config.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
        self.meta = config["general"]

    def test_required_fields_are_filled(self):
        for key in REQUIRED:
            self.assertTrue(self.meta.get(key), key)

    def test_version_matches_the_newest_changelog_entry(self):
        version = self.meta["version"]
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        first = self.meta["changelog"].strip().splitlines()[0]
        self.assertEqual(re.match(r"\S+", first).group(), version)

    def test_icon_exists(self):
        self.assertTrue((PLUGIN_DIR / self.meta["icon"]).exists())

    def test_flags_are_booleans(self):
        for key in ("experimental", "deprecated", "server"):
            self.assertIn(self.meta[key], ("True", "False"), key)

    def test_qgis4_support_comes_from_the_maximum_version(self):
        # plugins.qgis.org reads QGIS 4 support from qgisMaximumVersion only
        # and flags the old supportsQt6 key as deprecated.
        self.assertNotIn("supportsQt6", self.meta)
        self.assertGreaterEqual(float(self.meta["qgisMaximumVersion"]), 4.99)

    def test_packaging_reads_the_same_version(self):
        self.assertEqual(package.plugin_version(), self.meta["version"])
