#!/usr/bin/env python3
"""
Daily briefing from an existing compliance dashboard.

Instead of recomputing anything, this reads a workbook that already has a
"Master_Dashboard" tab (with the RAG count blocks) and turns the headline
numbers into a short, plain-English briefing.

It locates each metric by its LABEL text (e.g. it finds the cell that says
"HGV MOT EXPIRED" and reads the count beside it), so it is robust to the
dashboard moving up/down and it never needs to read the personal-data action
lists further down the sheet.

Usage:
    python dashboard_briefing.py --file "C:\\...\\Transport Compliance Workbook.xlsm"
    python dashboard_briefing.py --file "...xlsm" --out "C:\\...\\Reports"
    python dashboard_briefing.py --file "...xlsm" --config dashboard.yaml

Run it once and check the "matched / not found" report it prints — if any label
wasn't found, copy the exact wording from your dashboard into the config.

Decision-support only — does not replace the qualified Transport Manager (CPC)
named on the Operator's Licence. Verify against source records.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

try:
    import openpyxl
except ImportError:
    sys.exit("Missing dependency 'openpyxl'. Install with: pip install -r requirements.txt")


# ---------------------------------------------------------------------------
# Defaults — edit these (or a config file) to match your dashboard wording.
# Each metric: the label text to find, a short name for the briefing, and the
# group it belongs to ("red" = expired/overdue, "amber" = due soon).
# Label matching is case-insensitive and ignores extra spacing/punctuation.
# ---------------------------------------------------------------------------

DEFAULT_METRICS = [
    # --- expired / overdue (RED) ---
    {"label": "Licences EXPIRED",            "name": "Driver licences expired",        "group": "red"},
    {"label": "DQC EXPIRED",                 "name": "Driver CPC (DQC) expired",       "group": "red"},
    {"label": "HGV MOT EXPIRED",             "name": "HGV MOT expired",                "group": "red"},
    {"label": "HGV Tax EXPIRED",             "name": "HGV road tax expired",           "group": "red"},
    {"label": "Trailer MOT EXPIRED",         "name": "Trailer MOT expired",            "group": "red"},
    {"label": "Health Docs OVERDUE",         "name": "Driver health docs overdue",     "group": "red"},
    {"label": "Eyesight Check OVERDUE",      "name": "Eyesight checks overdue",        "group": "red"},
    {"label": "D&A Check OVERDUE",           "name": "Drug & alcohol checks overdue",  "group": "red"},
    {"label": "Tacho Direct Download",       "name": "Tacho downloads missing/expired","group": "red"},
    # --- due soon (AMBER) ---
    {"label": "Licences due within 30 days", "name": "Driver licences due (30d)",      "group": "amber"},
    {"label": "DQC due within 30 days",      "name": "Driver CPC due (30d)",           "group": "amber"},
    {"label": "DQC due within 90 days",      "name": "Driver CPC due (90d)",           "group": "amber"},
    {"label": "Driver Cards due within 30 days", "name": "Driver tacho cards due (30d)","group": "amber"},
    {"label": "HGV MOT due within 30 days",  "name": "HGV MOT due (30d)",              "group": "amber"},
    {"label": "HGV Tax due within 30 days",  "name": "HGV road tax due (30d)",         "group": "amber"},
    {"label": "Company Cars MOT due 30 days","name": "Company car MOT due (30d)",      "group": "amber"},
    {"label": "Company Cars Tax due 30 days","name": "Company car tax due (30d)",      "group": "amber"},
    {"label": "Trailer MOT due within 30 days","name": "Trailer MOT due (30d)",        "group": "amber"},
]

# Single-value header fields to read (label -> friendly name).
DEFAULT_HEADER_FIELDS = [
    {"label": "Operator Licence", "name": "O-Licence"},
    {"label": "Last Updated",     "name": "Dashboard last updated"},
]

# A line like "16 active compliance issues across 14 categories" — matched by regex.
ISSUES_BANNER_RE = re.compile(r"\d+\s+active\s+compliance\s+issues", re.IGNORECASE)


@dataclass
class DashboardConfig:
    file: str = ""
    out: Optional[str] = None
    sheet: str = "Master_Dashboard"
    scan_cols: int = 12          # how many columns right of a label to search for its value
    metrics: list = field(default_factory=lambda: [dict(m) for m in DEFAULT_METRICS])
    header_fields: list = field(default_factory=lambda: [dict(m) for m in DEFAULT_HEADER_FIELDS])


def load_config(path: str) -> DashboardConfig:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.lower().endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.exit("Config is YAML but PyYAML isn't installed (pip install pyyaml).")
        data = yaml.safe_load(text) or {}
    else:
        import json
        data = json.loads(text)
    cfg = DashboardConfig()
    for k, v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg


# ---------------------------------------------------------------------------
# Reading the dashboard
# ---------------------------------------------------------------------------

def _norm(s) -> str:
    """Normalise label text for forgiving comparison."""
    if s is None:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def build_grid(ws, max_scan_rows: int = 400) -> list[list]:
    """Return a 2D list of cell values for the top portion of the sheet."""
    grid = []
    for r, row in enumerate(ws.iter_rows(values_only=True)):
        grid.append(list(row))
        if r + 1 >= max_scan_rows:
            break
    return grid


def find_label(grid, label) -> Optional[tuple[int, int]]:
    target = _norm(label)
    if not target:
        return None
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            cell = _norm(val)
            if not cell:
                continue
            if cell == target or target in cell:
                return (r, c)
    return None


def value_right_of(grid, r, c, scan_cols, want_number=True):
    """Return the first meaningful value to the right of (r, c)."""
    row = grid[r]
    for cc in range(c + 1, min(c + 1 + scan_cols, len(row))):
        v = row[cc]
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if want_number and not _is_number(v):
            # allow numeric-looking strings
            try:
                return int(float(str(v).strip()))
            except ValueError:
                continue
        return v
    return None


def find_banner(grid) -> Optional[str]:
    for row in grid:
        for val in row:
            if isinstance(val, str) and ISSUES_BANNER_RE.search(val):
                return val.strip()
    return None


@dataclass
class DashReading:
    header: dict
    red: list          # list of (name, count) with count > 0
    amber: list
    clear: list        # names with count == 0
    not_found: list    # labels we couldn't locate
    banner: Optional[str]


def read_dashboard(cfg: DashboardConfig) -> DashReading:
    wb = openpyxl.load_workbook(cfg.file, data_only=True, read_only=True)
    if cfg.sheet not in wb.sheetnames:
        wb.close()
        raise SystemExit(
            f"Sheet '{cfg.sheet}' not found. Tabs in this file: {', '.join(wb.sheetnames)}\n"
            f"Set the right tab name with --sheet or in the config."
        )
    ws = wb[cfg.sheet]
    grid = build_grid(ws)
    wb.close()

    header = {}
    for f in cfg.header_fields:
        pos = find_label(grid, f["label"])
        if pos:
            val = value_right_of(grid, pos[0], pos[1], cfg.scan_cols, want_number=False)
            if val is not None:
                if isinstance(val, dt.datetime):
                    val = val.strftime("%d/%m/%Y %H:%M")
                header[f["name"]] = val

    red, amber, clear, not_found = [], [], [], []
    for m in cfg.metrics:
        pos = find_label(grid, m["label"])
        if not pos:
            not_found.append(m["label"])
            continue
        count = value_right_of(grid, pos[0], pos[1], cfg.scan_cols, want_number=True)
        if not _is_number(count):
            not_found.append(m["label"])
            continue
        count = int(count)
        if count <= 0:
            clear.append(m["name"])
        elif m["group"] == "red":
            red.append((m["name"], count))
        else:
            amber.append((m["name"], count))

    return DashReading(header, red, amber, clear, not_found, find_banner(grid))


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------

def format_briefing(reading: DashReading, today: dt.date) -> str:
    L = []
    L.append(f"# Transport Compliance Briefing — {today.strftime('%A %d %B %Y')}")
    src = []
    if "O-Licence" in reading.header:
        src.append(f"O-Licence {reading.header['O-Licence']}")
    if "Dashboard last updated" in reading.header:
        src.append(f"dashboard updated {reading.header['Dashboard last updated']}")
    if src:
        L.append("_Source: Master_Dashboard — " + " · ".join(str(s) for s in src) + "_")
    L.append("")

    total_red = sum(c for _, c in reading.red)
    total_amber = sum(c for _, c in reading.amber)

    if reading.banner:
        L.append(f"**{reading.banner}**")
    L.append(f"**Headline:** {total_red} expired/overdue · {total_amber} due soon.")
    L.append("")

    if reading.red:
        L.append("## 🔴 Expired / overdue — act now")
        for name, c in sorted(reading.red, key=lambda x: -x[1]):
            L.append(f"- **{name}: {c}**")
        L.append("")

    if reading.amber:
        L.append("## 🟠 Due soon")
        for name, c in sorted(reading.amber, key=lambda x: -x[1]):
            L.append(f"- {name}: {c}")
        L.append("")

    if not reading.red and not reading.amber:
        L.append("✅ **All clear** — no expired/overdue or due-soon items on the dashboard.")
        L.append("")

    if reading.not_found:
        L.append("> ⚠️ Couldn't find these labels on the dashboard (check the wording "
                 "in the config): " + "; ".join(reading.not_found))
        L.append("")

    L.append("_Decision-support only — does not replace the qualified Transport Manager "
             "named on the O-licence. Verify against source records._")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Daily briefing from a compliance dashboard")
    p.add_argument("--file", help="Path to the compliance workbook (.xlsm/.xlsx)")
    p.add_argument("--out", help="Folder to write the briefing into (optional)")
    p.add_argument("--sheet", help="Dashboard tab name (default: Master_Dashboard)")
    p.add_argument("--config", help="Path to a .yaml/.json config")
    args = p.parse_args(argv)

    cfg = load_config(args.config) if args.config else DashboardConfig()
    if args.file:
        cfg.file = args.file
    if args.out:
        cfg.out = args.out
    if args.sheet:
        cfg.sheet = args.sheet

    if not cfg.file or not os.path.isfile(cfg.file):
        print(f"ERROR: workbook not found: {cfg.file!r}")
        print('Pass --file "C:\\path\\to\\Transport Compliance Workbook.xlsm"')
        return 2

    today = dt.date.today()
    reading = read_dashboard(cfg)
    text = format_briefing(reading, today)

    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)
    matched = len(reading.red) + len(reading.amber) + len(reading.clear)
    print(f"\nMetrics matched: {matched}  |  not found: {len(reading.not_found)}")

    if cfg.out:
        os.makedirs(cfg.out, exist_ok=True)
        path = os.path.join(cfg.out, f"compliance_briefing_{today.strftime('%Y-%m-%d')}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        latest = os.path.join(cfg.out, "compliance_briefing_latest.md")
        with open(latest, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"Briefing written: {path}")
        print(f"Latest copy:      {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
