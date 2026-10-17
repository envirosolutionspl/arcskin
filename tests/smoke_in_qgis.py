"""Smoke test to run inside QGIS with ArcSkin loaded.

In the QGIS Python console (the look must be on):

    exec(open(r"<repo>/tests/smoke_in_qgis.py", encoding="utf-8").read())

It switches the look off, checks that QGIS is back as it was, switches
the look on again and checks that the skin is complete. Prints PASS or
the failed checks. Takes about half a minute.
"""

import qgis.utils
from qgis.core import QgsSettings, QgsStyle
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QApplication, QTabBar, QToolBar, QToolButton, QWidget,
)

from arcskin.ribbon import ADDIN_HOSTS

# QGIS toolbars and tools the ribbon does not offer (yet).
LATER_BARS = {"mLabelToolBar", "mRasterToolBar", "mAnnotationsToolBar",
              "mGpsToolBar", "mMeshToolBar"}
LATER = {"mActionRotatePointSymbols", "mActionOffsetPointSymbol",
         "mActionZoomActualSize", "mActionFeatureAction",
         "Circular string by radius",
         "Show Vertex Editor"}  # the ribbon has the Vertex Editor panel


def toolbar_actions(bar):
    """Actions of a toolbar, including the drop-down menus of its buttons
    (but not its embedded widgets such as spin boxes)."""
    actions = []
    for action in bar.actions():
        button = bar.widgetForAction(action)
        if button is None:
            actions.append(action)
        elif isinstance(button, QToolButton):
            actions += button.actions()
            if button.menu():
                actions += button.menu().actions()
    return [a for a in actions if a.text() and not a.isSeparator()]


def missing_from_ribbon(win):
    """Names of core QGIS toolbar actions that no ribbon button or drop-down
    reaches (the full QGIS menu of the Project button does not count)."""
    ribbon = next(bar for bar in win.findChildren(QToolBar,
                                                  "ArcSkinRibbonBar")
                  if bar.isVisible())
    qgis_menus = {sip.unwrapinstance(a) for a in win.menuBar().actions()}
    reached, menus = set(), []
    for button in ribbon.findChildren(QToolButton):
        if button.defaultAction():
            reached.add(sip.unwrapinstance(button.defaultAction()))
        if button.menu():
            menus.append(button.menu())
            reached.add(sip.unwrapinstance(button.menu().menuAction()))
    while menus:
        actions = menus.pop().actions()
        if any(sip.unwrapinstance(a) in qgis_menus for a in actions):
            continue  # the QGIS Menu entry
        for action in actions:
            reached.add(sip.unwrapinstance(action))
            if action.menu():
                menus.append(action.menu())
    missing = []
    for bar in win.findChildren(QToolBar):
        name = bar.objectName()
        if (bar.parent() is not win or not name.startswith("m")
                or name in ADDIN_HOSTS | LATER_BARS):
            continue
        for action in toolbar_actions(bar):
            key = action.objectName() or action.text()
            if sip.unwrapinstance(action) not in reached and key not in LATER:
                missing.append(key)
    return missing


def smoke_test(iface):
    """Failed checks of an off / on cycle (none when all is well)."""
    plugin = qgis.utils.plugins["arcskin"]
    win, canvas = iface.mainWindow(), iface.mapCanvas()
    failures = []

    def expect(condition, what):
        if not condition:
            failures.append(what)

    def arcskin_widgets():
        return [w.objectName() for w in win.findChildren(QWidget)
                if w.objectName().startswith("ArcSkin") and w.isVisible()]

    def ramps():
        return [name for name in QgsStyle.defaultStyle().colorRampNames()
                if name.startswith("ArcSkin ")]

    def qgis_toolbars():
        return [bar for bar in win.findChildren(QToolBar)
                if bar.parent() is win and bar.actions()
                and bar.objectName() != "ArcSkinRibbonBar"]

    def skinned():
        # QGIS has a style sheet of its own (the UI theme's), so look
        # for a selector of the plugin's one.
        return "#ArcSkinRibbon" in QApplication.instance().styleSheet()

    def ribbon_shown():
        # The old ribbon lingers hidden until Qt deletes it.
        return any(bar.isVisible() for bar in
                   win.findChildren(QToolBar, "ArcSkinRibbonBar"))

    def switch(on):
        plugin.action.setChecked(on)
        QCoreApplication.processEvents()  # Qt lays the window out

    expect(plugin.action.isChecked(), "the look is on at the start")
    switch(False)
    expect(not skinned(), "ArcSkin style sheet removed")
    expect(win.statusBar().isVisible(), "status bar back")
    expect(win.menuBar().isVisible(), "menu bar back")
    expect(any(bar.isVisible() for bar in qgis_toolbars()),
           "QGIS toolbars back")
    expect(not arcskin_widgets(),
           f"no ArcSkin widgets left: {arcskin_widgets()}")
    expect(not ramps(), "ArcSkin colour ramps removed from the style")
    expect(QgsSettings().value("UI/UITheme") != "ArcSkin",
           "UI theme setting restored")
    expect(canvas.renderFlag(), "map drawing on")

    switch(True)
    expect(ribbon_shown(), "ribbon shown")
    expect(win.findChild(QTabBar, "ArcSkinViewTabs") is not None,
           "view tabs above the map")
    expect(win.findChild(QWidget, "ArcSkinMapFooter") is not None,
           "footer under the map")
    expect(not win.statusBar().isVisible(), "status bar hidden")
    expect(skinned(), "ArcSkin style sheet applied")
    expect(len(ramps()) >= 100, "ArcSkin colour ramps in the style")
    expect(QgsSettings().value("UI/UITheme") == "ArcSkin", "UI theme set")
    missing = missing_from_ribbon(win)
    expect(not missing, f"QGIS tools the ribbon lacks: {missing}")
    return failures


if __name__ == "__console__" or "iface" in globals():
    _failures = smoke_test(globals()["iface"])
    print("PASS" if not _failures else "FAIL:\n- " + "\n- ".join(_failures))
