import os
import sys


SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"
MESSAGE_TEXT = "株式市況Botのテスト投稿です。"


def load_local_env() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        raise RuntimeError(
            "python-dotenv がインストールされていません。`uv pip install -r requirements.txt` または `pip install -r requirements.txt` を実行してください。"
        ) from None

    load_dotenv()


def build_payload() -> dict[str, str]:
    return {"text": MESSAGE_TEXT}


def post_to_slack(webhook_url: str) -> None:
    try:
        import requests
    except ModuleNotFoundError:
        raise RuntimeError(
            "requests がインストールされていません。`uv pip install -r requirements.txt` または `pip install -r requirements.txt` を実行してください。"
        ) from None

    try:
        response = requests.post(webhook_url, json=build_payload(), timeout=10)
        response.raise_for_status()
    except (
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidSchema,
        requests.exceptions.InvalidURL,
    ):
        raise RuntimeError(
            f"{SLACK_WEBHOOK_ENV} がURL形式ではありません。Slack Incoming WebhookのURLを設定してください。"
        ) from None
    except requests.exceptions.Timeout:
        raise RuntimeError("Slackへの投稿がタイムアウトしました。ネットワーク接続を確認してください。") from None
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Slackへ接続できませんでした。ネットワーク接続を確認してください。") from None
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        response_text = exc.response.text if exc.response is not None else ""
        detail = f" レスポンス: {response_text}" if response_text else ""
        raise RuntimeError(f"Slackへの投稿に失敗しました。HTTPステータス: {status_code}.{detail}") from None
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Slackへの投稿中にエラーが発生しました: {exc}") from None


def main() -> int:
    try:
        load_local_env()
        webhook_url = os.environ.get(SLACK_WEBHOOK_ENV, "").strip()
        if not webhook_url:
            print(
                f"エラー: {SLACK_WEBHOOK_ENV} が設定されていません。\n"
                f".env に {SLACK_WEBHOOK_ENV}=https://hooks.slack.com/services/... を設定してください。",
                file=sys.stderr,
            )
            return 1

        post_to_slack(webhook_url)
    except RuntimeError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    print("Slackへのテスト投稿が完了しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
