# youtube-production plugin

A deliberately small Claude Code marketplace plugin with one portable skill:

- `plan` turns a sourced brief into a script direction, shot list, and measurement plan.
- `production handoff` writes shot prompts and provider-neutral handoff artifacts. It does not render, spend, upload, or publish.
- `review` checks an artifact and analyzes explicitly declared retention or experiment data.

The package has no runtime dependencies, server, database, provider adapter, credential flow, or publishing endpoint.

## Install

In Claude Code:

```text
/plugin marketplace add dongeuncheon/youtube-production-plugin
/plugin install youtube-production@youtube-production
/youtube-production:youtube
```

For a local session without installing anything globally:

```sh
claude --plugin-dir /absolute/path/to/youtube-production-plugin/plugins/youtube-production
```

The marketplace entry is `.claude-plugin/marketplace.json`; the packaged plugin is `plugins/youtube-production`.

For Codex or another portable skill runner, load `plugins/youtube-production/skills/youtube/SKILL.md`. The skill explains how to resolve the bundled script without relying on the current directory.

## Analyze retention

The CSV header is `position,retention`. Units are never inferred. This 45-second example declares seconds and percent explicitly:

```sh
python3 plugins/youtube-production/scripts/analyze.py retention retention.csv \
  --axis-unit seconds --value-unit percent --duration-seconds 45
```

The evaluation endpoint defaults to `min(30, duration)`, so a 15-second Short is evaluated at 15 seconds. Use `--at-seconds N` for another finite endpoint greater than zero and no greater than the duration.

Axis units are `seconds`, `percent`, or `ratio` and must be bounded by the declared duration. Value units are `percent` or `ratio`; values must be finite and nonnegative but may exceed 100%/1 because replay can raise YouTube's aggregate audience-watch ratio. Positions must be strictly ordered and bracket the endpoint. Reported change is in percentage points, not individual-viewer loss or probability.

## Analyze an experiment

```json
{
  "source": "authorized analytics export",
  "assumptions": ["one eligible impression per assignment"],
  "design": {"assignment": "randomized", "horizon": "fixed", "prespecified": true, "alpha": 0.05},
  "arms": [
    {"name": "control", "clicks": 80, "impressions": 1000},
    {"name": "variant", "clicks": 105, "impressions": 1000}
  ]
}
```

```sh
python3 plugins/youtube-production/scripts/analyze.py experiment experiment.json
```

Wilson intervals are always reported. A two-proportion test runs only for a prespecified, randomized, fixed-horizon two-arm design with adequate expected cell counts. Sequential rotations are descriptive, not causal.

## Test and validate

```sh
python3 -m unittest discover -s plugins/youtube-production/tests -v
python3 plugins/youtube-production/scripts/validate_plugin.py
```

Tests use synthetic data and make no network or paid-provider calls.
