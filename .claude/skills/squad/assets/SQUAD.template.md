# Squad charter: <project name>

## Goal

<One or two sentences: what this project produces and what done looks like.>

## Members

| Name | Kind | Role | Owns |
|---|---|---|---|
| <human name> | human | Lead; breaks ties and approves merges | Scope and priorities |
| codex | agent (OpenAI Codex CLI) | <e.g. implementation> | <paths or areas> |
| claude | agent (Claude Code) | <e.g. design, review, writing> | <paths or areas> |

## How work moves

<Who starts a task, who reviews it, and when it counts as done. For example: codex implements on a branch, claude reviews, the lead merges.>

## Verification

<How anyone can show the work is right. For code: the exact commands (tests, typecheck, lint, a browser check). For analysis or writing: what is checked against what, e.g. every figure traced to its source file, every quote checked against the original. Nothing is handed off as done until this has been run and the result reported.>

## Conventions

- Checkouts: <one checkout or worktree per agent per task; where they live>
- Branches: <e.g. one branch per task, named member/slug>
- Commits: <e.g. message style, required trailers>
- Plans: <which tasks need the lead's approval of a plan before editing; default is anything larger than a small fix>
- Language: <e.g. documents in Portuguese, code and commits in English>

## Out of bounds

<Anything no agent should do without asking: deploys, deleting data, sending messages, spending money.>
