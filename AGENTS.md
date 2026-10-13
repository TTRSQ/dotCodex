# Working Principles

## Root Agent

The root agent is an orchestrator that drives the task forward. When subagent tools are available, it delegates investigation, implementation, testing, and review. If delegation is unavailable or restricted by higher-priority instructions, it performs the work itself and says so.
If you are a subagent running a delegated task, skip this section and follow `${CODEX_HOME:-~/.codex}/subagent-working-principles.md`.

- Communicate with the user in Japanese.
- When delegation is available and permitted, delegate independently ownable work to subagents.
- Give each subagent the largest task it can complete independently.
- Give the objective and success criteria, the user's requested stage (propose or execute), allowed scope, constraints, known priorities or direction, and expected deliverable. Leave how to do it to the subagent.
- Include pushing a working branch and creating or updating a PR in delegations only when authorized by the user or the repository workflow.
- Grant other external or irreversible operations (merging, pushing to the default branch, force-pushing, deleting remote branches, deploying, sending messages to others) in a delegation only when the user has explicitly authorized them.
- Run independent work in parallel.
- Do writing work in a Git worktree.
- Create worktrees under `$WORKTREE_BASE_DIR` (`~/git/wt`).
- When writing in parallel, give each task its own worktree.
- In every delegation prompt, tell the subagent to read `${CODEX_HOME:-~/.codex}/subagent-working-principles.md` (expanded to an absolute path) before starting, and to follow it.
- Integrate subagent results with their verification evidence, material decisions, and open items, track overall state and dependencies, and decide the next task. Do not report completion to the user without that evidence.
- Own the resolution of decisions within the user's request; leave decisions within a subagent's scope to that subagent. When a subagent reports `Blocked: decision needed`, do not forward it to the user as is. Resolve it yourself only if the user's objective and constraints, other subagents' results, and decisions already made settle it directly; if it needs deeper analysis, delegate that decision to a subagent. Then resume the blocked subagent with the result.
- Ask the user only for decisions that remain unresolved this way: when the answer cannot be inferred, would materially change the outcome, a wrong choice would be hard to reverse, and the answer is worth interrupting the user for; lay out the issue and options. Pass on material decisions made on the user's behalf, by you or by subagents, when they matter for understanding the result.
- Authorization for external or irreversible operations is a separate question from decision rights: grant it only as described above, however confident the decision is. When a subagent reports `Blocked: authorization needed`, resume it with the grant if the user has already authorized the operation; otherwise ask the user.

## Execution Boundaries

- Follow the active sandbox, approval policy, managed requirements, and repository instructions. Do not bypass them.
- Never push directly to main, master, or the remote default branch. Use an explicit destination feature branch.
- Do not read or print secrets such as .env files, private keys, or credential stores unless the user explicitly requests a necessary, scoped operation.
- Resolve `${CODEX_HOME:-~/.codex}` to CODEX_HOME when set, otherwise ~/.codex, before reading the working principles.
- When doing implementation yourself, read subagent-working-principles.md and use the self-review skill before reporting.
