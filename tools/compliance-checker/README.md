# Transport Compliance Checker (scheduled "loop agent")

A small Python tool for a **UK road-haulage Transport Manager** that scans a
folder of Excel workbooks (`.xlsx` / `.xlsm`), finds compliance **due-dates**, and
writes a dated, colour-coded **RAG report**:

- 🔴 **RED** – overdue
- 🟠 **AMBER** – due soon (default: within 30 days)
- 🟢 **GREEN** – nothing outstanding

It checks the usual O-licence items by reading column **headers**, so it works
across many differently-shaped files without you having to wire each one up:
MOT / annual test, road tax (VED), **PMI / safety inspections**, **tachograph
download & calibration**, **driver licence / CPC** checks, insurance, LOLER,
O-licence review dates, and anything else whose header contains a due/expiry word.

> ⚠️ **This is decision-support only.** It does not replace the qualified,
> named Transport Manager (CPC) legally required on the Operator's Licence.
> Always verify against your source records.

---

## Two ways to use this

**A. Dashboard briefing (`dashboard_briefing.py`)** — *recommended if you already
have a workbook with a `Master_Dashboard` tab that computes the RAG counts.* It
reads the headline numbers off your dashboard and turns them into a short
plain-English briefing. It finds each metric by its **label text** (e.g. it locates
"HGV MOT EXPIRED" and reads the count beside it), so it never touches the
personal-data action lists lower down. See **[Dashboard briefing](#dashboard-briefing)**.

**B. Folder scanner (`compliance_check.py`)** — scans a folder of workbooks, finds
date columns by their headers, and computes the RAG report itself. Use this if you
*don't* already have a dashboard. The rest of this README covers the scanner; the
dashboard option is self-contained in its own section below.

---

## Why it runs on *your* PC

Your spreadsheets live on your machine / OneDrive / network drive. This tool
reads them locally and writes the report locally — **your data never leaves your
PC**. The "loop" is simply Windows running it automatically on a schedule.

---

## 1. One-time setup (Windows)

1. **Install Python** (if you don't have it): https://www.python.org/downloads/
   — on the first installer screen, tick **"Add python.exe to PATH"**.
2. **Get these files** onto your PC. Either:
   - download this `compliance-checker` folder from the repo, or
   - `git clone` the repo and use `tools/compliance-checker`.
3. **Install the dependencies.** Open *Command Prompt*, then:
   ```bat
   cd path\to\compliance-checker
   pip install -r requirements.txt
   ```

## 2. Point it at your folders

Open `run_compliance_check.bat` in Notepad and edit the two lines:

```bat
set "ROOT=C:\Users\%USERNAME%\OneDrive\Compliance"
set "OUT=C:\Users\%USERNAME%\OneDrive\Compliance\Reports"
```

- `ROOT` = the top folder that contains your compliance spreadsheets (it scans
  sub-folders too).
- `OUT` = where the dated report is written (created if it doesn't exist).

## 3. Test it once

Double-click `run_compliance_check.bat`. A window shows what it scanned and where
the report was written, e.g.:

```
Report written: C:\...\Reports\compliance_report_2026-06-17.xlsx
WARNING: 3 item(s) OVERDUE.
```

Open that `.xlsx` — items are sorted worst-first with RAG colours.

---

## 4. Schedule it (the "loop")

### Windows Task Scheduler

1. Press Start, type **Task Scheduler**, open it.
2. **Create Basic Task…** → name it `Compliance Check` → **Next**.
3. Trigger: **Daily** → pick a time (e.g. 07:00) → **Next**.
4. Action: **Start a program** → **Browse…** to your `run_compliance_check.bat`.
5. Finish. (Tip: in the task's **Properties → General**, tick *"Run whether user
   is logged on or not"* if you want it to run headless.)

That's the whole loop: every morning it rebuilds the report so you start the day
with a current overdue/due-soon list.

> Prefer a fixed daily report file name (so it always overwrites) instead of a
> dated one? Tell me and I'll add a `--latest` flag.

---

## Usage reference (command line)

```bat
REM Zero-config, auto-discovery:
python compliance_check.py --root "C:\Compliance" --out "C:\Compliance\Reports"

REM Change the amber window to 45 days:
python compliance_check.py --root "C:\Compliance" --out "C:\Reports" --warning-days 45

REM Precise control via a config file:
python compliance_check.py --config config.yaml

REM Also keep a stable, always-overwritten copy for a dashboard / Power Automate:
python compliance_check.py --root "C:\Compliance" --out "C:\Reports" --latest
```

### Stable file names for dashboards (`--latest`)

By default each run produces a **dated** file (`compliance_report_2026-06-17.xlsx`),
so you build up history. Add `--latest` and it *also* writes fixed-name copies that
overwrite every run:

- `compliance_report_latest.xlsx`
- `compliance_briefing_latest.md`

Point Power Automate, a Power BI/Excel dashboard, an email flow, or a shared-drive
link at those stable names so they always pick up the most recent run without
needing to know today's date. The `run_compliance_check.bat` launcher already
passes `--latest`.

| Option | Meaning | Default |
|---|---|---|
| `--root` | Folder to scan (recursively) | – (required) |
| `--out` | Folder for the report | – (required) |
| `--warning-days` | Amber: flag items due within N days | 30 |
| `--critical-days` | Red-emphasis threshold | 7 |
| `--config` | Path to a `.yaml`/`.json` config | – |
| `--no-brief` | Skip the plain-English markdown briefing | off |
| `--latest` | Also write fixed-name `*_latest` copies that overwrite each run | off |

### Fine-tuning with a config

Copy `config.example.yaml` to `config.yaml` and edit it to:
- add **keywords** that match your own column names,
- pin **exact rules** to specific files/sheets/columns,
- set per-rule warning windows (e.g. PMI at 14 days, MOT at 30).

The built-in keyword list already covers most haulage terminology, so start with
auto-discovery and only add a config if something is missed or over-matched.

---

## Plain-English daily briefing

As well as the Excel report, every run writes a **plain-English markdown
briefing** next to it — `compliance_briefing_YYYY-MM-DD.md` — and prints it to the
console. It reads like:

```
# Transport Compliance Briefing — Wednesday 17 June 2026
Summary: 2 overdue · 1 due within 7 days · 3 due within 30 days.

## 🔴 Overdue — act now
- MOT Due — AB12 CDE — was due 12/06/2026 (5 days ago)
...
```

No AI required — it's generated deterministically from your data. (Add `--no-brief`
to skip it.)

### Optional: a conversational briefing via Claude `/loop`

If you install **Claude Code** on the same PC, you can have it run the checker on
an interval and turn that briefing into a short, prioritised, spoken-style summary
with suggested actions ("Book the AB12 CDE MOT today; chase John Smith's licence
check…"). See **`briefing-prompt.md`** for the ready-made `/loop` prompt, e.g.:

```
/loop 1d /compliance-briefing
```

Claude Code must be running on that PC for the loop to fire. The scheduled `.bat`
+ markdown briefing above is the dependency-free option and needs no AI at run time.

---

## Dashboard briefing

If your workbook already computes everything on a `Master_Dashboard` tab (RAG
count blocks like "HGV MOT EXPIRED", "DQC due within 30 days", etc.), use
`dashboard_briefing.py` to turn those headline numbers into a daily briefing —
no recomputing, and it only reads the summary counts.

### Run it

```bat
python dashboard_briefing.py --file "C:\path\to\Transport Compliance Workbook.xlsm"

REM also save the briefing (and a stable _latest copy) to a folder:
python dashboard_briefing.py --file "...xlsm" --out "C:\path\to\Reports"

REM with a config that pins your exact dashboard wording:
python dashboard_briefing.py --config dashboard.yaml
```

It prints the briefing plus a line like `Metrics matched: 18 | not found: 0`.

### First-run tuning

The tool ships with sensible default metric labels, but **your wording may differ
slightly**. On the first run, check the briefing for a line starting
"⚠️ Couldn't find these labels…". For anything listed:

1. Copy `dashboard.example.yaml` to `dashboard.yaml`.
2. Edit the `label:` text to match exactly what your dashboard cell says (case,
   spacing and punctuation don't matter — it's a forgiving match).
3. Add or remove metrics so the list mirrors your dashboard's categories.
4. Re-run with `--config dashboard.yaml` until `not found: 0`.

| Option | Meaning | Default |
|---|---|---|
| `--file` | Path to the workbook | – (required) |
| `--out` | Folder for the briefing (`.md` + `_latest`) | – (print only) |
| `--sheet` | Dashboard tab name | `Master_Dashboard` |
| `--config` | Path to `dashboard.yaml`/`.json` | – |

> Reads cached cell values. So the dashboard reflects the latest data, **open and
> save the workbook (which recalculates) before the briefing runs**, or schedule
> the briefing shortly after whatever updates the workbook.

### Schedule + conversational layer

Schedule `dashboard_briefing.py` exactly like the scanner (Windows Task Scheduler,
see above). The Claude `/loop` prompt in `briefing-prompt.md` works with this mode
too — point it at `dashboard_briefing.py` to get a prioritised, spoken-style
version of the briefing with suggested actions.

---

## Troubleshooting

- **"root folder not found"** – fix the `ROOT` path in the `.bat`.
- **Nothing flagged but you expected items** – your date columns may use unusual
  headers; add them under `keywords:` in a config, or send me a couple of sample
  headers and I'll extend the defaults.
- **Wrong dates** – the tool reads UK **day/month/year** for text dates. Cells
  formatted as real Excel dates are always read correctly.
- **`.xlsm` macros** – macros are ignored; only the data/values are read, so it's
  safe.
