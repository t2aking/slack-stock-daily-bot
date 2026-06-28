import os
import sys
from contextlib import redirect_stderr
from dataclasses import dataclass
from io import StringIO
from typing import Iterable


SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"
STOCK_CONFIG_ENV = "STOCK_CONFIG_PATH"
DEFAULT_STOCK_CONFIG_PATH = "stocks.yml"


@dataclass(frozen=True)
class MarketSymbol:
    symbol: str
    name: str | None = None

    @property
    def display_name(self) -> str:
        if not self.name or self.name == self.symbol:
            return self.symbol

        return f"{self.name} ({self.symbol})"


@dataclass(frozen=True)
class MarketConfig:
    japan_indices: tuple[MarketSymbol, ...]
    us_indices: tuple[MarketSymbol, ...]
    fx: tuple[MarketSymbol, ...]

    def all_symbols(self) -> tuple[MarketSymbol, ...]:
        return (*self.japan_indices, *self.us_indices, *self.fx)

    def sections(self) -> tuple[tuple[str, tuple[MarketSymbol, ...]], ...]:
        return (
            ("日本市場", self.japan_indices),
            ("米国市場", self.us_indices),
            ("為替", self.fx),
        )


DEFAULT_MARKET_CONFIG = MarketConfig(
    japan_indices=(MarketSymbol(symbol="^N225", name="日経平均"),),
    us_indices=(
        MarketSymbol(symbol="^GSPC", name="S&P 500"),
        MarketSymbol(symbol="VOO", name="VOO"),
        MarketSymbol(symbol="VTI", name="VTI"),
        MarketSymbol(symbol="QQQ", name="QQQ"),
    ),
    fx=(MarketSymbol(symbol="USDJPY=X", name="USD/JPY"),),
)


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    name: str | None = None
    close: float | None = None
    change: float | None = None
    change_rate: float | None = None
    failed: bool = False

    @property
    def display_name(self) -> str:
        if not self.name or self.name == self.symbol:
            return self.symbol

        return f"{self.name} ({self.symbol})"


def load_local_env() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        raise RuntimeError(
            "python-dotenv がインストールされていません。`uv pip install -r requirements.txt` または `pip install -r requirements.txt` を実行してください。"
        ) from None

    load_dotenv()


def parse_market_symbol(item: object, path: str) -> MarketSymbol:
    if not isinstance(item, dict):
        raise RuntimeError(f"{path} は symbol/name を持つオブジェクトで指定してください。")

    symbol = item.get("symbol")
    name = item.get("name")
    if not isinstance(symbol, str) or not symbol.strip():
        raise RuntimeError(f"{path}.symbol に空でない文字列を指定してください。")
    if name is not None and not isinstance(name, str):
        raise RuntimeError(f"{path}.name は文字列で指定してください。")

    return MarketSymbol(symbol=symbol.strip(), name=name.strip() if isinstance(name, str) else None)


def parse_market_symbol_list(data: object, path: str) -> tuple[MarketSymbol, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise RuntimeError(f"{path} はリストで指定してください。")

    return tuple(parse_market_symbol(item, f"{path}[{index}]") for index, item in enumerate(data))


def parse_market_config(data: object) -> MarketConfig:
    if not isinstance(data, dict):
        raise RuntimeError("銘柄設定ファイルのトップレベルはオブジェクトで指定してください。")

    indices = data.get("indices", {})
    if indices is None:
        indices = {}
    if not isinstance(indices, dict):
        raise RuntimeError("indices はオブジェクトで指定してください。")

    config = MarketConfig(
        japan_indices=parse_market_symbol_list(indices.get("japan"), "indices.japan"),
        us_indices=parse_market_symbol_list(indices.get("us"), "indices.us"),
        fx=parse_market_symbol_list(data.get("fx"), "fx"),
    )
    if not config.all_symbols():
        raise RuntimeError("銘柄設定ファイルには少なくとも1件のsymbolを指定してください。")

    return config


def load_market_config(path: str | None = None) -> MarketConfig:
    config_path = path or os.environ.get(STOCK_CONFIG_ENV, DEFAULT_STOCK_CONFIG_PATH)
    if not os.path.exists(config_path):
        if path is None and STOCK_CONFIG_ENV not in os.environ:
            return DEFAULT_MARKET_CONFIG

        raise RuntimeError(f"銘柄設定ファイルが見つかりません: {config_path}")

    try:
        import yaml
    except ModuleNotFoundError:
        raise RuntimeError(
            "PyYAML がインストールされていません。`uv pip install -r requirements.txt` または `pip install -r requirements.txt` を実行してください。"
        ) from None

    try:
        with open(config_path, encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except OSError as exc:
        raise RuntimeError(f"銘柄設定ファイルを読み込めませんでした: {config_path}: {exc}") from None
    except yaml.YAMLError as exc:
        raise RuntimeError(f"銘柄設定ファイルのYAML形式が不正です: {config_path}: {exc}") from None

    return parse_market_config(data)


def format_number(value: float) -> str:
    return f"{value:,.2f}"


def format_change(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,.2f}"


def format_change_rate(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def quote_status_icon(quote: MarketQuote) -> str:
    if quote.failed or quote.change is None or quote.change_rate is None:
        return "⚠️"
    if quote.change > 0:
        return "🟢"
    if quote.change < 0:
        return "🔴"
    return "⚪"


def format_quote_line(quote: MarketQuote) -> str:
    icon = quote_status_icon(quote)
    if quote.failed or quote.close is None or quote.change is None or quote.change_rate is None:
        return f"{icon} {quote.display_name}: 取得失敗"

    return (
        f"{icon} {quote.display_name}: 前日終値 {format_number(quote.close)} / "
        f"前日比 {format_change(quote.change)} / "
        f"前日比率 {format_change_rate(quote.change_rate)}"
    )


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


def is_nasdaq_symbol(symbol: MarketSymbol) -> bool:
    return "NASDAQ" in (symbol.name or "").upper() or symbol.symbol.upper() == "QQQ"


def generate_market_summary(
    quotes: list[MarketQuote], config: MarketConfig = DEFAULT_MARKET_CONFIG
) -> list[str]:
    us_stock_rates = [
        rate
        for symbol in config.us_indices
        if not is_nasdaq_symbol(symbol)
        if (rate := valid_change_rate(find_quote(quotes, symbol.symbol))) is not None
    ]
    nasdaq_rates = [
        rate
        for symbol in config.us_indices
        if is_nasdaq_symbol(symbol)
        if (rate := valid_change_rate(find_quote(quotes, symbol.symbol))) is not None
    ]
    usd_jpy = find_quote(quotes, "USDJPY=X")

    lines = ["値動きサマリ"]
    if us_stock_rates and any(rate > 0 for rate in us_stock_rates):
        lines.append("- 米国市場の値動きから、米国株は堅調です。")
    elif us_stock_rates:
        lines.append("- 米国市場の値動きから、米国株は上値の重い展開です。")
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


def fetch_market_quote(symbol: str, name: str | None = None) -> MarketQuote:
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
            return MarketQuote(symbol=symbol, name=name, failed=True)

        previous_close = float(closes.iloc[-1])
        before_previous_close = float(closes.iloc[-2])
        if before_previous_close == 0:
            return MarketQuote(symbol=symbol, name=name, failed=True)

        change = previous_close - before_previous_close
        change_rate = change / before_previous_close * 100
        return MarketQuote(
            symbol=symbol,
            name=name,
            close=previous_close,
            change=change,
            change_rate=change_rate,
        )
    except Exception:
        return MarketQuote(symbol=symbol, name=name, failed=True)


def fetch_market_quotes(symbols: Iterable[MarketSymbol] | None = None) -> list[MarketQuote]:
    target_symbols = tuple(symbols or load_market_config().all_symbols())
    return [fetch_market_quote(symbol.symbol, symbol.name) for symbol in target_symbols]


def quotes_for_symbols(quotes: list[MarketQuote], symbols: Iterable[MarketSymbol]) -> list[MarketQuote]:
    return [quote for symbol in symbols if (quote := find_quote(quotes, symbol.symbol)) is not None]


def append_quote_section(lines: list[str], title: str, quotes: list[MarketQuote]) -> None:
    lines.append(title)
    if quotes:
        lines.extend(format_quote_line(quote) for quote in quotes)
    else:
        lines.append("⚠️ 対象データがありません")


def build_message(quotes: list[MarketQuote], config: MarketConfig = DEFAULT_MARKET_CONFIG) -> str:
    lines = ["株式市況"]
    sections = [
        (title, quotes_for_symbols(quotes, symbols)) for title, symbols in config.sections()
    ]
    for index, (title, section_quotes) in enumerate(sections):
        if index > 0:
            lines.append("")
        append_quote_section(lines, title, section_quotes)

    lines.append("")
    lines.extend(generate_market_summary(quotes, config))
    return "\n".join(lines)


def build_blocks(
    quotes: list[MarketQuote], config: MarketConfig = DEFAULT_MARKET_CONFIG
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = [
        {"type": "header", "text": {"type": "plain_text", "text": "株式市況", "emoji": True}}
    ]
    sections = [
        (title, quotes_for_symbols(quotes, symbols)) for title, symbols in config.sections()
    ]
    for title, section_quotes in sections:
        text_lines = [f"*{title}*"]
        if section_quotes:
            text_lines.extend(format_quote_line(quote) for quote in section_quotes)
        else:
            text_lines.append("⚠️ 対象データがありません")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(text_lines)},
            }
        )

    summary_lines = generate_market_summary(quotes, config)
    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{summary_lines[0]}*\n" + "\n".join(summary_lines[1:]),
                },
            },
        ]
    )
    return blocks


def build_payload() -> dict[str, object]:
    config = load_market_config()
    quotes = fetch_market_quotes(config.all_symbols())
    return {"text": build_message(quotes, config), "blocks": build_blocks(quotes, config)}


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
