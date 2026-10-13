---
name: open-pull-request
description: Format and open a GitHub pull request with a Japanese, prefixed title and a Japanese body (背景 / 解決方法 / 変更の概要 / レビュー時の確認チェックリスト). Use when opening or rewriting a PR. A repository's own PR skill or PR template takes precedence.
---

# Open Pull Request

Covers the PR's format only. Running the `self-review` skill before this one is recommended.

## Precedence

If the target repository has its own PR skill (e.g. `.agents/skills/create-pull-request`) or a PR template (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `docs/pull_request_template.md`, etc.), follow it instead of this skill. Keep the title and body in Japanese unless the repository says otherwise.

## Title

- `<prefix>: <Japanese summary>`, 70 characters or fewer.
- Prefixes: `feat:` new feature, `fix:` bug fix, `refactor:`, `chore:` dependencies/config, `docs:`, `test:`.

## Body

Write in Japanese, for a reviewer seeing the PR for the first time. Keep each section short.

```markdown
## 背景

## 解決方法

## 変更の概要

## レビュー時の確認チェックリスト

- [ ] ...
```

- 背景: what is happening and why it is a problem, with the trigger (issue, report, thread) linked.
- 解決方法: the approach in one or two sentences; if there were alternatives, why this one.
- 変更の概要: let the reviewer grasp the whole change quickly. Use a Mermaid diagram for changed flows or interactions, or a Before/After table for behavior changes, where it helps.
- レビュー時の確認チェックリスト: concrete points the reviewer should check by hand, with steps and expected results.

## Create

Write the body to a temp file and pass it with `--body-file`; do not use a heredoc (backslash escapes break the formatting).

```bash
gh pr create --title "<title>" --body-file <path-to-body.md>
```
