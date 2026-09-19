# svcdesk - project instructions for Claude Code

<!-- ai-generated: 80% - Claude Code drafted from the project's own constitution and course rules, reviewed by the author -->

`svcdesk` is a Lab 1 course service (ITSM 2026/27): a JSON HTTP API implementing `docs/API.md`, verified by the
published checker (`docs/CHECKS.md`). See `.specify/memory/constitution.md` for the full principles; the
short version:

- `docs/API.md` is the enforced contract; `docs/REQUIREMENTS.md` is background. When they differ in precision,
  API.md wins.
- The image must run with zero network access at runtime — install every dependency at Docker build time.
- Three requirement conflicts (C1, C2, C3) are deliberately resolved and declared in `DECISIONS.md`; the running
  service's behavior must match that declaration exactly.
- No file is added under `src/` before the course's `specs` receipt exists for the current specs commit.
- Every file under `src/` and `specs/`, plus `DECISIONS.md`, carries an `ai-generated:` disclosure header in its
  first ten lines.
- Verify changes with `./itsmlab.sh verify 1` (builds and runs the service in Docker, then runs the conformance
  suite) rather than assuming code is correct from reading it.

See `.claude/agents/reviewer.md` and `AGENT-POLICY.md` for the review subagent's tool restrictions and why they
are set that way.
