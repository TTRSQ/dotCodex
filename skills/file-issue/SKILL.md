---
name: file-issue
description: File a GitHub issue after checking open and closed issues for duplicates, choosing a category and its heading template, and writing a Japanese title that names a specific subject. Use when asked to create, file, or turn something into an issue. A repository's own issue skill or issue template takes precedence.
---

# File Issue

Work in this order. Do not start writing the body before the category and template are settled.

## Precedence

If the target repository has its own issue skill (e.g. `.agents/skills/create-issue`) or issue templates (`.github/ISSUE_TEMPLATE/`), follow them instead of this skill. Keep the title and body in Japanese unless the repository says otherwise.

## 1. Choose a category

Pick the one category that fits the issue's purpose. The categories are standard forms, not a closed list.

| Category | Use when |
|---|---|
| Observation | Recording observed facts and evidence, without interpretation or solution |
| Problem | Stating an undesirable state and its impact; the solution is undecided |
| Proposal | Presenting a candidate solution for discussion |
| Decision | Recording a decision after comparing options |
| Execution | Defining decided work as implementable tasks |
| Experiment | Testing a hypothesis with a measurable method |
| Incident | Recording an outage's impact, response, and prevention |

- Do not mix categories. If facts, problem, proposal, decision, and implementation need separate tracking, file separate issues.

### When no category fits

Do not force one. Identify the reader and purpose, list the information needed for it, and order the headings so the reader can decide or act. Do not stitch together headings from the standard templates. The duplicate check and title rule still apply.

## 2. Check for duplicates

Search the target repository's open and closed issues.

1. Search several times by subject, symptom, and related type, function, or file names.
2. Open candidates with the same cause or completion criteria, even if worded differently, and read their bodies.
3. Decide:
   - **Duplicate**: same problem and completion criteria. Do not file; point to the existing issue.
   - **Contained**: part of, or parent of, an existing issue. Explain the relation; file only if there is a reason to split.
   - **Separate**: different cause or completion criteria. File it.
4. For closed issues, judge whether they were completed or whether this is a recurrence or an unresolved remainder.

The absence of an exact title match is not evidence of no duplicate.

## 3. Write the title

Write the title in Japanese. A reader must be able to identify the subject without asking.

- Execution: **specific subject + the concrete change to make**, not a bare action such as `整理する` or `統一する`.
- Every other category: **specific subject + what is happening to it**. Do not title with the solution, the work, or the ideal state, and do not make actions such as `整理する`, `分離する`, `統一する`, `導入する`, `移行する`, `〜に寄せる` the main clause.
- Do not lean on classifiers such as `refactor:`, `fix:`, `[設計]` to make up for a vague title.
- Do not stop at abstract words like `定義`, `処理`, `構成`; say what definition, process, or structure.

The NG rows for solutions and actions apply outside Execution.

| Verdict | Title | Why |
|---|---|---|
| NG | `ツール定義を一箇所に集約する` | It is a solution |
| NG | `同じ定義を複数箇所で管理している` | Which definition is unclear |
| OK | `ツールの入出力の定義が複数箇所に分かれている` | Subject and problem are clear |
| NG | `isolationId を必須にする` | It is an action |
| OK | `成果物の分離ルールが保存先によって異なる` | Subject and inconsistency are clear |
| OK (Execution) | `ツールの入出力の定義を一箇所に集約する` | Subject and the decided change are clear |

## 4. Write the body from the category template

For a standard category, read **only** the matching reference and use its headings. Write the content in Japanese.

| Category | Reference |
|---|---|
| Observation | [references/observation.md](references/observation.md) |
| Problem | [references/problem.md](references/problem.md) |
| Proposal | [references/proposal.md](references/proposal.md) |
| Decision | [references/decision.md](references/decision.md) |
| Execution | [references/execution.md](references/execution.md) |
| Experiment | [references/experiment.md](references/experiment.md) |
| Incident | [references/incident.md](references/incident.md) |

Do not fill unknown items by guessing; leave them as `未確認` or unchecked.

## 5. File it

Check the target repository, the category (or fallback) and why, the title, and the body, then create the issue. Pass the body via a temp file with `gh issue create --body-file`, not a heredoc. Report the issue number, category, final title, and URL.

If you judged it a duplicate, or contained with no reason to split, do not file; report the existing issue and the reason.
