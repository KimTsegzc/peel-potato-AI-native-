from __future__ import annotations

import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from .data import EXPECTED_HEADERS, TABLE_PATH


_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _cell_position(cell_ref: str) -> tuple[int, int]:
    letters = "".join(char for char in cell_ref if char.isalpha())
    row_number = int("".join(char for char in cell_ref if char.isdigit()) or "0")
    col_number = 0
    for char in letters:
        col_number = col_number * 26 + (ord(char.upper()) - ord("A") + 1)
    return row_number, col_number


def _read_shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", _NS):
        values.append("".join(node.text or "" for node in item.iterfind(".//main:t", _NS)))
    return values


def _resolve_first_sheet(zf: ZipFile) -> str:
    workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall("pkgrel:Relationship", _NS)
    }
    first_sheet = workbook_root.find("main:sheets/main:sheet", _NS)
    if first_sheet is None:
        raise ValueError("Workbook has no sheets")
    rel_id = first_sheet.attrib.get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    )
    if not rel_id or rel_id not in rel_map:
        raise ValueError("Cannot resolve first worksheet relationship")
    target = rel_map[rel_id]
    return target if target.startswith("xl/") else f"xl/{target}"


def convert_xlsx_to_csv(xlsx_path: Path, csv_path: Path = TABLE_PATH) -> Path:
    rows: list[list[str]] = []
    max_col = 0
    with ZipFile(xlsx_path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet_path = _resolve_first_sheet(zf)
        root = ET.fromstring(zf.read(sheet_path))
        for row in root.findall(".//main:sheetData/main:row", _NS):
            values_by_col: dict[int, str] = {}
            for cell in row.findall("main:c", _NS):
                _, col_idx = _cell_position(cell.attrib.get("r", ""))
                max_col = max(max_col, col_idx)
                cell_type = cell.attrib.get("t")
                value = ""
                if cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.findall(".//main:t", _NS))
                else:
                    raw_value = (cell.findtext("main:v", default="", namespaces=_NS) or "").strip()
                    if cell_type == "s" and raw_value:
                        value = shared_strings[int(raw_value)]
                    else:
                        value = raw_value
                values_by_col[col_idx] = value.strip()
            if values_by_col:
                rows.append([values_by_col.get(index, "") for index in range(1, max_col + 1)])

    if not rows:
        raise ValueError(f"No rows found in workbook: {xlsx_path}")

    header = tuple((rows[0][: len(EXPECTED_HEADERS)] + [""] * len(EXPECTED_HEADERS))[: len(EXPECTED_HEADERS)])
    if header != EXPECTED_HEADERS:
        raise ValueError(f"Unexpected workbook headers: {header!r}; expected {EXPECTED_HEADERS!r}")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
    return csv_path


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    repo_root = Path(__file__).resolve().parents[4]
    xlsx_path = Path(args[0]) if args else repo_root / "分行职能表（脱敏）.xlsx"
    output_path = Path(args[1]) if len(args) > 1 else TABLE_PATH
    resolved = convert_xlsx_to_csv(xlsx_path=xlsx_path, csv_path=output_path)
    print(f"Converted {xlsx_path} -> {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from .data import EXPECTED_HEADERS, TABLE_PATH


_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _cell_position(cell_ref: str) -> tuple[int, int]:
    letters = "".join(char for char in cell_ref if char.isalpha())
    row_number = int("".join(char for char in cell_ref if char.isdigit()) or "0")
    col_number = 0
    for char in letters:
        col_number = col_number * 26 + (ord(char.upper()) - ord("A") + 1)
    return row_number, col_number


def _read_shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", _NS):
        values.append("".join(node.text or "" for node in item.iterfind(".//main:t", _NS)))
    return values


def _resolve_first_sheet(zf: ZipFile) -> str:
    workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall("pkgrel:Relationship", _NS)
    }
    first_sheet = workbook_root.find("main:sheets/main:sheet", _NS)
    if first_sheet is None:
        raise ValueError("Workbook has no sheets")
    rel_id = first_sheet.attrib.get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    )
    if not rel_id or rel_id not in rel_map:
        raise ValueError("Cannot resolve first worksheet relationship")
    target = rel_map[rel_id]
    return target if target.startswith("xl/") else f"xl/{target}"


def convert_xlsx_to_csv(xlsx_path: Path, csv_path: Path = TABLE_PATH) -> Path:
    rows: list[list[str]] = []
    max_col = 0
    with ZipFile(xlsx_path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet_path = _resolve_first_sheet(zf)
        root = ET.fromstring(zf.read(sheet_path))
        for row in root.findall(".//main:sheetData/main:row", _NS):
            values_by_col: dict[int, str] = {}
            for cell in row.findall("main:c", _NS):
                _, col_idx = _cell_position(cell.attrib.get("r", ""))
                max_col = max(max_col, col_idx)
                cell_type = cell.attrib.get("t")
                value = ""
                if cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.findall(".//main:t", _NS))
                else:
                    raw_value = (cell.findtext("main:v", default="", namespaces=_NS) or "").strip()
                    if cell_type == "s" and raw_value:
                        value = shared_strings[int(raw_value)]
                    else:
                        value = raw_value
                values_by_col[col_idx] = value.strip()
            if values_by_col:
                rows.append([values_by_col.get(index, "") for index in range(1, max_col + 1)])

    if not rows:
        raise ValueError(f"No rows found in workbook: {xlsx_path}")

    header = tuple((rows[0][: len(EXPECTED_HEADERS)] + [""] * len(EXPECTED_HEADERS))[: len(EXPECTED_HEADERS)])
    if header != EXPECTED_HEADERS:
        raise ValueError(f"Unexpected workbook headers: {header!r}; expected {EXPECTED_HEADERS!r}")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
    return csv_path


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    repo_root = Path(__file__).resolve().parents[4]
    xlsx_path = Path(args[0]) if args else repo_root / "分行职能表（脱敏）.xlsx"
    output_path = Path(args[1]) if len(args) > 1 else TABLE_PATH
    resolved = convert_xlsx_to_csv(xlsx_path=xlsx_path, csv_path=output_path)
    print(f"Converted {xlsx_path} -> {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())