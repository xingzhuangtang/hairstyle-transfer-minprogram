---
name: zero-nine-orchestrator
description: Coordinate the Zero_Nine four-layer workflow. Use when you need one host command that can clarify requirements, bind an OpenSpec contract, run guarded execution, control the loop, and write back evolution artifacts.
---
## What to do

Route the request through four layers in order: Brainstorming, spec capture, execution, and evolution.

For Claude Code and OpenCode, treat the slash command as one continuous clarify-to-execute entry point. Reuse the same command for each answer until Zero_Nine reports that the session is Ready and the bound OpenSpec artifacts are complete. Do not bypass the clarification or specification gates by starting a separate execution command early.

Use `zero-nine status --project .` whenever you need an inspectable checkpoint. The status view now highlights runnable tasks, DAG blocking details, loop stage, and the subagent runtime directory that stores dispatch records, recovery ledgers, and resumable evidence. Treat those runtime artifacts and per-task reports as the canonical trace when you need to explain why the scheduler is blocked or what each subagent returned.

If host adapter files were exported before a runtime upgrade, refresh them with `zero-nine export --project .` so the local command help remains aligned with the latest scheduler window, retry behavior, and subagent recovery protocol.

## When to use me

Use this skill when a user wants a single entry point that can clarify requirements, produce inspectable specification artifacts, run a guarded implementation workflow, and write back progress and learning artifacts with minimal manual intervention.
