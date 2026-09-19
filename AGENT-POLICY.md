# Agent policy

<!-- ai-generated: 75% - Claude Code drafted the justifications, reviewed by the author -->

`.claude/agents/reviewer.md` is a review-only subagent: it reads the diff and the contract docs and reports
mismatches, and is deliberately denied the tools that would let it act on its own findings instead of reporting
them. Each denied entry, and why:

- Bash(rm *): the reviewer reads and comments; deleting files is the author's decision, not the reviewer's.
- Bash(git push *): a review that could push would let a subagent publish changes the author never approved.
- Bash(docker *): the reviewer should read code and docs, not rebuild or restart the service it is reviewing.
- WebFetch: the review is judged against this repository's own contract docs, not against anything fetched
  live from the internet, which would make the review's basis unreproducible.
