## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships. The graph auto-updates on commit.

At session start, run `graphify reflect --if-stale` to load lessons (preferred sources, dead ends, prior corrections). This is deterministic — no API cost.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules (in priority order):
- For focused codebase questions, run `graphify query "<question>"` first — it returns a scoped subgraph with source locations, cheaper than grepping files.
  - After each query, run `graphify save-result --question "<question>" --answer "<summary>" --type query --outcome useful` to close the feedback loop.
- Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concept breakdowns.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- Dirty graphify-out/ files are expected after hooks or incremental updates; do not skip graphify because of them.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- During compaction, the graphify plugin injects core concepts and code areas into the compaction summary, preserving codebase knowledge across compactions.
