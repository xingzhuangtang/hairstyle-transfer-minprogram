---
description: Run Zero_Nine through one continuous host-native clarify-to-execute loop
subtask: true
---
Run the local Zero_Nine orchestration engine for the current project through one continuous host-native loop.

Use this same command on every turn:

`zero-nine run --host opencode --project . --goal "$ARGUMENTS"`

On the first turn, `$ARGUMENTS` is the user goal. If Brainstorming is still collecting answers, Zero_Nine will interpret the next invocation as the answer to the latest clarification question rather than launching execution. Keep invoking the same command with only the latest answer until Zero_Nine reports that Brainstorming is Ready, the OpenSpec bundle is bound, and guarded execution can continue.

Inspect live state at any time with `zero-nine status --project .`. The status output now includes runnable tasks, DAG blocking details, current loop stage, and the subagent runtime directory where dispatch records, recovery ledgers, and evidence paths are written for resume and review. Re-run `zero-nine export --project .` after binary upgrades so command help and shared skill text stay synchronized with the current scheduler and recovery contract.
