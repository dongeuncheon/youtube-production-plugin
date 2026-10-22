---
name: youtube
description: Plan a YouTube video, prepare an authorized production handoff, or review measured retention and two-arm experiment evidence without publishing or making paid calls.
---

# YouTube production

Use one of three modes: **plan**, **production handoff**, or **review**. Ask for the mode only when the request does not make it clear. Never promise views, virality, a universal score, or algorithmic uplift.

Existing task-scoped user authorizations remain valid across modes. Do not request blanket confirmation for every mode; ask only when a new paid call, external mutation, or materially broader authority is actually needed.

Every deliverable must contain these fields:

- `sources`: user materials, measured files, and links actually consulted;
- `assumptions`: facts not established by a source;
- `uncertainty`: missing evidence and plausible limitations;
- `next_action`: one concrete, authorized next step;
- `measurement_plan`: metric, unit, observation window, and decision rule.

## Plan mode

Turn the brief into a decision-ready plan:

1. State audience, viewer need, promise, format, constraints, and evidence separately. Mark unknowns.
2. Draft a complementary title/thumbnail pair, opening promise, beat outline, and call to action. Explain how the title supplies context while the thumbnail adds a distinct visual reason to click; do not merely repeat the same words. These are hypotheses, not performance claims.
3. Write a shot list. Each shot has an ID, intended duration, narration/dialogue, visual purpose, source or provenance need, and accessibility notes.
4. Define the measurement plan before production. Do not invent benchmarks from unrelated channels.
5. When using benchmark or comparison evidence, distinguish traffic source, video format, and content age; do not treat unlike cohorts as directly comparable.

## Production handoff mode

Create artifacts a human or an already-available user tool can execute:

1. Provide the approved script with scene and timing markers.
2. For each shot, provide a self-contained visual prompt with subject, action, setting, composition, lighting, duration, aspect ratio, exclusions, and continuity notes.
3. Add voice, music, caption, rights/provenance, and assembly notes. Separate required inputs from optional creative choices.
4. Name the intended tool/provider only if the user has it available. Invoke an available tool only when the request authorizes that action and its cost or external effects. Otherwise stop at the handoff.
5. Never say media was rendered, uploaded, published, or paid for without tool evidence. This plugin has no provider adapter or publishing path.

## Review mode

Review the artifact against the plan and measured evidence:

1. Check promise-to-delivery alignment, pacing, shot continuity, captions, rights, and factual support.
2. Distinguish observations from interpretations and recommendations.
3. Use the bundled analysis tool for retention or two-arm experiment data. Do not infer input units. Aggregate retention may exceed 100% because of replay; describe changes in percentage points, never as individual exits or probability.
4. Recommend the smallest next test and keep observational results non-causal.

## Portable analysis command

In Claude Code, the script is:

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/analyze.py" --help
```

In portable/Codex mode, resolve the plugin root from this `SKILL.md` file: its parent is `skills/youtube`, so the plugin root is `../..`. Then run `scripts/analyze.py` from that resolved root. Do not assume the current working directory is the plugin directory.

Retention CSV must have `position,retention` columns and declare all units and duration:

```sh
python3 "$PLUGIN_ROOT/scripts/analyze.py" retention retention.csv \
  --axis-unit seconds --value-unit percent --duration-seconds 45
```

Experiment JSON must contain `design` and exactly two `arms`. Only a randomized, fixed-horizon, prespecified design with adequate expected counts receives a two-proportion test; all other comparisons remain observational or inconclusive.

See the plugin README's [experiment JSON and command example](../../README.md#analyze-an-experiment); using it does not require reading any external source repository.
