"""Settings and colour ramps of the plugin's earlier name."""

import tempfile
import unittest
from pathlib import Path

from qgis.core import QgsGradientColorRamp, QgsStyle
from qgis.PyQt.QtCore import QSettings

from cyanskin import legacy


class Settings(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QSettings(str(Path(self.directory.name) / "s.ini"),
                                  QSettings.Format.IniFormat)

    def tearDown(self):
        del self.settings
        self.directory.cleanup()

    def test_old_settings_are_taken_over_and_removed(self):
        self.settings.setValue("arcskin/enabled", False)
        self.settings.setValue("arcskin/original_ui_theme", "Night Mapping")
        legacy.migrate_settings(self.settings)
        self.assertEqual(self.settings.value("cyanskin/enabled"), False)
        self.assertEqual(self.settings.value("cyanskin/original_ui_theme"),
                         "Night Mapping")
        self.assertEqual(self.settings.allKeys(),
                         ["cyanskin/enabled", "cyanskin/original_ui_theme"])

    def test_newer_settings_are_kept(self):
        self.settings.setValue("arcskin/coordinate_format", "dms")
        self.settings.setValue("cyanskin/coordinate_format", "utm")
        legacy.migrate_settings(self.settings)
        self.assertEqual(self.settings.value("cyanskin/coordinate_format"),
                         "utm")

    def test_old_ui_theme_falls_back_to_the_one_before_it(self):
        self.settings.setValue("UI/UITheme", "ArcSkin")
        self.settings.setValue("arcskin/original_ui_theme", "Blend of Gray")
        legacy.migrate_settings(self.settings)
        self.assertEqual(self.settings.value("UI/UITheme"), "Blend of Gray")

    def test_old_ui_theme_without_record_falls_back_to_default(self):
        self.settings.setValue("UI/UITheme", "ArcSkin")
        legacy.migrate_settings(self.settings)
        self.assertEqual(self.settings.value("UI/UITheme"), "default")


class Ramps(unittest.TestCase):

    def test_old_ramps_and_their_tag_are_removed(self):
        style = QgsStyle()
        style.createMemoryDatabase()
        entity = QgsStyle.StyleEntity.ColorrampEntity
        for name in ("Old A", "Old B", "Mine"):
            style.addColorRamp(name, QgsGradientColorRamp(), True)
        for name in ("Old A", "Old B"):
            style.tagSymbol(entity, name, [legacy.OLD_TAG])
        legacy.remove_old_ramps(style)
        self.assertEqual(style.colorRampNames(), ["Mine"])
        self.assertFalse(style.tagId(legacy.OLD_TAG))
