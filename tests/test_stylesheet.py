"""The skin's block in the application style sheet, next to other sheets."""

import unittest

from qgis.PyQt.QtWidgets import QApplication, QMainWindow

from arcskin.stylesheet import (
    MARK_BEGIN, MARK_END, StyleSheetBlock, has_block, with_block,
    without_block,
)

OTHER = "/* other: begin */\nQToolButton { color: orange; }\n/* other: end */"
QSS = "QWidget { color: #4a4a4a; }"


class Block(unittest.TestCase):

    def test_block_goes_in_front_of_the_rest(self):
        sheet = with_block(OTHER, QSS)
        self.assertTrue(sheet.startswith(MARK_BEGIN))
        self.assertTrue(sheet.endswith(OTHER))
        self.assertIn(QSS, sheet)

    def test_block_alone_on_an_empty_sheet(self):
        self.assertEqual(with_block("", QSS),
                         "\n".join((MARK_BEGIN, QSS, MARK_END)))

    def test_block_is_replaced_not_doubled(self):
        sheet = with_block(with_block(OTHER, "a {}"), QSS)
        self.assertEqual(sheet.count(MARK_BEGIN), 1)
        self.assertNotIn("a {}", sheet)
        self.assertIn(QSS, sheet)

    def test_without_block_leaves_the_rest_untouched(self):
        self.assertEqual(without_block(with_block(OTHER, QSS)), OTHER)
        self.assertEqual(without_block(with_block("", QSS)), "")
        self.assertEqual(without_block(OTHER), OTHER)
        self.assertFalse(has_block(OTHER))


class Live(unittest.TestCase):
    """The block on the real application sheet, watched for replacement."""

    def setUp(self):
        self.app = QApplication.instance()
        self.app.setStyleSheet(OTHER)
        self.win = QMainWindow()
        self.block = StyleSheetBlock(self.win, QSS)

    def tearDown(self):
        if self.block.active:
            self.block.remove()
        self.app.setStyleSheet("")
        self.app.processEvents()

    def test_applied_in_front_of_what_was_there(self):
        self.assertEqual(self.app.styleSheet(), with_block(OTHER, QSS))

    def test_comes_back_after_the_sheet_is_replaced(self):
        # QGIS replaces the whole sheet when the interface font changes.
        self.app.setStyleSheet("QWidget { font-size: 11pt; }")
        self.app.processEvents()
        sheet = self.app.styleSheet()
        self.assertTrue(has_block(sheet))
        self.assertTrue(sheet.endswith("QWidget { font-size: 11pt; }"))

    def test_another_plugin_adding_its_block_is_left_alone(self):
        # The other plugin's resync appends its block behind ours.
        self.app.setStyleSheet(with_block("", QSS) + "\n" + OTHER)
        self.app.processEvents()
        self.assertEqual(self.app.styleSheet().count(MARK_BEGIN), 1)
        self.assertIn(OTHER, self.app.styleSheet())

    def test_remove_takes_only_the_block_out(self):
        self.block.remove()
        self.assertEqual(self.app.styleSheet(), OTHER)
        # Nothing watches any more: a later sheet stays as set.
        self.app.setStyleSheet("")
        self.app.processEvents()
        self.assertEqual(self.app.styleSheet(), "")
