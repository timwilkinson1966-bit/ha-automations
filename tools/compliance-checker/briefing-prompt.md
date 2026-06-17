# Daily compliance briefing — prompt for Claude Code `/loop`

This is the prompt to hand to **Claude Code's `/loop` skill** on the PC where your
compliance files live, so you get a natural-English briefing each day on top of
the Excel report.

The checker script already writes a deterministic markdown briefing
(`compliance_briefing_YYYY-MM-DD.md`) — Claude's job here is to read it, prioritise
it like a Transport Manager would, and give you a short spoken-style summary with
suggested next actions.

---

## How to start it

Open Claude Code in the `compliance-checker` folder and run (once a day):

```
/loop 1d Run the daily compliance briefing below.
```

…then paste the **Prompt** section, or save the prompt as a slash command and run
`/loop 1d /compliance-briefing`. (`1d` = every 24 hours; use `12h`, `8h`, etc. to
taste. Claude Code must be running for the loop to fire.)

---

## Prompt

> You are assisting a UK road-haulage Transport Manager. Do the following:
>
> 1. Run the compliance checker (edit paths to match this machine):
>    `python compliance_check.py --root "C:\path\to\Compliance" --out "C:\path\to\Compliance\Reports"`
> 2. Read the markdown briefing it just wrote (the newest
>    `compliance_briefing_*.md` in the Reports folder).
> 3. Write a short, plain-English daily briefing (under ~150 words) that:
>    - leads with anything **overdue** — name the vehicle/driver and how late it is;
>    - then flags what's **due this week** and what's **due within 30 days**;
>    - groups sensibly (e.g. "two PMIs and one MOT due this week") rather than
>      just relisting every row;
>    - ends with a one-line **suggested action list** (book X, chase Y).
> 4. If nothing is overdue or due soon, say so in one upbeat line.
> 5. Do **not** invent items, dates, vehicles, or drivers — use only what's in the
>    briefing file. If the script reported errors opening a file, mention it.
>
> Remember this is decision-support only; it does not replace the qualified CPC
> holder named on the Operator's Licence.

---

## No Claude on that PC?

You don't need this at all to get a readable briefing — the script already writes
`compliance_briefing_YYYY-MM-DD.md` (plain English) and prints it to the console
every run. The `/loop` layer just makes it conversational and adds prioritised
actions.
