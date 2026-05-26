# Codemap: `.claude/skills/`

## Responsibility

Defines 17+ specialized skills for the AI-powered Chinese web novel writing engine. Each skill encapsulates a discrete workflow phase — from brainstorming through world-building, character design, outline planning, chapter writing, review, and revision. Skills follow a phase-gated pipeline (A1→A2→A3→B1→B2→B3→C1→C2→C3→D) with mandatory user-confirmation checkpoints.

---

## Topology

```
.claude/skills/
├── skill-loader-spec.md              # Skill loader specification
│
├── novel-writer/                     # [core] Router — dispatches to sub-skills by phase keyword
├── novel-setup/                      # [core] Project init + world-building
├── novel-character/                  # [core] Character distillation (7-step)
├── novel-planner/                    # [core] Full-book outline architecture
├── novel-planner-volume/             # [core] Per-volume chapter design
├── novel-chapter-writer/             # [core] Chapter writing orchestrator (v2)
├── novel-qa/                         # [core] Three-perspective review + AI fingerprint detection
├── novel-reviser/                    # [core] Text revision and polishing
│
├── abilitycraft/                     # [specialized] Ability system design
├── lorecraft/                        # [specialized] World-building terminology mapping
├── novel-ability-designer/           # [specialized] Standalone ability design
├── novel-creative-analyze/           # [specialized] Creative analysis
├── novel-skill-creator/              # [meta] Meta-skill for creating new skills
├── story-architecture/               # [specialized] Story structure design
├── prose-critique/                   # [specialized] Prose quality review (7 resource files)
├── brainstorm/                       # [specialized] Brainstorming engine
├── skill-evolver/                    # [experimental] Skill evolution
├── darwin-skill/                     # [experimental] Evolutionary skill testing
│
├── engines/                          # 39 on-demand writing engine .md files
├── phases/                           # 8 phase instruction files
├── shared/                           # 5 cross-skill protocol files
├── templates/                        # 6 entity template files
└── examples/                         # 7 example / reference files
```

---

## Core Skills (auto-routed)

### 1. `novel-writer/` — Router Skill

Top-level dispatcher. Reads user intent, maps to the correct sub-skill based on phase keywords. Owns the shared conventions and three-perspective analysis references.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — routing logic, phase-keyword mapping |
| `references/shared-conventions.md` | Iron-clad writing conventions (8 rules) shared across all skills |
| `references/three-perspective-analysis.md` | Three-perspective review methodology |
| `test-prompts.json` | Validation prompts |

### 2. `novel-setup/` — Project Initialization + World-Building

Handles A1 (brainstorm) and A2 (world-building) phases. Contains two agents for research and generation.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — setup workflow steps |
| `agents/generator.md` | Generative agent for world-building content |
| `agents/researcher.md` | Research agent for sourcing world-building material |

### 3. `novel-character/` — Character Design

A3 phase. Implements the 7-step character distillation process, appearance templates, and relationship differentiation.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — 7-step distillation workflow |
| `references/relationship-tracking.md` | Relationship tracking methodology |
| `test-prompts.json` | Validation prompts |

### 4. `novel-planner/` — Full-Book Outline

B1 phase. Architecture-level outline design with 5 specialized agents and token-budget management.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — outline architecture workflow |
| `agents/framework-architect.md` | Structural design agent |
| `agents/framework-validator.md` | Consistency validation agent |
| `agents/subplot-planner.md` | Subplot weaving agent |
| `agents/target-card-generator.md` | Target card generation agent |
| `agents/vein-designer.md` | Narrative vein design agent |
| `references/p0-fix-loop.md` | P0 priority fix loop protocol |
| `references/token-budget.md` | Token budget allocation strategy |
| `test-prompts.json` | Validation prompts |

### 5. `novel-planner-volume/` — Per-Volume Chapter Design

B1 sub-phase. Designs chapters within a single volume — scene lists, events, subplots. Uses incremental algorithm for large volumes.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — volume chapter design workflow |
| `agents/chapter-designer.md` | Chapter structure design agent |
| `agents/event-architect.md` | Event architecture agent |
| `agents/shared-constraints.md` | Cross-agent constraint enforcement |
| `references/volume-outline-template.md` | Volume outline template |
| `references/audit-report-template.md` | Audit report template |
| `references/display-templates.md` | Display formatting templates |
| `references/incremental-algorithm.md` | Incremental processing for large volumes |
| `test-prompts.json` | Validation prompts |

### 6. `novel-chapter-writer/` — Chapter Writing Orchestrator (v2)

B2 phase. Direct MCP + model pipeline with no sub-agents. Orchestrates: context loading → creative decisions → engine resolution → scene generation → validation → save.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — v2 orchestrator pipeline (5 steps, 2 checkpoints) |
| `references/agent-output-validation.md` | Output validation rules for generated content |
| `references/db-save-detail.md` | Database save protocol details |

### 7. `novel-qa/` — Quality Assurance

B3 phase. Three-perspective review (reader / author / character) + AI fingerprint detection.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — review workflow |
| `test-prompts.json` | Validation prompts |

### 8. `novel-reviser/` — Text Revision

Post-review revision and polishing. Fixes P0/P1/P2 issues identified by `novel-qa`.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — revision workflow |

---

## Specialized Skills

### 9. `abilitycraft/` — Ability System Design

Designs the novel's ability/power system with naming conventions and design case studies.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — ability design workflow |
| `references/naming-guide.md` | Ability naming conventions |
| `references/design-cases.md` | Reference design cases |
| `test-prompts.json` | Validation prompts |

### 10. `lorecraft/` — World-Building Terminology

Maps modern/technical terms to in-universe spiritual-fantasy equivalents (e.g., data→讯息, system→阵法, signal→灵波). Loaded before volume outlines, chapter text, or setting file generation.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — terminology mapping workflow |
| `references/term-map.md` | Core term mapping table |
| `references/core-principles.md` | Terminology design principles |
| `references/quickref.md` | Quick reference for in-flight lookups |

### 11. `novel-ability-designer/` — Standalone Ability Design

Independent skill for designing individual abilities outside the main workflow.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — standalone ability design |

### 12. `novel-creative-analyze/` — Creative Analysis

Analyzes creative decisions and their narrative implications.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — creative analysis workflow |

### 13. `novel-skill-creator/` — Meta-Skill

Creates new skills for the system. Follows the skill lifecycle specification.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — skill creation workflow |

### 14. `story-architecture/` — Story Structure Design

Designs macro-level story architecture — act structure, narrative arcs, pacing.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — story architecture workflow |

### 15. `prose-critique/` — Prose Quality Review

Multi-dimensional prose quality assessment across 7 resource dimensions.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — prose critique workflow |
| `resources/antipatterns.md` | Anti-pattern detection rules |
| `resources/baseline.md` | Quality baseline metrics |
| `resources/character.md` | Character voice consistency checks |
| `resources/continuity.md` | Continuity verification rules |
| `resources/prose.md` | Prose-level quality criteria |
| `resources/structure.md` | Structural quality criteria |
| `resources/voice.md` | Author voice consistency checks |

### 16. `brainstorm/` — Brainstorming Engine

General-purpose brainstorming with novel-specific methodology.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — brainstorming workflow |
| `references/methods.md` | General brainstorming methods |
| `references/novel-brainstorm.md` | Novel-specific brainstorming techniques |
| `test-prompts.json` | Validation prompts |

### 17. `skill-evolver/` — Skill Evolution

Evolves and improves existing skills through iterative refinement.

| File | Purpose |
|------|---------|
| `SKILL.md` | Entry point — skill evolution workflow |

### 18. `darwin-skill/` — Experimental Evolution

Evolutionary skill testing with result tracking. No `SKILL.md` entry point — operates via external orchestration.

| File | Purpose |
|------|---------|
| `results.tsv` | Tab-separated experiment results |
| `result-novel-planner-volume.html` | HTML visualization of planner-volume evolution |
| `test-prompts-all.json` | Full test prompt suite |

---

## Shared Infrastructure

### `engines/` — On-Demand Writing Engines (39 files)

Loaded at runtime by the `resolve_engines` MCP tool based on scene type. Not pre-loaded — each chapter only receives the engines relevant to its scenes.

| Category | Files | Purpose |
|----------|-------|---------|
| **Scene** | `scene-composition.md`, `scene-deepening.md`, `scene-type.md` | Scene structure, deepening techniques, type taxonomy |
| **Description** | `environment.md`, `dialogue.md`, `action.md`, `item.md` | Environment, dialogue, action, item description |
| **Battle** | `battle.md`, `ability.md` | Combat design, ability system |
| **Narrative** | `causality.md`, `spiral-structure.md`, `plot-density.md`, `relationship.md` | Causal chains, spiral structure, plot density, relationship dynamics |
| **Anti-AI** | `anti-ai.md`, `anti-ai-patterns.md` | Anti-AI fingerprint elimination (full reference) |
| **Author Voice** | `author-voice.md`, `author-voice-emotion.md`, `author-voice-daily.md`, `author-voice-battle.md`, `author-voice-mystery.md` | Three-layer author voice architecture (base + 4 emotion registers) |
| **Review** | `three-perspective.md`, `three-perspective-review.md`, `reader-perspective-agent.md`, `author-perspective-agent.md`, `character-perspective-agent.md`, `review-checklist.md` | Three-perspective review system + per-perspective agents |
| **World** | `worldbuilding.md`, `world-element-registry.md`, `genre.md` | World-building, element registry, genre conventions |
| **Character** | `character-design.md` | Character design engine |
| **Style** | `writing-style.md`, `corpus-style.md`, `writing-constraints.md` | Writing style, corpus-based style, hard constraints |
| **Other** | `snapshot.md`, `loading.md`, `outline-review.md`, `book-analysis.md`, `brainstorm.md`, `creative-methodology.md`, `platform.md` | Snapshots, loading, outline review, book analysis, brainstorming, creative methodology, platform |
| **Test** | `test-prompts.json` | Engine validation prompts |

### `phases/` — Phase Instruction Files (8 files)

Each file defines the entry conditions, allowed actions, and exit criteria for a workflow phase.

| File | Phase | Trigger |
|------|-------|---------|
| `a1-brainstorm.md` | A1 | "头脑风暴" / "灵感" |
| `a2-worldbuilding.md` | A2 | "建世界观" / "设定" |
| `a3-character.md` | A3 | "设计人物" / "人物卡" |
| `b1-volume.md` | B1 | "规划卷" / "大纲" |
| `b2-chapter.md` | B2 | "写第N章" / "继续写" |
| — | B3 | Handled by `novel-qa` skill |
| `c2-diagnose.md` | C2 | "诊断" / "卡文" |
| `c3-update.md` | C3 | "改设定" / "调整" |
| `README.md` | — | Phase system overview |

### `shared/` — Cross-Skill Protocols (5 files)

| File | Purpose |
|------|---------|
| `checkpoint-protocol.md` | 🔒 Checkpoint confirmation protocol (user must say "OK"/"继续") |
| `consistency-protocol.md` | Cross-skill consistency enforcement |
| `db-save-protocol.md` | Database save protocol (DB as authority, MCP as sole interface) |
| `engine-loading-protocol.md` | On-demand engine loading via `resolve_engines` MCP tool |
| `three-perspective-protocol.md` | Three-perspective review protocol shared across skills |

### `templates/` — Entity Templates (6 files)

Standard templates for DB-synced entities. Template sections map 1:1 to DB table columns.

| File | DB Table |
|------|----------|
| `character.md` | `characters` |
| `world-setting.md` | `world_settings` |
| `relation.md` | `character_relations` |
| `foreshadow.md` | `foreshadows` |
| `volume.md` | `volumes` |
| `chapter.md` | `chapters` |

### `examples/` — Reference Examples (7 files)

| File | Content |
|------|---------|
| `character.md` | Character description example |
| `deepening.md` | Scene deepening example |
| `dialogue.md` | Dialogue writing example |
| `dialogue-vocabulary.md` | Dialogue vocabulary reference |
| `item.md` | Item description example |
| `scene-templates.md` | Scene structure templates |
| `writing.md` | General writing example |

---

## Design Patterns

### SKILL.md as Entry Point
Every skill exposes a `SKILL.md` as its sole entry point. The file defines numbered workflow steps, mandatory checkpoints, and references to agents/references. Callers never access agents or references directly.

### Mandatory Checkpoints (🔒)
Steps marked with 🔒 require explicit user confirmation ("OK" / "继续") before proceeding. These gate critical transitions: world-building → character design → outline → chapter writing. Skipping a checkpoint is a flow violation.

### Phase-Gated Workflow
Skills can only be invoked in the correct phase order. The router (`novel-writer`) enforces this by checking the current phase before dispatching. Phase transitions are one-directional (A1→A2→A3→B1→B2→B3→C1/C2/C3→D) with C3 (cascade update) having highest priority.

### Engine Loading Protocol
Writing engines are loaded on-demand via the `resolve_engines` MCP tool, which selects engines based on scene type. Engines are never pre-loaded — this keeps per-chapter context at ~36KB. The protocol is defined in `shared/engine-loading-protocol.md`.

### Anti-AI System
Three-layer anti-AI fingerprint elimination:
1. `engines/anti-ai.md` — Full reference with 6 fingerprint types (F1–F6)
2. `engines/anti-ai-patterns.md` — Pattern catalog with detection and replacement rules
3. `SENTENCE-PATTERNS.md` (project root) — Runtime enforcement rules (punctuation diversity, information staging, scene structure randomization, negation caps, image gradients, ambient noise rotation)

### Agent Architecture
Skills may contain `agents/` subdirectories with specialized sub-workflow definitions. Agents are invoked by their parent skill's `SKILL.md` — they are not independently callable. The v2 chapter writer (`novel-chapter-writer`) eliminated all sub-agents in favor of direct MCP + model orchestration.

### Data Authority Chain
```
Skill operation → MCP tool → DB (authority) → sync_db_to_files() → File (human-readable copy)
```
All data writes go through MCP tools. Direct Python/sqlite3 access to the DB is prohibited. After MCP writes, `sync_db_to_files()` produces the human-readable file mirror.

---

## Skill Lifecycle Buckets

| Bucket | Skills | Auto-Routed |
|--------|--------|-------------|
| **core** | novel-writer, novel-setup, novel-character, novel-planner, novel-planner-volume, novel-chapter-writer | Yes |
| **quality** | novel-qa, novel-reviser | Yes |
| **specialized** | abilitycraft, lorecraft, novel-ability-designer, novel-creative-analyze, story-architecture, prose-critique, brainstorm | No |
| **meta** | novel-skill-creator, skill-evolver | No |
| **experimental** | darwin-skill | No |

---

## File Count Summary

| Directory | Files |
|-----------|-------|
| Skill directories (with SKILL.md) | 17 |
| `engines/` | 39 .md + 1 .json |
| `phases/` | 7 .md + 1 README |
| `shared/` | 5 .md |
| `templates/` | 6 .md |
| `examples/` | 7 .md |
| **Total** | ~83 files |
