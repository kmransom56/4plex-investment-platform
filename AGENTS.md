# AGENTS.md — 4plex-investment-platform

AI agent instructions for this repository. Applies to Cursor, Claude Code, Codex, and other agentskills-compatible tools.

## Project

4plex investment platform (backend + frontend) for multifamily investment workflows.

## Context Engineering Kit

Skills are installed globally (`plan-task`, `implement-task`, `do-and-judge`, etc.). Claude Code: slash commands. Cursor/Codex: invoke the skill by name.

### Default policy

| Situation | Use |
| --- | --- |
| Small / clear (1–few files) | SADD: `do-and-judge` or `do-in-steps` |
| Independent parallel targets | SADD: `do-in-parallel` |
| High-stakes single change | SADD: `do-competitively` |
| Multi-file / architecture / unclear requirements | SDD: `add-task` → `plan-task` → review → `implement-task` |
| Highest reliability | SDD + human review of the `.specs` task before implement |

Clear context between `plan-task` and `implement-task`.

### Spec paths

```
.specs/tasks/draft/        # add-task output
.specs/tasks/todo/         # plan-task output (ready)
.specs/tasks/in-progress/  # implement-task working
.specs/tasks/done/         # completed
.specs/scratchpad|analysis|reports/  # ephemeral (*.md gitignored)
.claude/skills/            # task-generated skills from plan-task
```

## Local conventions

- Follow existing backend/frontend patterns; do not invent parallel stacks
- Prefer `uv` for Python; respect Docker compose workflow when changing services
- Never guess ports — use `port-manager` / `port-registry`
- No mock/fake application data
- Do not commit unless explicitly asked
