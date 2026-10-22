# YouTube Production

A small agent plugin: **plan → production handoff → review**.
One skill, one Python analysis tool. No server, database, dashboard or pip dependencies.

- [Install and use](plugins/youtube-production/README.md)
- [Research sources](docs/plugin/SOURCES.md) · [Pinned forks](sources.lock.json)

The skill helps create concepts, hooks, scripts, title/thumbnail pairs, shot prompts,
and a measurement plan. Actual rendering uses tools already available to the user.
The analysis tool reads explicitly labeled retention data and experiment counts.
It does not predict virality, publish videos, or silently spend generation credits.

```bash
python3 -m unittest discover -s plugins/youtube-production/tests -v
python3 plugins/youtube-production/scripts/validate_plugin.py
```

All seven reviewed repositories are forked. Their runtimes are not bundled into this plugin.
The original production engine is preserved on this fork's `master` branch and in Git history.

MIT. Original copyright and license retained in [LICENSE](LICENSE).
