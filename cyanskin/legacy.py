"""Settings and leftovers of the plugin's earlier name, ArcSkin.

CyanSkin continues the plugin published as ArcSkin. On start it takes
over ArcSkin's settings (so that QGIS's own window layout and UI theme can
still be restored) and removes what ArcSkin left in QGIS: its colour ramps
in the QGIS style and its icon theme folder. Layers added from the basemap
gallery under the old name stay recognised.
"""

import shutil
from pathlib import Path

from qgis.core import QgsApplication, QgsStyle

OLD = "arcskin"  # settings group and plugin package
OLD_THEME = "ArcSkin"  # icon theme folder and UI theme name
OLD_TAG = "ArcSkin"  # tag of the colour ramps in the QGIS style
OLD_MARKER = "arcskin.version"  # file marking the icon theme folder
OLD_BASEMAP = "arcskin/basemap"  # custom property of basemap layers
KEYS = ("enabled", "original_window_state", "original_ui_theme",
        "coordinate_format")
THEME_KEY = "UI/UITheme"


def old_plugin_active():
    """Whether the old plugin is loaded next to this one."""
    from qgis import utils
    return OLD in utils.active_plugins


def migrate_settings(settings, new="cyanskin"):
    """Copy the old settings to ``new`` (keeping newer ones), drop them.

    A UI theme still set to the old icon theme falls back to the theme
    QGIS had before it.
    """
    for key in KEYS:
        value = settings.value(f"{OLD}/{key}")
        if value is not None and settings.value(f"{new}/{key}") is None:
            settings.setValue(f"{new}/{key}", value)
    settings.remove(OLD)
    if settings.value(THEME_KEY) == OLD_THEME:
        settings.setValue(THEME_KEY,
                          settings.value(f"{new}/original_ui_theme",
                                         "default"))


def remove_old_ramps(style=None):
    """Remove the colour ramps tagged with the old name, and the tag."""
    style = style or QgsStyle.defaultStyle()
    tag = style.tagId(OLD_TAG)
    if not tag:
        return
    entity = QgsStyle.StyleEntity.ColorrampEntity
    for name in style.symbolsWithTag(entity, tag):
        style.removeColorRamp(name)
    style.remove(QgsStyle.StyleEntity.TagEntity, tag)


def remove_old_theme():
    """Delete the old icon theme folder, unless QGIS runs with it now
    (its icons are read from there until QGIS restarts)."""
    if QgsApplication.themeName() == OLD_THEME:
        return
    for folder in (QgsApplication.defaultThemesFolder(),
                   QgsApplication.userThemesFolder()):
        target = Path(folder) / OLD_THEME
        if (target / OLD_MARKER).is_file():  # made by the plugin
            shutil.rmtree(target, ignore_errors=True)


def migrate(settings):
    """Everything above, for a start next to no old plugin."""
    migrate_settings(settings)
    remove_old_ramps()
    remove_old_theme()
