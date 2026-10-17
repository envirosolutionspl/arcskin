"""Translations: the .ts files follow the code and compile to working .qm."""

import tempfile
import unittest
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, QTranslator

import i18n


class Translations(unittest.TestCase):

    def test_ts_files_list_exactly_the_strings_in_the_code(self):
        sources = set(i18n.source_strings())
        for path in i18n.I18N.glob("arcskin_*.ts"):
            with self.subTest(file=path.name):
                self.assertEqual(set(i18n.read_ts(path)), sources)

    def test_polish_is_complete_and_keeps_the_placeholders(self):
        entries = i18n.read_ts(i18n.I18N / "arcskin_pl.ts")
        self.assertEqual([s for s, t in entries.items() if not t], [])
        for source, translation in entries.items():
            self.assertEqual(source.count("{}"), translation.count("{}"),
                             source)

    def test_compiled_qm_translates(self):
        entries = i18n.read_ts(i18n.I18N / "arcskin_pl.ts")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "arcskin_pl.qm"
            i18n.write_qm(path, entries)
            translator = QTranslator()
            self.assertTrue(translator.load(str(path)))
            app = QCoreApplication.instance()
            app.installTranslator(translator)
            try:
                for source in ("Contents", "Catalog", "Selected features: {}"):
                    self.assertEqual(
                        QCoreApplication.translate(i18n.CONTEXT, source),
                        entries[source])
            finally:
                app.removeTranslator(translator)
