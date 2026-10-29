"""Attribute table dressing."""

import unittest

from qgis.core import QgsVectorLayer
from qgis.PyQt import sip
from qgis.PyQt.QtWidgets import QDialog, QTableView, QWidget

from arcskin.dialogs import TableFooter
from arcskin.icon_theme import holders_in


class Footer(unittest.TestCase):

    def test_removing_the_footer_of_a_closed_table_is_harmless(self):
        # QGIS deletes an attribute table when it is closed; switching the
        # skin off afterwards must not fail on the footer's deleted widgets.
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "points", "memory")
        dialog = QDialog()
        QTableView(dialog, objectName="mTableView")
        footer = TableFooter(dialog, layer)
        footer.setParent(dialog)
        sip.delete(dialog)
        footer.remove()  # no error

    def test_removing_the_footer_resets_the_zoom(self):
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "points", "memory")
        dialog = QDialog()
        QTableView(dialog, objectName="mTableView")
        footer = TableFooter(dialog, layer)
        footer.setParent(dialog)
        footer.zoom.setValue(150)
        footer.remove()
        self.assertEqual(footer.zoom.value(), 100)

    def test_the_icon_theme_can_walk_an_open_footer(self):
        # The skin going on again with a table open swaps the icons of
        # all widgets, the footer among them: its actions() must work.
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "points", "memory")
        dialog = QDialog()
        QTableView(dialog, objectName="mTableView")
        footer = TableFooter(dialog, layer)
        footer.setParent(dialog)
        holders_in([footer] + footer.findChildren(QWidget))  # no error


if __name__ == "__main__":
    unittest.main()
