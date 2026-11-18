"""CyanSkin - QGIS plugin giving QGIS an interface inspired by ArcGIS Pro."""

from pathlib import Path


def _install_translator():
    """Load i18n/cyanskin_<lang>.qm for the QGIS user interface language."""
    from qgis.core import QgsApplication
    from qgis.PyQt.QtCore import QCoreApplication, QTranslator

    language = QgsApplication.locale()[:2]  # QGIS's own UI language
    qm = Path(__file__).resolve().parent / "i18n" / f"cyanskin_{language}.qm"
    translator = QTranslator()
    if qm.exists() and translator.load(str(qm)):
        QCoreApplication.installTranslator(translator)
        return translator
    return None


def classFactory(iface):  # noqa: N802 (QGIS API name)
    # The translator must be installed before the modules are imported,
    # because their ribbon and pane specifications are translated then.
    translator = _install_translator()
    from .plugin import CyanSkinPlugin

    return CyanSkinPlugin(iface, translator)
