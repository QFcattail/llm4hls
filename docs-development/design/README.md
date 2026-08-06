> [中文](README.cn.md)

# Detailed Design (Detailed Design)

> This directory holds the agent's detailed design documents. **Design docs describe "how it should be implemented" and may differ from the actual code -- defer to the code**.

## Document Manifest

| Document | Content | Corresponding Code | Status |
|---|---|---|---|
| `agent-architecture.md` | Overall agent architecture: control loop (linear with backtracking), checkpoint logic, observability, routing | `agent/` (all) | 🟢 Done v2.2 |
| `agent-code-design.md` | Cross-module code design / data flow | `agent/` (all) | 🟢 Done |
| `tui-design.md` | TUI dashboard design: four-zone layout, thread model, event bridging | `tui/` | 🟢 Done |
| `knowledge-base-schema.md` | bug->fix knowledge-base entry schema | `agent/knowledge-base/` | ⚪ To be written (draft in prep-study handbook Appendix B) |
| `eval-interface.md` | Evaluation interface contract (already solved by the official harness) | `contest/fpt26-harness/` | ✅ Not needed (harness ToolServer is the real interface) |

## Design Document Conventions

- Design documents **do not contain code**; they describe behavior, state, fields, and flows in prose.
- Detailed to the point where "you can't be any more detailed," so that a successor can reproduce the work.
- Key terms are given in both Chinese and English for easy lookup of English-language references.
- Each design document is paired with a `README.md` in the corresponding code directory (updated more frequently, includes known pitfalls).
- Design documents describe "how it should be implemented" and may differ from the actual code -- **defer to the code**; discrepancies are listed in this README or the corresponding document.

## Reading Order

1. First read `agent-architecture.md` -- to understand the agent's three-stage control loop (correctness -> synth -> optimize) and the checkpoint logic.
2. Read `agent-code-design.md` -- to understand the cross-module data flow and function call relationships.
3. Read `tui-design.md` -- to understand the four-zone layout and thread bridging model of the TUI dashboard.
4. Cross-reference the README and `.doc.md` in the code directory for implementation details.

## Review

Design reviews are in [`../reviews/`](../reviews/). P3 test-case writing may only begin after the design review passes.
