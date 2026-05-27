#!/usr/bin/env python3
"""Build HA devices + entities Excel spreadsheet from JSON files."""

import json
import re
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# All device JSON blobs collected from the HA API
TOOL_RESULT_PATHS = [
    # offset 50 and 200 were saved to persisted files; the rest were in-memory
]

# Parse all device data from the tool results directory
TOOL_RESULTS_DIR = Path("/root/.claude/projects/-home-user-ha-automations/904137f4-e6db-4712-83df-3c6fe90236f5/tool-results")

def load_all_devices():
    devices = []
    # Load from the persisted tool result files (toolu_*.txt) and inline JSON files
    patterns = ["toolu_*.txt", "inline_offset_*.json"]
    seen_offsets = set()
    all_files = []
    for pattern in patterns:
        all_files.extend(TOOL_RESULTS_DIR.glob(pattern))
    # Sort by offset so duplicates are detected consistently
    def file_offset(fp):
        try:
            data = json.loads(fp.read_text())
            return data.get("offset", 9999)
        except Exception:
            return 9999
    all_files.sort(key=file_offset)
    for filepath in all_files:
        try:
            content = filepath.read_text()
            data = json.loads(content)
            if data.get("success") and "devices" in data:
                offset = data.get("offset")
                if offset in seen_offsets:
                    print(f"Skipping duplicate offset={offset} in {filepath.name}")
                    continue
                seen_offsets.add(offset)
                devices.extend(data["devices"])
                print(f"Loaded {len(data['devices'])} devices from {filepath.name} (offset={offset})")
        except Exception as e:
            print(f"Skipping {filepath.name}: {e}")
    return devices


def domain_color(domain):
    colors = {
        "light": "FFF9C4",
        "switch": "E3F2FD",
        "sensor": "E8F5E9",
        "binary_sensor": "FFF3E0",
        "media_player": "F3E5F5",
        "camera": "FCE4EC",
        "climate": "E8EAF6",
        "button": "FBE9E7",
        "select": "E0F7FA",
        "number": "F1F8E9",
        "update": "F5F5F5",
        "lock": "E8EAF6",
        "cover": "FFF8E1",
        "alarm_control_panel": "FFEBEE",
        "event": "EDE7F6",
        "input_boolean": "F9FBE7",
        "device_tracker": "E8F5E9",
    }
    return colors.get(domain, "FFFFFF")


def build_spreadsheet(devices, output_path):
    wb = openpyxl.Workbook()

    # ── Sheet 1: Devices Summary ──────────────────────────────────────────────
    ws_dev = wb.active
    ws_dev.title = "Devices"

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    alt_fill = PatternFill("solid", fgColor="D6E4F0")
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    dev_headers = [
        "Device Name", "Manufacturer", "Model", "SW Version",
        "Integration", "Area", "Device ID", "Entity Count",
    ]
    for col, h in enumerate(dev_headers, 1):
        cell = ws_dev.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    ws_dev.row_dimensions[1].height = 20

    seen_device_ids = set()
    unique_devices = []
    for d in devices:
        if d["device_id"] not in seen_device_ids:
            seen_device_ids.add(d["device_id"])
            unique_devices.append(d)

    unique_devices.sort(key=lambda d: (d.get("name") or "").lower())

    for row_idx, d in enumerate(unique_devices, 2):
        fill = alt_fill if row_idx % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        row_data = [
            d.get("name") or "",
            d.get("manufacturer") or "",
            d.get("model") or "",
            d.get("sw_version") or "",
            d.get("integration_type") or "",
            d.get("area_id") or "",
            d.get("device_id") or "",
            len(d.get("entities") or []),
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws_dev.cell(row=row_idx, column=col, value=val)
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            cell.font = Font(size=9)

    col_widths_dev = [35, 22, 28, 16, 22, 22, 36, 12]
    for col, w in enumerate(col_widths_dev, 1):
        ws_dev.column_dimensions[get_column_letter(col)].width = w

    ws_dev.freeze_panes = "A2"
    ws_dev.auto_filter.ref = f"A1:{get_column_letter(len(dev_headers))}1"

    # ── Sheet 2: Entities (flat list) ─────────────────────────────────────────
    ws_ent = wb.create_sheet("Entities")

    ent_headers = [
        "Device Name", "Manufacturer", "Model", "Integration", "Area",
        "Entity ID", "Entity Name", "Domain", "Platform",
    ]
    for col, h in enumerate(ent_headers, 1):
        cell = ws_ent.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    ws_ent.row_dimensions[1].height = 20

    entity_row = 2
    for d in unique_devices:
        for ent in (d.get("entities") or []):
            entity_id = ent.get("entity_id") or ""
            domain = entity_id.split(".")[0] if "." in entity_id else ""
            dc = domain_color(domain)
            row_fill = PatternFill("solid", fgColor=dc)
            row_data = [
                d.get("name") or "",
                d.get("manufacturer") or "",
                d.get("model") or "",
                d.get("integration_type") or "",
                d.get("area_id") or "",
                entity_id,
                ent.get("name") or "",
                domain,
                ent.get("platform") or "",
            ]
            for col, val in enumerate(row_data, 1):
                cell = ws_ent.cell(row=entity_row, column=col, value=val)
                cell.fill = row_fill
                cell.border = border
                cell.alignment = Alignment(vertical="center")
                cell.font = Font(size=9)
            entity_row += 1

    col_widths_ent = [35, 22, 28, 18, 22, 55, 40, 20, 16]
    for col, w in enumerate(col_widths_ent, 1):
        ws_ent.column_dimensions[get_column_letter(col)].width = w

    ws_ent.freeze_panes = "A2"
    ws_ent.auto_filter.ref = f"A1:{get_column_letter(len(ent_headers))}1"

    # ── Sheet 3: Devices × Entities (grouped) ────────────────────────────────
    ws_grp = wb.create_sheet("Devices with Entities")

    grp_headers = [
        "Device Name", "Manufacturer", "Model", "SW Version",
        "Integration", "Area", "Entity ID", "Entity Name", "Domain", "Platform",
    ]
    for col, h in enumerate(grp_headers, 1):
        cell = ws_grp.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    ws_grp.row_dimensions[1].height = 20

    dev_header_fill = PatternFill("solid", fgColor="2E75B6")
    dev_header_font = Font(bold=True, color="FFFFFF", size=9)

    grp_row = 2
    for d in unique_devices:
        entities = d.get("entities") or []
        # Device header row
        dev_info = [
            d.get("name") or "",
            d.get("manufacturer") or "",
            d.get("model") or "",
            d.get("sw_version") or "",
            d.get("integration_type") or "",
            d.get("area_id") or "",
            "", "", "", "",
        ]
        for col, val in enumerate(dev_info, 1):
            cell = ws_grp.cell(row=grp_row, column=col, value=val)
            cell.font = dev_header_font
            cell.fill = dev_header_fill
            cell.border = border
            cell.alignment = Alignment(vertical="center")
        ws_grp.row_dimensions[grp_row].height = 16
        grp_row += 1

        for ent in entities:
            entity_id = ent.get("entity_id") or ""
            domain = entity_id.split(".")[0] if "." in entity_id else ""
            dc = domain_color(domain)
            row_fill = PatternFill("solid", fgColor=dc)
            row_data = [
                "", "", "", "", "", "",
                entity_id,
                ent.get("name") or "",
                domain,
                ent.get("platform") or "",
            ]
            for col, val in enumerate(row_data, 1):
                cell = ws_grp.cell(row=grp_row, column=col, value=val)
                cell.fill = row_fill
                cell.border = border
                cell.alignment = Alignment(vertical="center")
                cell.font = Font(size=9)
            ws_grp.row_dimensions[grp_row].height = 14
            grp_row += 1

        if not entities:
            # placeholder
            cell = ws_grp.cell(row=grp_row, column=7, value="(no entities)")
            cell.font = Font(italic=True, color="999999", size=9)
            cell.border = border
            grp_row += 1

    col_widths_grp = [35, 22, 28, 16, 22, 22, 55, 40, 20, 16]
    for col, w in enumerate(col_widths_grp, 1):
        ws_grp.column_dimensions[get_column_letter(col)].width = w

    ws_grp.freeze_panes = "A2"

    wb.save(output_path)
    print(f"\nSaved: {output_path}")
    print(f"Devices: {len(unique_devices)}")
    print(f"Entities: {entity_row - 2}")


if __name__ == "__main__":
    devices = load_all_devices()
    if not devices:
        print("No device data found!")
    else:
        build_spreadsheet(devices, "/home/user/ha-automations/ha_devices_entities.xlsx")
