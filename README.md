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
🟢 ^N225: 前日終値 39,000.00 / 前日比 +100.00 / 前日比率 +0.26%

米国市場
🟢 ^GSPC: 前日終値 5,500.00 / 前日比 +25.00 / 前日比率 +0.46%
🟢 VOO: 前日終値 500.00 / 前日比 +2.50 / 前日比率 +0.50%
🟢 VTI: 前日終値 260.00 / 前日比 +1.30 / 前日比率 +0.50%
🟢 QQQ: 前日終値 480.00 / 前日比 +4.80 / 前日比率 +1.01%

為替
🟢 USDJPY=X: 前日終値 160.00 / 前日比 +0.80 / 前日比率 +0.50%

値動きサマリ
- S&P500/VOO/VTIの値動きから、米国株は堅調です。
- NASDAQ系が相対的に強く、ハイテク優勢です。
- USDJPYは上昇しており、円安方向です。
- 日本株には外部環境と為替が追い風になりやすい市況です。
- 投資助言ではなく、市況メモとしての整理です。
```

対象銘柄は `^N225`, `^GSPC`, `VOO`, `VTI`, `QQQ`, `USDJPY=X` です。
上昇は `🟢`、下落は `🔴`、横ばいは `⚪` で表示します。
個別銘柄の取得に失敗した場合でも処理は止めず、該当行に `⚠️ 取得失敗` と表示します。

## エラー時

`SLACK_WEBHOOK_URL` が未設定の場合、依存ライブラリが未インストールの場合、Slackへの投稿に失敗した場合は、標準エラーに原因がわかるメッセージを表示して終了します。

## 秘密情報の扱い

- `SLACK_WEBHOOK_URL` は `.env` に設定してください。
- `.env` など秘密情報を含むファイルはコミットしないでください。
- 本番やCIでは、実行環境の環境変数として `SLACK_WEBHOOK_URL` を設定しても動作します。
