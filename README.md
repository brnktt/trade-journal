# trade-journal

A command-line trade journal that does the one thing generic journals don't:
it **quantifies your execution leak** — the gap between what your setups
*should* have produced (plan-traded) and what you *actually* banked (realized).

If your strategy backtests at a high win rate but your live results keep
blowing up, the problem usually isn't the strategy — it's execution (dragging
stops, taking out-of-plan trades, skipping good setups). This tool turns that
leak into a number you can watch shrink.

## Why it exists

A real two-day sample:

| Day | Setups that hit target | What was banked | Leak |
|-----|------------------------|-----------------|------|
| 06-24 | 2 winners | both → break-even (dragged stops) | -2.6R |
| 06-25 | 1 winner | → scratch (dragged stop, swept) | -1.3R |

Three winning setups, zero banked. A +1.6R day became -1R. The strategy was
fine; the hands were the leak. This tool exists to make that impossible to
ignore.

## Install

```bash
cd ~/Projects/trade-journal
python3 -m pip install -e .      # gives you the `journal` command
```

No third-party dependencies (Python 3.10+, standard library only).

## Use

```bash
journal add            # log a trade interactively
journal stats          # performance + leak report
journal stats --since 2026-06-24
journal list -n 10     # recent trades
```

You can also log non-interactively:

```bash
journal add --setup "5m SIBI" --direction long --risk 500 --rr 1.3 \
            --result be --target-hit --dragged-stop
```

### What it records per trade

- setup, timeframe, session, direction, grade (1–5), price action, risk,
  planned R:R, result, duration
- **target_hit** — did price reach your planned target? (this is what unlocks
  the leak calculation)
- behaviour tags — **dragged_stop**, **out_of_plan**, **reversal_zone**
  (entered a SIBI / reversal zone before target)
- your own **custom tags** (e.g. `fomo`, `news`) — see [Tags](#tags)
- missed setups, with the R you'd have made if you'd taken them

## Tags

Every trade can carry tags. Two kinds:

- **Built-in** behaviour tags — `drag`, `oop`, `zone` — set by the
  `--dragged-stop` / `--out-of-plan` / `--reversal-zone` flags. These drive the
  leak attribution in `stats` and can't be renamed or deleted.
- **Custom** tags you define and manage yourself, for slicing trades any way you
  like (`fomo`, `news`, `revenge`, …).

Manage the custom tag registry:

```bash
journal tags list                 # show built-in + custom tags
journal tags add fomo             # create a tag (one word, no spaces)
journal tags rename fomo tilt     # rename everywhere (registry + all trades)
journal tags delete news          # delete everywhere (registry + all trades)
```

Attach tags when logging (the tag must exist first):

```bash
journal add --setup "revenge" --result loss --dragged-stop --tag fomo
```

### Tag-based filtering

Filter `list` and `stats` by any tag — built-in or custom. Repeat `--tag` to
require **all** of them (AND):

```bash
journal list  --tag zone            # every reversal-zone trade
journal stats --tag fomo            # leak report for just your fomo trades
journal list  --tag zone --tag oop  # trades that are both
```

This is how you test a hypothesis: tag the trades, then re-run `stats` on the
subset to see if that behaviour is where the leak lives.

### What the report tells you

- **Realized win rate** vs **setup hit rate** — how often you bank a win vs how
  often your setup actually works. A big gap = an execution problem.
- **Realized R vs plan-traded R**, in R and in dollars.
- **Leak**, attributed to dragged stops / out-of-plan trades.
- **Missed-setup opportunity cost.**

## Data

Trades live in `data/trades.csv` (human-readable, git-ignored — your trades
stay private). Point elsewhere with `TRADE_JOURNAL_DB=/path/to/file.csv`. Your
custom tag registry sits beside it as `<db-name>.tags.json`.

## Test

```bash
python3 -m unittest discover -s tests
```

Pure standard library — no test runner to install. Covers the model
(validation, R-accounting, serialization), storage (ids, delete, tag
registry), analytics (the leak math), and the CLI end-to-end.

## Roadmap

- Equity curve & R-distribution plots
- Per-setup and per-session breakdowns
- Import from broker / prop-firm trade exports
