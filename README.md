# slack-stock-daily-bot

Slackへ毎朝投稿する株式市況Botです。

Slack Incoming Webhookへ、yfinanceで取得した前日終値・前日比・前日比率をBlock Kit形式で投稿します。

## セットアップ

Python 3.10以上を想定しています。

`uv` を使う場合:

```bash
uv venv
source .venv/bin/activate
UV_LINK_MODE=copy uv pip install -r requirements.txt
```

外付けドライブなど、`uv` のキャッシュと仮想環境が別ファイルシステムにある場合はhardlinkのwarningが出ることがあります。`UV_LINK_MODE=copy` を指定すると、copy方式を明示してwarningを抑制できます。

`pip` を使う場合:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Slack Incoming Webhookの設定

SlackのIncoming Webhook URLは秘密情報なので、リポジトリにはコミットせず `.env` に設定します。

```bash
cp .env.example .env
```

`.env` の `SLACK_WEBHOOK_URL` にSlack Incoming Webhook URLを設定してください。

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

`.env` はgitの管理対象外です。

## 対象銘柄の設定

監視対象の銘柄は `stocks.yml` で設定します。

```yaml
indices:
  japan:
    - symbol: "^N225"
      name: "日経平均"
    - symbol: "^TOPX"
      name: "TOPIX"

  us:
    - symbol: "VOO"
      name: "VOO"
    - symbol: "VTI"
      name: "VTI"

fx:
  - symbol: "USDJPY=X"
    name: "USD/JPY"
```

別の設定ファイルを使う場合は、`.env` または実行環境の環境変数で `STOCK_CONFIG_PATH` を指定してください。

```env
STOCK_CONFIG_PATH=stocks.yml
```

`symbol` は yfinance で取得できるティッカー、`name` はSlack表示用の名称です。`name` と `symbol` が異なる場合は `日経平均 (^N225)` のように表示されます。

## 注目イベントの設定

市況の背景になりやすいイベントは `market_events.yml` で設定します。
初期状態では実イベントを投稿しないよう、コメント例だけを置いています。FOMC、CPI、雇用統計、日銀会合、米国主要決算など、運用で追いたい予定を公式日程に合わせて追加してください。

```yaml
events:
  - date: "2026-07-29"
    end_date: "2026-07-30"
    category: "FOMC"
    title: "FOMC政策金利発表"
    region: "米国"
    importance: "高"
    note: "政策金利、声明文、記者会見に注目"
    url: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

  - date: "2026-07-03"
    category: "雇用統計"
    title: "米雇用統計"
    region: "米国"
    importance: "高"
```

別の設定ファイルを使う場合は `EVENT_CONFIG_PATH` を指定してください。

```env
EVENT_CONFIG_PATH=market_events.yml
```

投稿対象は標準で「前日から7日後まで」のイベントです。範囲を変える場合は `EVENT_LOOKBACK_DAYS` と `EVENT_LOOKAHEAD_DAYS` を指定します。

```env
EVENT_LOOKBACK_DAYS=1
EVENT_LOOKAHEAD_DAYS=7
```

対象期間内のイベントがある場合はSlack投稿に `注目イベント` セクションを追加し、AI要約を使う場合はイベント情報もプロンプトに渡します。

## AI要約の設定

`GEMINI_API_KEY` を設定すると、値動きサマリをGemini APIで100〜150字程度の自然な市況メモに整形します。
数値分析はBot内のルールベース処理で行い、AIには文章化だけを任せます。

```env
EVENT_CONFIG_PATH=market_events.yml
EVENT_LOOKBACK_DAYS=1
EVENT_LOOKAHEAD_DAYS=7
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODELS=gemini-3.1-flash-lite,gemini-2.5-flash-lite
GEMINI_TIMEOUT_SECONDS=45
```

`GEMINI_API_KEY` が未設定の場合、またはAI要約の生成に失敗した場合は、従来のルールベースの箇条書きサマリを投稿します。
AI要約は投資助言ではなく市況メモとして生成するようプロンプトで制御していますが、投稿前に実運用に合う表現か確認してください。
Gemini APIの応答待ちは標準で45秒です。変更する場合は `GEMINI_TIMEOUT_SECONDS` を指定してください。
Gemini APIが混雑している場合は、`GEMINI_FALLBACK_MODELS` のモデルを左から順に試します。

## 投稿

```bash
python main.py
```

`uv` を使って仮想環境を有効化せずに実行する場合:

```bash
uv run python main.py
```

成功すると、Slackに日本市場 / 米国市場 / 為替 / サマリ を分けたBlock Kit形式で投稿されます。
通知用のフォールバック本文は以下の形式です。

```text
株式市況
日本市場
🟢 日経平均 (^N225): 前日終値 39,000.00 / 前日比 +100.00 / 前日比率 +0.26%

米国市場
🟢 S&P 500 (^GSPC): 前日終値 5,500.00 / 前日比 +25.00 / 前日比率 +0.46%
🟢 VOO: 前日終値 500.00 / 前日比 +2.50 / 前日比率 +0.50%
🟢 VTI: 前日終値 260.00 / 前日比 +1.30 / 前日比率 +0.50%
🟢 QQQ: 前日終値 480.00 / 前日比 +4.80 / 前日比率 +1.01%

為替
🟢 USD/JPY (USDJPY=X): 前日終値 160.00 / 前日比 +0.80 / 前日比率 +0.50%

注目イベント
📅 2026-07-29〜2026-07-30 FOMC FOMC政策金利発表 (米国) [高] - 政策金利、声明文、記者会見に注目

値動きサマリ
- 米国市場の値動きから、米国株は堅調です。
- NASDAQ系が相対的に強く、ハイテク優勢です。
- USDJPYは上昇しており、円安方向です。
- 日本株には外部環境と為替が追い風になりやすい市況です。
- 投資助言ではなく、市況メモとしての整理です。
```

`GEMINI_API_KEY` を設定している場合、値動きサマリは以下のような1段落の文章になります。

```text
値動きサマリ
米国株は主要指数やETFが堅調に推移し、NASDAQ系も相対的に強さが見られます。USD/JPYも上昇しており、外部環境と為替は日本株の支えになりやすい市況です。
```

初期設定の対象銘柄は `^N225`, `^GSPC`, `VOO`, `VTI`, `QQQ`, `USDJPY=X` です。
上昇は `🟢`、下落は `🔴`、横ばいは `⚪` で表示します。
個別銘柄の取得に失敗した場合でも処理は止めず、該当行に `⚠️ 取得失敗` と表示します。
全銘柄の取得に失敗した場合は、Slack投稿の先頭に `⚠️ 全銘柄の株価取得に失敗しました。` と表示します。

## 自動実行

GitHub Actionsで、火曜〜土曜の朝9時（JST）に自動投稿します。
GitHub ActionsのcronはUTC基準のため、設定は `0 0 * * 2-6` です。

public repositoryで秘密情報を扱うため、`.github/workflows/daily-stock.yml` は `stock-post` environmentを使います。
リポジトリの `Settings` → `Environments` → `stock-post` に、以下のEnvironment secretを登録してください。

```text
SLACK_WEBHOOK_URL
GEMINI_API_KEY
```

`GEMINI_API_KEY` はAI要約を使う場合だけ必要です。必要に応じて `Settings` → `Secrets and variables` → `Actions` のRepository variable `GEMINI_MODEL` でモデル名を変更できます。
`GEMINI_MODEL` が未設定の場合は `gemini-3.5-flash` を使います。
混雑時の退避先を変える場合はRepository variable `GEMINI_FALLBACK_MODELS` にカンマ区切りで指定してください。
Gemini APIのタイムアウトを変える場合はRepository variable `GEMINI_TIMEOUT_SECONDS` を指定してください。
イベント設定を変える場合はRepository variable `EVENT_LOOKBACK_DAYS` と `EVENT_LOOKAHEAD_DAYS` で投稿対象期間を調整できます。

workflowは最小権限として `permissions: contents: read` を指定しています。
GitHub側ではActionsのWorkflow permissionsをRead onlyにし、fork pull request workflowは外部コントリビューターの承認を必須にしてください。

`.github/workflows/daily-stock.yml` は `workflow_dispatch` にも対応しているため、GitHub Actions画面から手動実行もできます。

## エラー時

`SLACK_WEBHOOK_URL` が未設定の場合、銘柄設定ファイルが不正な場合、依存ライブラリが未インストールの場合、Slackへの投稿に失敗した場合は、標準エラーに原因がわかるメッセージを表示して終了します。
株価取得中に例外が発生した場合は、該当銘柄を `⚠️ 取得失敗` として扱い、例外ログを標準エラーへ出力します。
AI要約の生成に失敗した場合は標準エラーに警告ログを出力し、Slack投稿自体はルールベースのサマリで継続します。

## 秘密情報の扱い

- `SLACK_WEBHOOK_URL` は `.env` に設定してください。
- `GEMINI_API_KEY` を使う場合も `.env` または実行環境の秘密情報として設定してください。
- `.env` など秘密情報を含むファイルはコミットしないでください。
- 本番やCIでは、実行環境の環境変数として `SLACK_WEBHOOK_URL` を設定しても動作します。
