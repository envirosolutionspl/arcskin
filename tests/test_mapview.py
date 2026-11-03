"""Pro's map scale box under the map."""

import unittest

from qgis.PyQt.QtCore import QObject, Qt, pyqtSignal
from qgis.PyQt.QtTest import QTest

from arcskin.mapview import ScaleBox


class Canvas(QObject):
    """The part of QgsMapCanvas the scale box uses; records the zooms."""

    scaleChanged = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.zooms = []

    def scale(self):
        return 10000.0

    def zoomScale(self, scale):  # noqa: N802 (QGIS API name)
        self.zooms.append(scale)


class Scale(unittest.TestCase):

    def setUp(self):
        self.canvas = Canvas()
        self.box = ScaleBox(self.canvas)

    def test_a_typed_scale_zooms_without_a_new_list_entry(self):
        # An editable combo box added the typed text as an entry without
        # a scale and activated it: zoomScale(None) failed (issue #5).
        count = self.box.count()
        self.box.lineEdit().setText("1:12 345")
        QTest.keyClick(self.box.lineEdit(), Qt.Key.Key_Return)
        self.assertEqual(self.box.count(), count)
        self.assertNotIn(None, self.canvas.zooms)
        self.assertEqual(self.canvas.zooms[-1], 12345)

    def test_picking_a_listed_scale_zooms(self):
        self.box.activated.emit(self.box.findData(50000))
        self.assertEqual(self.canvas.zooms, [50000])
