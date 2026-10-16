"""Translations: extract tr("...") strings to .ts and compile .ts to .qm.

Usage:
    python scripts/i18n.py update    # refresh arcskin/i18n/*.ts from code
    python scripts/i18n.py compile   # arcskin/i18n/*.ts -> *.qm

The .ts files are standard Qt Linguist files (also usable with Transifex).
Compilation is done here, so no Qt tools (lrelease) are needed. To add a
language, create an empty ``arcskin/i18n/arcskin_<code>.ts`` and run update.
"""

import ast
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "arcskin"
I18N = PLUGIN / "i18n"
CONTEXT = "ArcSkin"
QM_MAGIC = bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd")


def source_strings():
    """All literal arguments of tr(...) calls, in order of appearance."""
    found = []
    for path in sorted(PLUGIN.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "tr"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value not in found):
                found.append(node.args[0].value)
    return found


def read_ts(path):
    """Return {source: translation} from a .ts file ('' if untranslated)."""
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {}
    root = ET.parse(path).getroot()
    return {m.findtext("source"): m.findtext("translation") or ""
            for m in root.iter("message")}


def write_ts(path, language, translations, sources):
    ts = ET.Element("TS", version="2.1", language=language)
    context = ET.SubElement(ts, "context")
    ET.SubElement(context, "name").text = CONTEXT
    for source in sources:
        message = ET.SubElement(context, "message")
        ET.SubElement(message, "source").text = source
        text = translations.get(source, "")
        translation = ET.SubElement(message, "translation")
        translation.text = text
        if not text:
            translation.set("type", "unfinished")
    ET.indent(ts)
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n'
                    '<!DOCTYPE TS>\n' + ET.tostring(ts, encoding="unicode")
                    + "\n", encoding="utf-8")


def elf_hash(data):
    """Qt's hash of the source text used to look messages up in a .qm."""
    h = 0
    for byte in data:
        h = ((h << 4) + byte) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h or 1


def write_qm(path, translations):
    """Write a minimal .qm: a hash table plus messages with context."""
    messages, hashes = bytearray(), []
    for source, text in translations.items():
        if not text:
            continue
        src, ctx = source.encode("utf-8"), CONTEXT.encode("utf-8")
        hashes.append((elf_hash(src), len(messages)))
        target = text.encode("utf-16-be")
        messages += b"\x03" + struct.pack(">I", len(target)) + target
        messages += b"\x06" + struct.pack(">I", len(src)) + src
        messages += b"\x07" + struct.pack(">I", len(ctx)) + ctx
        messages += b"\x01"
    table = b"".join(struct.pack(">II", h, o) for h, o in sorted(hashes))
    path.write_bytes(QM_MAGIC
                     + b"\x42" + struct.pack(">I", len(table)) + table
                     + b"\x69" + struct.pack(">I", len(messages)) + messages)


def main(command):
    if command == "update":
        sources = source_strings()
        for path in sorted(I18N.glob("arcskin_*.ts")):
            language = path.stem.split("_", 1)[1]
            write_ts(path, language, read_ts(path), sources)
            done = sum(1 for t in read_ts(path).values() if t)
            print(f"{path.name}: {done}/{len(sources)} translated")
    elif command == "compile":
        for path in sorted(I18N.glob("arcskin_*.ts")):
            write_qm(path.with_suffix(".qm"), read_ts(path))
            print(path.with_suffix(".qm").name)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
