"""The undo log every interface change goes through."""

import unittest

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QWidget

from arcskin.util import Changes


class UndoLog(unittest.TestCase):

    def test_set_restores_old_values_newest_first(self):
        obj = QObject()
        obj.setObjectName("a")
        seen = []
        changes = Changes()
        changes.set(obj, "objectName", "b")
        changes.add(lambda: seen.append(obj.objectName()))
        changes.set(obj, "objectName", "c")
        changes.undo()
        self.assertEqual(obj.objectName(), "a")
        self.assertEqual(seen, ["b"], "undo of the later change ran first")

    def test_boolean_properties_use_the_is_getter(self):
        widget = QWidget()
        widget.show()
        changes = Changes()
        changes.set(widget, "visible", False)
        self.assertFalse(widget.isVisible())
        changes.undo()
        self.assertTrue(widget.isVisible())

    def test_objects_deleted_meanwhile_are_skipped(self):
        obj = QObject()
        changes = Changes()
        changes.set(obj, "objectName", "x")
        sip.delete(obj)
        changes.undo()  # no error

    def test_undo_reports_the_fraction_done(self):
        changes = Changes()
        for _ in range(4):
            changes.add(lambda: None)
        fractions = []
        changes.undo(fractions.append)
        self.assertEqual(fractions, [0.25, 0.5, 0.75, 1.0])
        changes.undo()  # nothing left: still fine
