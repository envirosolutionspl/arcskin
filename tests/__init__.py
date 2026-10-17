"""ArcSkin test suite: unit tests that need no QGIS window.

Run with QGIS's Python, from the repository root:

    C:/OSGeo4W/bin/python-qgis.bat -m unittest discover -s tests -t . -v

(``-t .`` makes unittest import the tests as the ``tests`` package, so that
this file runs first.)

One QgsApplication is started for all tests (offscreen when nothing else
is asked for). The plugin package and the build scripts are imported from
the repository. ``smoke_in_qgis.py`` is not part of this suite: it runs
inside a QGIS session with the plugin loaded.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication  # noqa: E402 (path set up above)

APP = QgsApplication([], True)
APP.initQgis()
