import os
import sys
from dataclasses import dataclass
from contextlib import redirect_stderr
from io import StringIO


SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"
TARGET_SYMBOLS = ["^N225", "^GSPC", "VOO", "VTI", "QQQ", "USDJPY=X"]
US_STOCK_SYMBOLS = ["^GSPC", "VOO", "VTI"]
NASDAQ_SYMBOLS = ["QQQ"]


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    close: float | None = None
    change: float | None = None
    change_rate: float | None = None
    failed: bool = False


def load_local_env() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        raise RuntimeError(
            "python-dotenv がインストールされていません。`uv pip install -r requirements.txt` または `pip install -r requirements.txt` を実行してください。"
        ) from None

    load_dotenv()


def format_number(value: float) -> str:
    return f"{value:,.2f}"


def format_change(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,.2f}"


def format_change_rate(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def find_quote(quotes: list[MarketQuote], symbol: str) -> MarketQuote | None:
    return next((quote for quote in quotes if quote.symbol == symbol), None)


def quote_is_up(quote: MarketQuote | None) -> bool:
    return (
        quote is not None
        and not quote.failed
        and quote.change_rate is not None
        and quote.change_rate > 0
    )


def valid_change_rate(quote: MarketQuote | None) -> float | None:
    if quote is None or quote.failed or quote.change_rate is None:
        return None

    return quote.change_rate


def generate_market_summary(quotes: list[MarketQuote]) -> list[str]:
    us_stock_rates = [
        rate
        for symbol in US_STOCK_SYMBOLS
        if (rate := valid_change_rate(find_quote(quotes, symbol))) is not None
    ]
    nasdaq_rates = [
        rate
        for symbol in NASDAQ_SYMBOLS
        if (rate := valid_change_rate(find_quote(quotes, symbol))) is not None
    ]
    usd_jpy = find_quote(quotes, "USDJPY=X")

    lines = ["値動きサマリ"]
    if us_stock_rates and any(rate > 0 for rate in us_stock_rates):
        lines.append("- S&P500/VOO/VTIの値動きから、米国株は堅調です。")
    elif us_stock_rates:
        lines.append("- S&P500/VOO/VTIの値動きから、米国株は上値の重い展開です。")
    else:
        lines.append("- 米国株の方向感は取得データ不足で判断を控えます。")

    if nasdaq_rates:
        reference_rates = us_stock_rates or [0]
        if max(nasdaq_rates) > max(reference_rates):
            lines.append("- NASDAQ系が相対的に強く、ハイテク優勢です。")
        elif any(rate > 0 for rate in nasdaq_rates):
            lines.append("- NASDAQ系も底堅く推移しています。")
        else:
            lines.append("- NASDAQ系はやや弱く、ハイテク株には慎重な地合いです。")
    else:
        lines.append("- NASDAQ系の方向感は取得データ不足で判断を控えます。")

    if quote_is_up(usd_jpy):
        lines.append("- USDJPYは上昇しており、円安方向です。")
    elif valid_change_rate(usd_jpy) is not None:
        lines.append("- USDJPYは低下しており、円高方向です。")
    else:
        lines.append("- 為替の方向感は取得データ不足で判断を控えます。")

    if (us_stock_rates and any(rate > 0 for rate in us_stock_rates)) and quote_is_up(usd_jpy):
        lines.append("- 日本株には外部環境と為替が追い風になりやすい市況です。")
    elif us_stock_rates and any(rate > 0 for rate in us_stock_rates):
        lines.append("- 日本株には米国株高が支えになりやすい一方、為替の影響は確認が必要です。")
    elif quote_is_up(usd_jpy):
        lines.append("- 日本株には円安が輸出関連の支えになりやすい一方、米国株の弱さには注意が必要です。")
    else:
        lines.append("- 日本株には外部環境の支えが限られる市況です。")

    lines.append("- 投資助言ではなく、市況メモとしての整理です。")
    return lines


def fetch_market_quote(symbol: str) -> MarketQuote:
    try:
        import yfinance as yf
    except ModuleNotFoundError:
        raise RuntimeError(
            "yfinance がインストールされていません。`uv pip install -r requirements.txt` または `pip install -r requirements.txt` を実行してください。"
        ) from None

    try:
        with redirect_stderr(StringIO()):
            history = yf.Ticker(symbol).history(period="10d", auto_adjust=False)
        closes = history["Close"].dropna()
        if len(closes) < 2:
            return MarketQuote(symbol=symbol, failed=True)

        previous_close = float(closes.iloc[-1])
        before_previous_close = float(closes.iloc[-2])
        if before_previous_close == 0:
            return MarketQuote(symbol=symbol, failed=True)

        change = previous_close - before_previous_close
        change_rate = change / before_previous_close * 100
        return MarketQuote(
            symbol=symbol,
            close=previous_close,
            change=change,
            change_rate=change_rate,
        )
    except Exception:
        return MarketQuote(symbol=symbol, failed=True)


def fetch_market_quotes(symbols: list[str] = TARGET_SYMBOLS) -> list[MarketQuote]:
    return [fetch_market_quote(symbol) for symbol in symbols]


def build_message(quotes: list[MarketQuote]) -> str:
    lines = ["株式市況"]
    for quote in quotes:
        if quote.failed or quote.close is None or quote.change is None or quote.change_rate is None:
            lines.append(f"{quote.symbol}: 取得失敗")
            continue

        lines.append(
            f"{quote.symbol}: 前日終値 {format_number(quote.close)} / "
            f"前日比 {format_change(quote.change)} / "
            f"前日比率 {format_change_rate(quote.change_rate)}"
        )

    lines.append("")
    lines.extend(generate_market_summary(quotes))
    return "\n".join(lines)


def build_payload() -> dict[str, str]:
    return {"text": build_message(fetch_market_quotes())}


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
