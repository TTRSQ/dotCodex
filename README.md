# dotCodex

[dotClaude](https://github.com/TTRSQ/dotClaude) を参考にした、Codex のユーザー設定テンプレート。ルートエージェントが進行と判断を担い、サブエージェントが調査・実装・検証を担当する運用を配布する。

独立した仕事を並列に進め、実装時の文脈を持たないエージェントで差分をレビューする。委譲ツールが利用できない場合や上位の指示で制限される場合は、同じ作業原則に従って自身で作業し、独立レビューを実施できなかったことを報告する。長時間の実行や文脈の維持を保証するものではない。

## 管理対象

| リポジトリのパス | 反映先 | 内容 |
|---|---|---|
| `AGENTS.md` | `$CODEX_HOME/AGENTS.md` | ユーザーとは日本語・エージェント間は英語、委譲、判断と操作許可の分離 |
| `subagent-working-principles.md` | `$CODEX_HOME/subagent-working-principles.md` | 全体像からの設計、検証、報告の原則 |
| `config.toml` | `$CODEX_HOME/config.toml` | sandbox、承認の自動レビュー、サブエージェント |
| `rules/dotcodex.rules` | `$CODEX_HOME/rules/dotcodex.rules` | 一部の直接 push を禁止するコマンドルール |
| `skills/self-review/` | `~/.agents/skills/self-review/` | 実装後の独立レビュー |
| `skills/file-issue/` | `~/.agents/skills/file-issue/` | 重複調査、7分類のテンプレート、日本語の issue 作成 |
| `skills/open-pull-request/` | `~/.agents/skills/open-pull-request/` | 日本語の PR タイトル・本文、リポジトリのテンプレート優先 |
| `install.py` | 実行用 | 設定のマージ、退避、復元 |

`CODEX_HOME` の既定値は `~/.codex`。スキルの反映先は独立しており、`CODEX_HOME` を変えても変わらない。モデル、テーマ、MCP、プラグインは各自の設定に任せる。

`agents.max_concurrent_threads_per_session = 10` で、ルートを除くサブエージェントの同時実行上限を 10 にする（ルートを含めると最大 11）。設定の意味は[公式のサブエージェント設定](https://learn.chatgpt.com/docs/agent-configuration/subagents)を参照。

## セットアップ

前提: Codex CLI、Git、Python 3.11 以降。issue・PR を作る運用では `gh` も必要。

```bash
git clone git@github.com:TTRSQ/dotCodex.git ~/git/dotCodex
cd ~/git/dotCodex
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python install.py --dry-run
.venv/bin/python install.py
```

反映後は Codex を再起動する。利用環境や組織の管理設定により、一部の設定や委譲機能が制限される場合がある。

- リンクではなくコピーする。個人のフック・ルール・スキルは、テンプレートと同じファイル名でなければ残る。
- `config.toml` は、前回のテンプレート・現在の個人設定・新しいテンプレートを三者マージする。個人の値の変更・削除を優先し、未変更のテンプレート項目を更新する。`sandbox_workspace_write.writable_roots` は個人の追加・削除を残してテンプレートの差分を取り込む。その他の配列は順序や重複を変えず、値全体を三者マージする。コメントと既存の書式も可能な範囲で保持する。
- 初回から既存の値と競合する場合も個人設定が優先される。このため、テンプレートにある安全設定や機能設定が必ず有効になるわけではない。
- 作業原則・スキル・ルールの管理対象ファイルは上書きする。個人の変更がある場合は警告し、変更前のファイルを退避する。
- テンプレートから削除されたファイルは、前回の反映後に変更されていなければ削除する。変更済みなら残す。
- 反映状態を `$CODEX_HOME/.dotcodex-state.json` に記録する。変更がない再実行ではバックアップも作らない。
- 変更前の内容は、この clone/worktree の `backups/<timestamp>[-N]/` に保存する。個人設定に認証情報が含まれる可能性があるため、バックアップは Git 管理外にし、新しいバックアップディレクトリ・保存ファイルの権限を制限する。
- シンボリックリンクへの反映・復元は拒否する。コピー運用へ移行してから実行する。
- dry-run は反映先と操作を表示し、変更しない。設定値は認証情報の露出を避けるため表示しない。

### 更新とブランチの試用

```bash
git pull
.venv/bin/python install.py --dry-run
.venv/bin/python install.py

# 作業ブランチをコミットして試す
.venv/bin/python install.py --ref HEAD --dry-run
.venv/bin/python install.py --ref HEAD
```

既定の反映元は、最後に取得した `origin/HEAD` のコミット。作業コピーの未コミット変更は使わない。`origin/HEAD` がなければ `git remote set-head origin --auto` で設定する。

worktree の場所は `--worktree-dir <dir>`、`WORKTREE_BASE_DIR`、前回の反映値、`~/git/wt` の順で決める。インストール時に絶対パスへ展開し、作業原則と書き込み許可へ反映する。環境変数を他のセッションへ設定する機能はない。

### 復元と隔離した試用

```bash
.venv/bin/python install.py --restore --dry-run
.venv/bin/python install.py --restore            # 直近のバックアップへ戻す
.venv/bin/python install.py --restore 20261014090000

# 実際のユーザー設定を変えずに試す（先にコミットする）
.venv/bin/python install.py --ref HEAD \
  --codex-dir /private/tmp/dotcodex-demo/codex \
  --skills-dir /private/tmp/dotcodex-demo/agents/skills
```

復元直前の状態も新しいバックアップになる。バックアップを取得したのと同じ `CODEX_HOME` / `--codex-dir` / `--skills-dir` を指定すること。別の反映先のバックアップは復元できない。反映先を変更するときは、新しい空の反映先を使用する。バックアップは実行した clone/worktree に属するため、必要な間はその場所を保持する。

## dotClaude からの対応と制限

| dotClaude | dotCodex |
|---|---|
| `CLAUDE.md` | `AGENTS.md` |
| `settings.json` と auto mode | `config.toml` の `on-request` + `approvals_reviewer = "auto_review"` |
| `additionalDirectories` と Edit 許可 | `workspace-write` + worktree の `writable_roots` |
| Agent ツール | 利用環境の Codex サブエージェントツール |
| `PreToolUse` の push 拒否フック | コマンド prefix rules と作業原則・承認レビューへの方針 |
| Read deny | 秘密情報を扱わない作業原則。パスごとの強制 deny はこのテンプレートでは実装しない |

承認の自動レビューは sandbox を無効化しない。ネットワークは sandbox 内では既定で許可せず、必要な操作を承認フローへ渡す。マージ、force push、リモートブランチ削除、デプロイ、他者への送信は明示的な許可を必要とする。

`dotcodex.rules` は sandbox 外で実行するコマンドの prefix に適用される。`git push origin main` / `master` / `HEAD:main` / `HEAD:master` を禁止するが、`-C`、別 remote、別のオプション順、任意の refspec、別名コマンドなどを網羅するものではない。sandbox 内の操作や秘密情報の読み取りを完全に阻止する仕組みでもない。既定ブランチを保護する強制要件には、GitHub 等の branch protection と組織の管理設定を併用する。

動作の根拠: [公式の設定リファレンス](https://learn.chatgpt.com/docs/config-file/config-reference)、[AGENTS.md](https://developers.openai.com/codex/guides/agents-md)、[スキルの配置](https://learn.chatgpt.com/docs/build-skills)、[コマンドルール](https://learn.chatgpt.com/docs/agent-configuration/rules)。

## 検証

```bash
.venv/bin/python -m unittest discover -s tests -v
codex execpolicy check --rules rules/dotcodex.rules -- git push origin main
codex execpolicy check --rules rules/dotcodex.rules -- git push origin feature/example
```

テストは一時 Git リポジトリと一時反映先を使い、実際のユーザー設定に触れない。`.gitignore` はホワイトリスト方式。管理対象を増やす際は許可するパスも追加する。
