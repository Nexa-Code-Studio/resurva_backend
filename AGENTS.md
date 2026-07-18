## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships. The graph auto-updates on commit.

Rules (in priority order):
- After modifying code, run `graphify update .` in the background (do not wait for it to complete; let it run while you proceed with your work) to keep the graph current (AST-only, no API cost).
- Dirty graphify-out/ files are expected after hooks or incremental updates; do not skip graphify because of them.
- During compaction, the graphify plugin injects core concepts and code areas into the compaction summary, preserving codebase knowledge across compactions.

