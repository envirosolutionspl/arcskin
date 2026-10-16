# ArcSkin

**ArcSkin gives QGIS an interface inspired by ArcGIS Pro**: a ribbon, Pro-style
panes, view tabs above the map, Pro's map status bar, light flat icons for the whole
of QGIS, Pro's default symbology and colour ramps. Everything is switched on with one
click and fully reverted with the next one.

It is meant for people who know ArcGIS Pro and want to feel at home in QGIS, for
training rooms that teach both, and for organisations moving from Esri to QGIS.

![ArcSkin demo project: ribbon, Contents, view tabs, Catalog and the map status bar](docs/images/overview.png)

> ArcSkin is an independent open source project. It is not affiliated with,
> sponsored or endorsed by Esri. ArcGIS and ArcGIS Pro are trademarks of Esri.

## Features

**Ribbon and title row**

- Ribbon with *Map*, *Insert*, *Analysis*, *View*, *Edit*, *Share*, *Help* and
  *Add-ins* tabs built from QGIS's own tools, with Pro's captions and grouping.
  Plugin toolbars appear on *Add-ins*.
- Blue *Project* button with project commands, the complete QGIS menu and the
  ArcSkin switch.
- Title row with a Quick Access Toolbar, the project name and QGIS's search box
  centred at the top (like Pro's Command Search).
- Basemap gallery: Topographic (OpenTopoMap), OpenStreetMap, Imagery (Sentinel-2
  cloudless), Light and Dark Gray Canvas (CARTO). Only worldwide services.

**Panes**

- *Contents* with a layer search box and filter, Pro's *List By* views (drawing
  order, data source, selection, editing, snapping, labeling) and Pro-style
  raster legends ("Value", *High* / *Low*).
- *Catalog* with *Project*, *Favorites* and *All* tabs, *Geoprocessing* with
  toolboxes and *Find Tools*, *Symbology* with Pro page icons.
- The active pane gets Pro's blue title and frame; *View → Reset Panes* restores
  the mapping, editing or geoprocessing layout.

![Geoprocessing pane](docs/images/geoprocessing.png)

**Map view**

- View tabs above the map. Extra 2D map views are shown in the main map area, one
  at a time: each tab has its own map theme and extent, and the *Contents* pane
  edits the layers of the tab you are on. 3D views and print layouts get tabs too.
- Pro's status bar under the map: editable scale, snapping / grid / constraints,
  coordinates you can type in (decimal degrees, DMS, DDM, MGRS, US National Grid,
  UTM and linear units), the coordinate system, the number of selected features
  (click to zoom to them), clear selection, pause drawing and refresh.
- Selected features in Pro's cyan, on the map and in the attribute table.

![Selected features in cyan, with the count in the status bar](docs/images/selection.png)

![Map view tabs: the "Climate zones" view shown in the main map](docs/images/view_tabs.png)

**Attribute table**

Pro's toolbar (*Field: Add, Calculate | Selection: Select By Attributes, Zoom To,
Switch, Clear, Delete, Copy*) and footer (show all or selected records, first and
last record, "N of M selected", filters, zoom slider, refresh).

![Attribute table with Pro's toolbar and footer](docs/images/attribute_table.png)

**Symbology and styling**

- New layers get Pro's defaults: pastel colours from Pro's "Basic Random" palette,
  0.7 pt grey outlines, 1 pt lines, 4 pt circle markers.
- New labels use Pro's default text symbol (Tahoma 10 pt, black).
- About 100 of Pro's colour ramps (sequential, diverging, analytical such as
  elevation, slope, aspect and precipitation, spectrum and qualitative) are added
  to the QGIS style with the tag *ArcSkin*, for classifying vectors and
  stretching rasters.

![Symbology pane](docs/images/symbology.png)

**Look and feel**

- Light, flat theme with Segoe UI and Pro-style check boxes, radio buttons, lists
  and trees.
- Every QGIS icon redrawn in Pro's light, flat style, plus hand-drawn icons for
  tools and layer types.
- English interface, Polish translation.

![Basemap gallery](docs/images/basemap_gallery.png)

## Requirements

- QGIS 4.x (Qt 6), the main platform
- QGIS 3.40 or newer (Qt 5)

## Installation

1. Download `arcskin-<version>.zip` from the releases.
2. In QGIS open *Plugins → Manage and Install Plugins… → Install from ZIP*,
   choose the file and click *Install Plugin*.

The ArcSkin look is applied as soon as the plugin is installed. Switching takes a
few seconds; a progress box shows the work.

## Turning the look on and off

| What you want | How |
|---|---|
| Switch the look off for now | Blue **Project** button → **ArcSkin look** |
| Switch it on again | **Plugins → ArcSkin → ArcSkin look** (QGIS menu bar) |
| Keep plain QGIS after restarting | **Plugins → Manage and Install Plugins… → Installed**, untick **ArcSkin** |
| Remove the plugin | Same dialog, select **ArcSkin**, **Uninstall Plugin** |

While the plugin is active, ArcSkin is switched on at every QGIS start.

Switching the look off restores QGIS as it was: toolbars, panes and their
positions, the UI theme, icons, the status bar, project styles and the colour ramps
added to the QGIS style. Your projects are not changed by switching.

The first time ArcSkin is switched on, most icons change at once. Layer icons in
*Contents* and *Catalog* follow after a QGIS restart; a message says so.

## Demo project

`demo/arcskin_demo.qgz` is a world map in the Equal Earth projection: countries
coloured by climate zone, country names, disputed borders and a raster of the
distance from the coast, with two extra map views (*Climate zones*, *Distance from
coast*) and a print layout. The data come from Natural Earth (public domain).

## Good to know

- QGIS keeps one layer tree per project, so the drawing order is shared by all view
  tabs; each tab has its own layer visibility (a QGIS map theme) and extent.
- 3D views and print layouts open in their own windows; their tabs bring them to the
  front.
- The icon theme is installed into QGIS's `resources/themes` folder when it is
  writable, because QGIS 4 only reads UI themes from there.

## Development

```
arcskin/                      the plugin (packed into the ZIP)
  plugin.py                   on / off switch, style sheet, progress box
  util.py                     tr(), Pro icons, undo log of all changes (Changes)
  ribbon.py                   ribbon, title row, Project menu
  panes.py                    Contents, Catalog, Geoprocessing, Symbology panes
  contents_views.py           List By views, raster legend, context menu icons
  mapview.py                  view tabs, map status bar
  coords.py                   coordinate formats of the status bar
  dialogs.py                  attribute table, Pro icons in other windows
  symbology.py                default symbols, label font, colour ramps
  icon_theme.py               QGIS icon theme
  basemaps.py                 basemap gallery
  resources/                  icons, style sheets, generated icon theme, colour ramps
  i18n/                       translations (.ts sources)
scripts/
  package.py                  builds dist/arcskin-<version>.zip
  i18n.py                     update .ts files from the code, compile .qm files
  build_icon_theme.py         generates the QGIS icon theme (run with python-qgis)
  build_demo.py               builds the demo project (QGIS Python console)
demo/                         demo project and data
docs/images/                  screenshots
```

Every change ArcSkin makes to QGIS goes through `util.Changes`, which records how to
undo it; switching off replays that log backwards.

For development, link the plugin folder into your QGIS profile (PowerShell as
administrator, or with Windows developer mode on):

```powershell
New-Item -ItemType SymbolicLink `
  -Path "$env:APPDATA\QGIS\QGIS4\profiles\default\python\plugins\arcskin" `
  -Target "$PWD\arcskin"
```

**Translations.** Texts in the code are English and go through `tr("...")`. After
changing them run `python scripts/i18n.py update`, translate the new entries in
`arcskin/i18n/arcskin_pl.ts` (Qt Linguist or a text editor) and the `.qm` files are
compiled when packaging. For a new language, add an empty
`arcskin/i18n/arcskin_<code>.ts` and run `update`.

**Packaging and releases.** `python scripts/package.py` writes
`dist/arcskin-<version>.zip`. For a release, raise `version` in
`arcskin/metadata.txt`, tag the commit `v<version>` and push the tag; GitHub
Actions builds the ZIP and attaches it to the release.

## Credits and licence

ArcSkin is licensed under the GPL-2.0-or-later, see [LICENSE](LICENSE). The icon
theme is derived from QGIS's own icons (GPL-2.0-or-later). Demo data: Natural
Earth (public domain). Basemaps: © OpenStreetMap contributors, OpenTopoMap
(CC-BY-SA), CARTO, Sentinel-2 cloudless by EOX IT Services GmbH (CC BY 4.0).
