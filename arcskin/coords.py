"""Coordinate display units of the Pro map footer: format and parse.

Units (as in ArcGIS Pro): Decimal Degrees, Degrees Minutes Seconds,
Degrees Decimal Minutes, MGRS, US National Grid, UTM and linear units of
the map coordinates. Geographic and grid units work on WGS 84 longitude /
latitude; linear units on the map's own (projected) coordinates.
"""

import re

from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY,
    QgsProject, QgsUnitTypes,
)
from qgis.PyQt.QtCore import QLocale

from .util import tr

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")
DU = Qgis.DistanceUnit
ANGULAR = {
    "dd": tr("Decimal Degrees"),
    "dms": tr("Degrees Minutes Seconds"),
    "ddm": tr("Degrees Decimal Minutes"),
    "mgrs": "MGRS",
    "usng": tr("US National Grid"),
    "utm": "UTM",
}
LINEAR = {
    "m": (tr("Meters"), DU.Meters),
    "km": (tr("Kilometers"), DU.Kilometers),
    "ft": (tr("Feet"), DU.Feet),
    "mi": (tr("Miles"), DU.Miles),
    "nmi": (tr("Nautical Miles"), DU.NauticalMiles),
    "yd": (tr("Yards"), DU.Yards),
    "in": (tr("Inches"), DU.Inches),
    "cm": (tr("Centimeters"), DU.Centimeters),
    "mm": (tr("Millimeters"), DU.Millimeters),
}
BANDS = "CDEFGHJKLMNPQRSTUVWX"
COLUMN_SETS = ("ABCDEFGH", "JKLMNPQR", "STUVWXYZ")
ROWS = "ABCDEFGHJKLMNPQRSTUV"


def _number(value, digits):
    return QLocale().toString(value, "f", digits)


def _transform(point, source, target):
    return QgsCoordinateTransform(source, target,
                                  QgsProject.instance()).transform(point)


def _utm_crs(zone, north):
    return QgsCoordinateReferenceSystem(
        f"EPSG:{(32600 if north else 32700) + zone}")


def _utm(lon, lat):
    zone = min(int((lon + 180) / 6) + 1, 60)
    p = _transform(QgsPointXY(lon, lat), WGS84, _utm_crs(zone, lat >= 0))
    return zone, p.x(), p.y()


# --- formatting ---------------------------------------------------------


def _degrees(value, unit, positive, negative):
    hemisphere = positive if value >= 0 else negative
    value = abs(value)
    if unit == "dd":
        return f"{_number(value, 6)}°{hemisphere}"
    degrees = int(value)
    minutes = (value - degrees) * 60
    if unit == "ddm":
        return f"{degrees}°{_number(minutes, 4)}′{hemisphere}"
    seconds = (minutes - int(minutes)) * 60
    return f"{degrees}°{int(minutes):02d}′{_number(seconds, 2)}″{hemisphere}"


def _mgrs(lon, lat, spaced):
    zone, east, north = _utm(lon, lat)
    band = BANDS[min(max(int((lat + 80) / 8), 0), 19)]
    column = COLUMN_SETS[(zone - 1) % 3][int(east // 100000) - 1]
    row = ROWS[(int(north // 100000) + (5 if zone % 2 == 0 else 0)) % 20]
    e, n = int(east % 100000), int(north % 100000)
    if spaced:  # US National Grid notation
        return f"{zone}{band} {column}{row} {e:05d} {n:05d}"
    return f"{zone}{band}{column}{row}{e:05d}{n:05d}"


def format_point(point, unit, map_crs):
    """Text of ``point`` (in ``map_crs``) in display ``unit``."""
    if unit in LINEAR:
        source = map_crs.mapUnits()
        if source == DU.Degrees:
            unit = "dd"  # linear units need projected map coordinates
        else:
            factor = QgsUnitTypes.fromUnitToUnitFactor(source,
                                                       LINEAR[unit][1])
            abbreviation = QgsUnitTypes.toAbbreviatedString(LINEAR[unit][1])
            x, y = point.x() * factor, point.y() * factor
            return (f"{_number(x, 2)} {abbreviation}   "
                    f"{_number(y, 2)} {abbreviation}")
    geo = _transform(point, map_crs, WGS84)
    lon, lat = geo.x(), geo.y()
    if unit in ("mgrs", "usng"):
        if not -80 <= lat <= 84:
            return "—"
        return _mgrs(lon, lat, unit == "usng")
    if unit == "utm":
        zone, east, north = _utm(lon, lat)
        hemisphere = "N" if lat >= 0 else "S"
        return (f"{zone}{hemisphere} {_number(east, 0)}m E "
                f"{_number(north, 0)}m N")
    return (f"{_degrees(lon, unit, 'E', 'W')}  "
            f"{_degrees(lat, unit, 'N', 'S')}")


# --- parsing --------------------------------------------------------------


def _parse_degrees(text):
    """'18°30′15″E', '18 30 15 E', '-18.5' -> decimal degrees."""
    sign = -1 if re.search(r"[WSws]|^\s*-", text) else 1
    numbers = [float(n.replace(",", "."))
               for n in re.findall(r"\d+(?:[.,]\d+)?", text)]
    if not numbers:
        raise ValueError(text)
    value = sum(n / 60 ** i for i, n in enumerate(numbers[:3]))
    return sign * value, re.search(r"[NSns]", text) is not None


def _float(text):
    """Number written in the locale ("500,000.5" in English), else with a
    point or a comma as the decimal separator."""
    value, ok = QLocale().toDouble(text)
    return value if ok else float(text.replace(",", "."))


def _plain(text):
    """``text`` without the locale's digit group separators (500 000)."""
    return re.sub(r"(?<=\d)[\s\u00a0\u202f](?=\d{3}(?!\d))", "", text)


def _split_pair(text):
    """Two coordinates separated by a wide gap or ';', or written with
    hemisphere letters or single spaces."""
    parts = [p for p in re.split(r"\s{2,}|;", text.strip()) if p]
    if len(parts) == 2:
        return parts
    parts = re.findall(r"[-+]?[^NSEWnsew;]+[NSEWnsew]", text)
    if len(parts) == 2:
        return parts
    parts = [p for p in re.split(r"[;\s]+", text.strip()) if p]
    if len(parts) == 2:
        return parts
    if len(parts) % 2 == 0 and len(parts) <= 6:  # e.g. "18 30 15 52 7 0"
        half = len(parts) // 2
        return " ".join(parts[:half]), " ".join(parts[half:])
    raise ValueError(text)


def _parse_mgrs(text):
    m = re.fullmatch(r"(\d{1,2})([C-HJ-NP-X])([A-HJ-NP-Z])([A-HJ-NP-V])"
                     r"(\d*)", re.sub(r"\s+", "", text.upper()))
    if not m or len(m.group(5)) % 2:
        raise ValueError(text)
    zone, band = int(m.group(1)), m.group(2)
    digits = m.group(5)
    half = len(digits) // 2
    scale = 10 ** (5 - half)
    e = int(digits[:half] or 0) * scale
    n = int(digits[half:] or 0) * scale
    east = (COLUMN_SETS[(zone - 1) % 3].index(m.group(3)) + 1) * 100000 + e
    row = (ROWS.index(m.group(4)) - (5 if zone % 2 == 0 else 0)) % 20
    north_hemisphere = band >= "N"
    band_lat = -80 + BANDS.index(band) * 8
    crs = _utm_crs(zone, north_hemisphere)
    band_north = _transform(QgsPointXY(zone * 6 - 183, band_lat), WGS84,
                            crs).y()
    north = row * 100000 + n
    while north < band_north - 100000:
        north += 2000000
    return _transform(QgsPointXY(east, north), crs, WGS84)


def parse_point(text, unit, map_crs):
    """Point in ``map_crs`` from text typed in display ``unit``."""
    if unit in ("mgrs", "usng"):
        return _transform(_parse_mgrs(text), WGS84, map_crs)
    if unit == "utm":
        m = re.fullmatch(r"\s*(\d{1,2})\s*([NSns])[\s,;]+([\d.,]+)\s*m?\s*E?"
                         r"[\s,;]+([\d.,]+)\s*m?\s*N?\s*", _plain(text))
        if not m:
            raise ValueError(text)
        crs = _utm_crs(int(m.group(1)), m.group(2).upper() == "N")
        point = QgsPointXY(_float(m.group(3)), _float(m.group(4)))
        return _transform(point, crs, map_crs)
    first, second = _split_pair(text)
    if unit in LINEAR and map_crs.mapUnits() != DU.Degrees:
        factor = QgsUnitTypes.fromUnitToUnitFactor(LINEAR[unit][1],
                                                   map_crs.mapUnits())
        x, y = (_float(re.sub(r"[^\d.,-]", "", v)) for v in (first, second))
        return QgsPointXY(x * factor, y * factor)
    (a, a_is_lat), (b, b_is_lat) = map(_parse_degrees, (first, second))
    lon, lat = (b, a) if a_is_lat and not b_is_lat else (a, b)
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError(text)
    return _transform(QgsPointXY(lon, lat), WGS84, map_crs)


def unit_name(unit):
    return ANGULAR.get(unit) or LINEAR[unit][0]


def is_valid(unit):
    return unit in ANGULAR or unit in LINEAR
