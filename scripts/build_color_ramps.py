"""Generate cyanskin/resources/color_ramps.json: the bundled colour ramps.

Usage:

    python scripts/build_color_ramps.py

Each ramp is a few anchor colours chosen for the purpose (relief, depth,
temperature, ...) after common cartographic conventions; QGIS interpolates
between them.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "cyanskin" / "resources" \
    / "color_ramps.json"


def even(*colours):
    """Stops spread evenly over 0..1."""
    last = len(colours) - 1
    return [[round(i / last, 4), c] for i, c in enumerate(colours)]


# (name, group, stops)
RAMPS = [
    ("Terrain", "Thematic", [
        [0.0, "#3b8a6c"], [0.2, "#6fae5a"], [0.4, "#c9d88a"],
        [0.55, "#efe1a0"], [0.7, "#c99a62"], [0.85, "#9c7462"],
        [1.0, "#f8eef1"]]),
    ("Terrain (land only)", "Thematic", even(
        "#3a7d44", "#a7c957", "#f2e8a0", "#c08a4f", "#8c5a3c", "#f5f5f5")),
    ("Depth", "Thematic", [
        [0.0, "#e6f4fa"], [0.35, "#8cc6e3"], [0.7, "#2e7bb5"],
        [1.0, "#0b2e59"]]),
    ("Temperature", "Thematic", even(
        "#2b4f9e", "#77b5dd", "#f7f3d0", "#f4a259", "#b2272c")),
    ("Precipitation", "Thematic", [
        [0.0, "#f7fbe9"], [0.3, "#b8e2b0"], [0.6, "#4ba6c4"],
        [1.0, "#1d3f8f"]]),
    ("Slope", "Thematic", [
        [0.0, "#e8f3dc"], [0.4, "#f4e07a"], [0.7, "#ee8f3c"],
        [1.0, "#b3212d"]]),
    # Cyclic: north and back to north have the same colour.
    ("Aspect", "Thematic", even(
        "#d73b3b", "#e8c33c", "#4fbf9b", "#4a6fd1", "#d73b3b")),
    ("Greys", "Sequential", even("#f4f4f4", "#9a9a9a", "#2b2b2b")),
    ("Blues", "Sequential", even("#eef5fb", "#6aa6d6", "#0d3d74")),
    ("Greens", "Sequential", even("#eff7e8", "#7fbf6a", "#1f5e2a")),
    ("Reds", "Sequential", even("#fdeeea", "#e8775f", "#8a1717")),
    ("Purples", "Sequential", even("#f3eef8", "#a48bcf", "#4b2a7a")),
    ("Red-Blue", "Diverging", even("#b2272c", "#f6f4f0", "#2a5fa8")),
    ("Brown-Green", "Diverging", even("#8a5a2b", "#f5f1e4", "#2f7a5a")),
]


def main():
    ramps = [{"name": name, "group": group, "stops": stops}
             for name, group, stops in RAMPS]
    OUT.write_text(json.dumps(ramps, indent=1) + "\n", encoding="utf-8")
    print(f"{len(ramps)} ramps -> {OUT}")


if __name__ == "__main__":
    main()
