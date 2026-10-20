"""Attribute table dressing."""

import unittest

from qgis.core import QgsVectorLayer
from qgis.PyQt import sip
from qgis.PyQt.QtWidgets import QDialog, QTableView

from arcskin.dialogs import TableFooter


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


if __name__ == "__main__":
    unittest.main()
