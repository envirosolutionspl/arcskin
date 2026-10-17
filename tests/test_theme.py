"""Resources the code refers to: icons, style sheet, generated icon theme."""

import re
import unittest

import build_icon_theme
from arcskin import basemaps, contents_views, dialogs, panes, ribbon
from arcskin.icon_theme import SOURCE as THEME_DIR
from arcskin.plugin import PLUGIN_DIR, THEME, load_qss
from arcskin.util import ICON_DIR

CODE = "\n".join(path.read_text(encoding="utf-8")
                 for path in PLUGIN_DIR.glob("*.py"))
DARK = "#4a4a4a"


def referenced_icons():
    """Names of the Pro icons the specifications and the code use."""
    names = set()
    for _, groups in ribbon.RIBBON:
        for _, items in groups:
            names.update(icon for _, _, icon, _ in items)
    names.update(icon for _, icon in ribbon.PROJECT_MENU)
    names.update(panes.CONTENTS_ICONS)
    names.update(panes.CATALOG_ICONS.values())
    names.update(icon for icon, _, _ in contents_views.VIEWS.values())
    names.update(contents_views.MENU_ICONS.values())
    names.update(icon for _, items in dialogs.TABLE_TOOLBAR
                 for _, icon, _ in items)
    names.update(thumb for _, thumb, _, _ in basemaps.BASEMAPS)
    names.update(re.findall(r'(?:pro_icon|tool_button)\("([\w]+)"', CODE))
    return names


class Icons(unittest.TestCase):

    def test_every_referenced_pro_icon_exists(self):
        missing = sorted(name for name in referenced_icons()
                         if not (ICON_DIR / f"{name}.svg").exists())
        self.assertEqual(missing, [])

    def test_icons_the_theme_builder_maps_exist_on_both_sides(self):
        for key, targets in build_icon_theme.PRO_AS_QGIS.items():
            self.assertTrue((ICON_DIR / f"{key}.svg").exists(), key)
            for target in targets:
                self.assertTrue((THEME_DIR / "icons" / target).exists(),
                                target)

    def test_hand_drawn_icons_have_light_outlines(self):
        for folder in ("pro", "theme_overrides"):
            for path in (ICON_DIR.parent / folder).glob("*.svg"):
                self.assertNotIn(DARK, path.read_text(encoding="utf-8"),
                                 path.name)

    def test_ribbon_specification_is_well_formed(self):
        for tab, groups in ribbon.RIBBON:
            self.assertTrue(tab)
            for group, items in groups:
                self.assertTrue(group)
                for names, size, icon, caption in items:
                    self.assertIn(size, ("L", "S"), names)
                    self.assertTrue(names.split(), names)
                    self.assertTrue(icon and caption, names)


class StyleSheet(unittest.TestCase):

    def setUp(self):
        self.qss = load_qss(THEME)

    def test_all_variables_are_defined(self):
        self.assertEqual(re.findall(r"@[\w-]+", self.qss), [])

    def test_selectors_name_widgets_the_code_creates(self):
        for name in sorted(set(re.findall(r"#(ArcSkin\w+)", self.qss))):
            self.assertIn(f'"{name}"', CODE, f"selector #{name} is stale")

    def test_referenced_files_exist(self):
        for url in re.findall(r"url\(([^)]+)\)", self.qss):
            path = PLUGIN_DIR / url.strip("'\"")
            self.assertTrue(path.exists(), url)


class Soften(unittest.TestCase):
    """Pro-like outlines the theme builder gives icons."""

    def test_filled_shapes_get_a_tinted_thin_outline(self):
        svg = build_icon_theme.soften(
            '<svg><path d="M0 0" fill="#f2b822" stroke="#4a4a4a"/></svg>')
        self.assertNotIn(DARK, svg)
        self.assertIn('stroke-width="1.5"', svg)
        stroke = re.search(r'stroke="(#\w+)"', svg).group(1)
        self.assertNotEqual(stroke, "#f2b822", "darker than the fill")

    def test_white_shapes_get_light_grey(self):
        svg = build_icon_theme.soften(
            '<svg><rect fill="#ffffff" stroke="#4a4a4a"/></svg>')
        self.assertIn('stroke="#8f8f8f"', svg)

    def test_line_art_gets_lighter_grey_and_keeps_its_width(self):
        svg = build_icon_theme.soften(
            '<svg><path d="M0 0" fill="none" stroke="#4a4a4a"/></svg>')
        self.assertIn('stroke="#6b6b6b"', svg)
        self.assertNotIn("stroke-width", svg)

    def test_other_outlines_are_left_alone(self):
        svg = '<svg><path d="M0 0" fill="#ffffff" stroke="#007ac2"/></svg>'
        self.assertEqual(build_icon_theme.soften(svg), svg)
