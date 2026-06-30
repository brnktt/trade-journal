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

- setup, timeframe, direction, risk, planned R:R, result
- **target_hit** — did price reach your planned target? (this is what unlocks
  the leak calculation)
- behaviour tags — **dragged_stop**, **out_of_plan**, **reversal_zone**
  (entered a SIBI / reversal zone before target)
- missed setups, with the R you'd have made if you'd taken them

### What the report tells you

- **Realized win rate** vs **setup hit rate** — how often you bank a win vs how
  often your setup actually works. A big gap = an execution problem.
- **Realized R vs plan-traded R**, in R and in dollars.
- **Leak**, attributed to dragged stops / out-of-plan trades.
- **Missed-setup opportunity cost.**

## Data

Trades live in `data/trades.csv` (human-readable, git-ignored — your trades
stay private). Point elsewhere with `TRADE_JOURNAL_DB=/path/to/file.csv`.

## Test

```bash
python3 -m pytest        # or: python3 -m unittest
```

## Roadmap

- Equity curve & R-distribution plots
- Per-setup and per-session breakdowns
- Tag-based filtering (e.g. all `reversal_zone` trades) to test hypotheses
- Import from broker / prop-firm trade exports
