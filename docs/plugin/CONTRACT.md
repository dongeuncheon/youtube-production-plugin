# YouTube Production — minimal plugin contract v0.1.0

User decision 2026-10-23: maximize simplicity; avoid heavy architecture.
One portable skill, one standard-library analysis script, no required services.
Claude Code plugin packaging and Codex SKILL.md compatibility are the default.

## Sources

Seven audited repositories are separately forked and pinned in sources.lock.json.
The production-engine fork retains upstream history/master; its Node runtime is not bundled
into the lightweight plugin branch. Workflow concepts are selected; arbitrary success scores,
unsupported algorithm weights and source defects are excluded.
Reference: https://support.google.com/youtube/answer/141805

## Acceptance

1. Valid marketplace/plugin manifests and exactly one discoverable skill.
2. Skill modes: plan, production handoff, review. Produce scripts, packaging,
   shot prompts, provider handoff and a measurement plan. No claim of rendered media without evidence.
3. One dependency-free Python analysis tool. Retention data explicitly declares axis
   (seconds/percent/ratio), value units and duration. Validate finite ordered bounded data;
   interpolate a declared endpoint, defaulting to min(30 seconds, video duration), so 15-second
   Shorts are supported. Never infer units from the largest value.
   Absolute audienceWatchRatio may exceed 1 (100%) due to replay; allow nonnegative finite
   values above 100 and do not label changes as unique-viewer loss.
4. Experiments validate integer clicks/impressions and report Wilson intervals.
   Sequential rotations are observational. Fixed-horizon randomized, prespecified two-arm
   comparisons may report statistical evidence with explicit assumptions, not guaranteed causality.
5. No server, DB, dashboard, HTTP bridge, vendor adapters, auto-publishing or paid calls.
6. Tests cover malformed inputs, short-video axis regression, ratio inputs, unit conversion,
   insufficient exposure and experimental assumptions. Fixtures are synthetic test data only.
7. Sources, assumptions, uncertainty and next action appear in deliverables.
8. No unsupported 100%-optimization, virality or real-channel uplift claims.

## Verify

`python3 -m unittest discover -s plugins/youtube-production/tests -v`
`python3 plugins/youtube-production/scripts/validate_plugin.py`
