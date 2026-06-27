# Graph Report - .  (2026-06-27)

## Corpus Check
- Corpus is ~2,526 words - fits in a single context window. You may not need a graph.

## Summary
- 79 nodes · 138 edges · 7 communities (6 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.5)
- Token cost: 19,645 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Trade Domain & Reporting|Trade Domain & Reporting]]
- [[_COMMUNITY_Analytics & Tests|Analytics & Tests]]
- [[_COMMUNITY_CLI Interface|CLI Interface]]
- [[_COMMUNITY_R-Multiple Accounting|R-Multiple Accounting]]
- [[_COMMUNITY_CSV Storage|CSV Storage]]
- [[_COMMUNITY_Trade Model Serialization|Trade Model Serialization]]
- [[_COMMUNITY_Project Root|Project Root]]

## God Nodes (most connected - your core abstractions)
1. `Trade` - 24 edges
2. `analyze()` - 13 edges
3. `Report` - 7 edges
4. `Trade` - 7 edges
5. `june24_session()` - 6 edges
6. `db_path()` - 6 edges
7. `cmd_add()` - 5 edges
8. `load()` - 5 edges
9. `Execution Leak` - 5 edges
10. `format_report()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `june24_session()` --references--> `Trade`  [EXTRACTED]
  tests/test_analytics.py → trade_journal/models.py
- `test_missed_setup_opportunity_cost()` --calls--> `Trade`  [EXTRACTED]
  tests/test_analytics.py → trade_journal/models.py
- `test_clean_day_no_leak()` --calls--> `Trade`  [EXTRACTED]
  tests/test_analytics.py → trade_journal/models.py
- `test_realized_vs_plan_swing()` --calls--> `analyze()`  [EXTRACTED]
  tests/test_analytics.py → trade_journal/analytics.py
- `test_leak_attributed_to_dragged_stops()` --calls--> `analyze()`  [EXTRACTED]
  tests/test_analytics.py → trade_journal/analytics.py

## Import Cycles
- None detected.

## Communities (7 total, 1 thin omitted)

### Community 0 - "Trade Domain & Reporting"
Cohesion: 0.16
Nodes (18): dragged_stop, Execution Leak, journal add, journal command, journal list, journal stats, Performance & Leak Report, Missed Setup (+10 more)

### Community 1 - "Analytics & Tests"
Cohesion: 0.21
Nodes (12): june24_session(), Tests built around the real trades that motivated this tool.  The 2026-06-24 ses, test_clean_day_no_leak(), test_leak_attributed_to_dragged_stops(), test_missed_setup_opportunity_cost(), test_realized_vs_plan_swing(), test_setup_hit_rate_vs_realized_win_rate(), test_usd_view() (+4 more)

### Community 2 - "CLI Interface"
Cohesion: 0.20
Nodes (12): ArgumentParser, Namespace, format_report(), build_parser(), cmd_add(), cmd_list(), cmd_stats(), main() (+4 more)

### Community 3 - "R-Multiple Accounting"
Cohesion: 0.22
Nodes (5): R actually banked on this trade., R the written plan would have produced.          If the trade reached its target, R left on the table vs. trading the plan (>= 0 for executed)., For missed setups: R given up by not taking a trade that hit target., Trade

### Community 4 - "CSV Storage"
Cohesion: 0.46
Nodes (7): Path, append(), db_path(), load(), CSV-backed storage. Plain text so trades stay human-readable and editable., Location of the trades CSV (override with TRADE_JOURNAL_DB)., save_all()

### Community 5 - "Trade Model Serialization"
Cohesion: 0.33
Nodes (4): _fmt(), Core data model for a single trade and its R-multiple accounting.  The key idea:, _to_bool(), _to_float()

## Knowledge Gaps
- **5 isolated node(s):** `trade-journal`, `reversal_zone`, `TRADE_JOURNAL_DB`, `Python 3.10+ (standard library)`, `pytest / unittest`
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Trade` connect `R-Multiple Accounting` to `Analytics & Tests`, `CLI Interface`, `CSV Storage`, `Trade Model Serialization`?**
  _High betweenness centrality (0.320) - this node is a cross-community bridge._
- **Why does `analyze()` connect `Analytics & Tests` to `CLI Interface`, `R-Multiple Accounting`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `Report` connect `Analytics & Tests` to `CLI Interface`, `R-Multiple Accounting`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **What connects `trade-journal`, `Tests built around the real trades that motivated this tool.  The 2026-06-24 ses`, `trade-journal — a trade logger that quantifies execution leaks.  Most journals t` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._