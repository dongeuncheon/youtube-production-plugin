# Sources and decisions

Reviewed 2026-10-23. All seven source repositories were forked to dongeuncheon.
A fork is source preservation, not a claim that every feature is integrated or proven.
No source runtime is bundled in the lightweight plugin branch.

| Source fork | License | Use |
| --- | --- | --- |
| [youtube-production-plugin](https://github.com/dongeuncheon/youtube-production-plugin) | MIT | fork-ancestry-production-reference |
| [youtube-agent-skill](https://github.com/dongeuncheon/youtube-agent-skill) | MIT | editorial-reference |
| [claude-youtube](https://github.com/dongeuncheon/claude-youtube) | MIT | strategy-reference |
| [yutu](https://github.com/dongeuncheon/yutu) | Apache-2.0 | operations-adapter-candidate |
| [AI-Youtube-Shorts-Generator](https://github.com/dongeuncheon/AI-Youtube-Shorts-Generator) | MIT | clipping-adapter-candidate |
| [ShortGPT](https://github.com/dongeuncheon/ShortGPT) | MIT | editing-adapter-candidate |
| [MoneyPrinter](https://github.com/dongeuncheon/MoneyPrinter) | MIT | short-production-adapter-candidate |

## Selected concepts

- One editorial loop: topic evidence → hook/script → packaging → shot handoff → measured review.
- Separate observations from hypotheses and next experiments.
- Use explicit measurement units and declare experiment assumptions.
- Preserve provider/account routing already chosen by the user.

## Excluded complexity and unreliable logic

No embedded production server, DB, orchestrator, duplicated vendor SDKs, uploader or dashboard.
No arbitrary hook score presented as a success probability. No universal CTR/retention thresholds.
No inference of time units from values: this misread 45-second data in the original tool.
No claims that sequential title rotation proves causal improvement.

The two additional generation frameworks, ShortGPT and MoneyPrinter, are source candidates;
their production stacks are deliberately not required for installation.

Official references: [YouTube performance FAQ](https://support.google.com/youtube/answer/141805)
and [YouTube Analytics metrics](https://developers.google.com/youtube/analytics/metrics#audienceWatchRatio).
Absolute retention can exceed 100% due to replay; it is not a unique-viewer survival probability.
Pinned revisions and integration status are in ../../sources.lock.json.
