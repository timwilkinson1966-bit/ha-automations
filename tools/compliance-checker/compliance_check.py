#!/usr/bin/env python3
"""
Transport compliance checker.

Scans a folder of Excel workbooks (.xlsx / .xlsm), finds compliance due-dates
(MOT, road tax, PMI/safety inspection, tachograph download & calibration,
driver licence / CPC, insurance, LOLER, O-licence review, etc.) and writes a
dated, colour-coded RAG report:

    RED    = overdue
    AMBER  = due soon (within --warning-days)
    GREEN  = ok

It works out of the box by auto-discovering date columns from their headers.
For precise control you can add rules in a config file (see config.example.yaml).

This is a decision-support tool for a Transport Manager. It does NOT replace the
legally required, qualified CPC holder named on the Operator's Licence.

Usage (auto-discovery):
    python compliance_check.py --root "C:\\Compliance" --out "C:\\Compliance\\Reports"

Usage (with config):
    python compliance_check.py --config config.yaml
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, Optional

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit(
        "Missing dependency 'openpyxl'.\n"
        "Install it with:  pip install -r requirements.txt"
    )

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Header keywords that suggest a column holds a compliance due/expiry date.
# Matching is case-insensitive and substring-based.
DEFAULT_KEYWORDS = [
    "due", "expiry", "expire", "expires", "exp date", "valid to", "valid until",
    "renew", "renewal", "review", "next", "mot", "road tax", "tax due", "ved",
    "pmi", "inspection", "safety insp", "service", "maintenance",
    "tacho", "tachograph", "calibration", "calib", "download",
    "licence", "license", "dvla", "cpc", "driver card",
    "insurance", "loler", "ler", "o-licence", "o licence", "operator licence",
    "first aid", "fire", "gas", "psv", "annual test", "atf", "plating",
]

# Identifier columns: used to label each flagged row (vehicle reg, driver name...).
DEFAULT_ID_KEYWORDS = [
    "reg", "registration", "vrm", "vehicle", "fleet", "trailer",
    "driver", "name", "employee", "asset", "ref", "id",
]

# File patterns to ignore while scanning.
DEFAULT_EXCLUDE = ["~$*", "*compliance_report_*.xlsx", "*Compliance Report*.xlsx"]

EXCEL_EXTS = (".xlsx", ".xlsm")

# Plausible range for raw Excel date serials (≈1982-01-01 .. 2061-...).
EXCEL_SERIAL_MIN = 30000
EXCEL_SERIAL_MAX = 60000
EXCEL_EPOCH = dt.datetime(1899, 12, 30)  # Excel's day 0 (with the 1900 leap bug)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """An explicit, precise check for a known file/sheet/column."""
    file_glob: str = "*"
    sheet: Optional[str] = None          # None = any sheet
    column: str = ""                     # header text to match (case-insensitive)
    label: Optional[str] = None          # friendly name for the report
    warning_days: Optional[int] = None   # override global warning threshold


@dataclass
class Config:
    root: str = "."
    out: str = "."
    warning_days: int = 30               # amber if due within this many days
    critical_days: int = 7               # (reported, used for sort emphasis)
    keywords: list[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    id_keywords: list[str] = field(default_factory=lambda: list(DEFAULT_ID_KEYWORDS))
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    header_scan_rows: int = 8            # rows to inspect when locating the header
    auto_discover: bool = True           # scan by keyword in addition to rules
    rules: list[Rule] = field(default_factory=list)


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    data = _parse_config_text(text, path)
    rules = [Rule(**r) for r in data.pop("rules", [])]
    cfg = Config(**{k: v for k, v in data.items() if k in Config.__annotations__})
    cfg.rules = rules
    return cfg


def _parse_config_text(text: str, path: str) -> dict:
    if path.lower().endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.exit(
                "Config is YAML but PyYAML is not installed.\n"
                "Install it (pip install pyyaml) or use a .json config."
            )
        return yaml.safe_load(text) or {}
    import json
    return json.loads(text)


# ---------------------------------------------------------------------------
# Date handling (UK day-first)
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%y", "%d-%m-%y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d %b %Y", "%d %B %Y",
]


def coerce_date(value) -> Optional[dt.date]:
    """Best-effort conversion of a cell value to a date (day-first for text)."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, (int, float)):
        # Possibly a raw Excel date serial.
        if EXCEL_SERIAL_MIN <= value <= EXCEL_SERIAL_MAX:
            return (EXCEL_EPOCH + dt.timedelta(days=int(value))).date()
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        for fmt in _DATE_FORMATS:
            try:
                return dt.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Finding & reading workbooks
# ---------------------------------------------------------------------------

def iter_workbooks(cfg: Config) -> Iterable[str]:
    for dirpath, _dirs, files in os.walk(cfg.root):
        for name in files:
            if not name.lower().endswith(EXCEL_EXTS):
                continue
            if any(fnmatch.fnmatch(name, pat) for pat in cfg.exclude):
                continue
            yield os.path.join(dirpath, name)


def find_header_row(ws, scan_rows: int) -> int:
    """Return the 1-based row index that looks most like a header row."""
    best_row, best_score = 1, -1
    for r in range(1, min(scan_rows, ws.max_row or 1) + 1):
        score = 0
        for cell in ws[r]:
            if isinstance(cell.value, str) and cell.value.strip():
                score += 1
        if score > best_score:
            best_row, best_score = r, score
    return best_row


def match_keyword(header: str, keywords: list[str]) -> bool:
    h = header.lower()
    return any(k in h for k in keywords)


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    sheet: str
    identifier: str
    item: str
    due: dt.date
    days: int

    @property
    def status(self) -> str:
        if self.days < 0:
            return "OVERDUE"
        return "DUE SOON"


def check_workbook(path: str, cfg: Config, today: dt.date) -> list[Finding]:
    findings: list[Finding] = []
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001 - keep scanning other files
        print(f"  ! could not open {os.path.basename(path)}: {exc}")
        return findings

    rel = os.path.basename(path)
    for ws in wb.worksheets:
        try:
            findings.extend(_check_sheet(ws, rel, path, cfg, today))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! error in {rel}[{ws.title}]: {exc}")
    wb.close()
    return findings


def _check_sheet(ws, rel: str, path: str, cfg: Config, today: dt.date) -> list[Finding]:
    findings: list[Finding] = []
    if ws.max_row is None or ws.max_row < 2:
        return findings

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return findings

    header_idx = find_header_row(ws, cfg.header_scan_rows) - 1
    if header_idx >= len(rows):
        header_idx = 0
    headers = [str(c).strip() if c is not None else "" for c in rows[header_idx]]

    # Which columns are date columns to check, and what to call them.
    date_cols: dict[int, tuple[str, int]] = {}  # col_idx -> (label, warning_days)

    # 1) explicit rules
    for rule in cfg.rules:
        if not fnmatch.fnmatch(rel, rule.file_glob):
            continue
        if rule.sheet and rule.sheet.lower() != ws.title.lower():
            continue
        for i, h in enumerate(headers):
            if rule.column and rule.column.lower() in h.lower():
                date_cols[i] = (
                    rule.label or h or f"col{i+1}",
                    rule.warning_days if rule.warning_days is not None else cfg.warning_days,
                )

    # 2) auto-discovery by keyword
    if cfg.auto_discover:
        for i, h in enumerate(headers):
            if i in date_cols or not h:
                continue
            if match_keyword(h, cfg.keywords):
                date_cols[i] = (h, cfg.warning_days)

    if not date_cols:
        return findings

    # Identifier column (vehicle reg / driver name / ref).
    id_col = None
    for i, h in enumerate(headers):
        if h and match_keyword(h, cfg.id_keywords):
            id_col = i
            break
    if id_col is None:
        id_col = 0  # fall back to first column

    for row in rows[header_idx + 1:]:
        if row is None:
            continue
        ident = ""
        if id_col < len(row) and row[id_col] is not None:
            ident = str(row[id_col]).strip()
        for col_idx, (label, warn) in date_cols.items():
            if col_idx >= len(row):
                continue
            due = coerce_date(row[col_idx])
            if due is None:
                continue
            days = (due - today).days
            if days <= warn:  # overdue or within warning window
                findings.append(
                    Finding(
                        file=rel,
                        sheet=ws.title,
                        identifier=ident or "(no id)",
                        item=label,
                        due=due,
                        days=days,
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

RED = PatternFill("solid", fgColor="FFC7CE")
AMBER = PatternFill("solid", fgColor="FFEB9C")
GREEN = PatternFill("solid", fgColor="C6EFCE")
HEADER_FILL = PatternFill("solid", fgColor="305496")


def write_report(findings: list[Finding], cfg: Config, today: dt.date) -> str:
    os.makedirs(cfg.out, exist_ok=True)
    stamp = today.strftime("%Y-%m-%d")
    out_path = os.path.join(cfg.out, f"compliance_report_{stamp}.xlsx")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compliance"

    overdue = [f for f in findings if f.days < 0]
    critical = [f for f in findings if 0 <= f.days <= cfg.critical_days]
    soon = [f for f in findings if cfg.critical_days < f.days <= cfg.warning_days]

    ws["A1"] = "Transport Compliance Report"
    ws["A1"].font = Font(size=14, bold=True)
    ws["A2"] = f"Generated: {today.strftime('%d/%m/%Y')}"
    ws["A3"] = (
        f"OVERDUE: {len(overdue)}    "
        f"Critical (≤{cfg.critical_days}d): {len(critical)}    "
        f"Due soon (≤{cfg.warning_days}d): {len(soon)}"
    )
    ws["A3"].font = Font(bold=True)
    ws["A4"] = (
        "Decision-support only — does not replace the qualified Transport "
        "Manager named on the O-licence."
    )
    ws["A4"].font = Font(italic=True, size=9, color="808080")

    header_row = 6
    cols = ["Status", "Days", "Due date", "Item", "Identifier", "Sheet", "File"]
    for c, title in enumerate(cols, start=1):
        cell = ws.cell(row=header_row, column=c, value=title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL

    findings_sorted = sorted(findings, key=lambda f: f.days)
    r = header_row + 1
    for f in findings_sorted:
        fill = RED if f.days < 0 else (AMBER if f.days <= cfg.critical_days else None)
        status = "OVERDUE" if f.days < 0 else "DUE SOON"
        values = [
            status,
            f.days,
            f.due.strftime("%d/%m/%Y"),
            f.item,
            f.identifier,
            f.sheet,
            f.file,
        ]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            if fill is not None:
                cell.fill = fill
        r += 1

    if not findings_sorted:
        cell = ws.cell(row=r, column=1, value="No items overdue or due soon. ✅")
        cell.fill = GREEN
        cell.font = Font(bold=True)

    # Column widths
    widths = [11, 7, 12, 28, 22, 18, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(cols))}{max(r-1, header_row)}"

    wb.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_config(args) -> Config:
    if args.config:
        cfg = load_config(args.config)
    else:
        cfg = Config()
    # CLI overrides
    if args.root:
        cfg.root = args.root
    if args.out:
        cfg.out = args.out
    if args.warning_days is not None:
        cfg.warning_days = args.warning_days
    if args.critical_days is not None:
        cfg.critical_days = args.critical_days
    return cfg


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Transport compliance checker")
    p.add_argument("--root", help="Folder to scan for .xlsx/.xlsm files")
    p.add_argument("--out", help="Folder to write the report into")
    p.add_argument("--config", help="Path to a .yaml/.json config file")
    p.add_argument("--warning-days", type=int, default=None,
                   help="Amber threshold: flag items due within this many days (default 30)")
    p.add_argument("--critical-days", type=int, default=None,
                   help="Red-emphasis threshold in days (default 7)")
    args = p.parse_args(argv)

    cfg = build_config(args)

    if not cfg.root or not os.path.isdir(cfg.root):
        print(f"ERROR: root folder not found: {cfg.root!r}")
        print("Pass --root \"C:\\path\\to\\Compliance\" (or set it in a config).")
        return 2

    today = dt.date.today()
    print(f"Scanning: {cfg.root}")
    print(f"Today: {today.strftime('%d/%m/%Y')}  warning<= {cfg.warning_days}d  critical<= {cfg.critical_days}d")

    all_findings: list[Finding] = []
    n_files = 0
    for path in iter_workbooks(cfg):
        n_files += 1
        print(f"  reading {os.path.relpath(path, cfg.root)}")
        all_findings.extend(check_workbook(path, cfg, today))

    print(f"Scanned {n_files} workbook(s); {len(all_findings)} item(s) flagged.")
    out_path = write_report(all_findings, cfg, today)
    print(f"Report written: {out_path}")

    overdue = sum(1 for f in all_findings if f.days < 0)
    if overdue:
        print(f"WARNING: {overdue} item(s) OVERDUE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
