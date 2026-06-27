import unittest
from unittest.mock import patch

from main import MarketQuote, build_blocks, build_message, build_payload, generate_market_summary


class BuildMessageTest(unittest.TestCase):
    def test_builds_market_summary(self) -> None:
        message = build_message(
            [
                MarketQuote(
                    symbol="^N225",
                    close=39000,
                    change=100,
                    change_rate=0.25641,
                ),
                MarketQuote(
                    symbol="^GSPC",
                    close=500,
                    change=2.5,
                    change_rate=0.5,
                ),
                MarketQuote(
                    symbol="VOO",
                    close=501,
                    change=1,
                    change_rate=0.2,
                ),
                MarketQuote(
                    symbol="VTI",
                    close=250,
                    change=1.25,
                    change_rate=0.5,
                ),
                MarketQuote(
                    symbol="QQQ",
                    close=450,
                    change=4.5,
                    change_rate=1.0,
                ),
                MarketQuote(
                    symbol="USDJPY=X",
                    close=160,
                    change=0.8,
                    change_rate=0.5,
                ),
            ]
        )

        self.assertEqual(
            message,
            "\n".join(
                [
                    "株式市況",
                    "日本市場",
                    "🟢 ^N225: 前日終値 39,000.00 / 前日比 +100.00 / 前日比率 +0.26%",
                    "",
                    "米国市場",
                    "🟢 ^GSPC: 前日終値 500.00 / 前日比 +2.50 / 前日比率 +0.50%",
                    "🟢 VOO: 前日終値 501.00 / 前日比 +1.00 / 前日比率 +0.20%",
                    "🟢 VTI: 前日終値 250.00 / 前日比 +1.25 / 前日比率 +0.50%",
                    "🟢 QQQ: 前日終値 450.00 / 前日比 +4.50 / 前日比率 +1.00%",
                    "",
                    "為替",
                    "🟢 USDJPY=X: 前日終値 160.00 / 前日比 +0.80 / 前日比率 +0.50%",
                    "",
                    "値動きサマリ",
                    "- S&P500/VOO/VTIの値動きから、米国株は堅調です。",
                    "- NASDAQ系が相対的に強く、ハイテク優勢です。",
                    "- USDJPYは上昇しており、円安方向です。",
                    "- 日本株には外部環境と為替が追い風になりやすい市況です。",
                    "- 投資助言ではなく、市況メモとしての整理です。",
                ]
            ),
        )

    def test_marks_failed_quote_without_raising(self) -> None:
        message = build_message(
            [
                MarketQuote(symbol="^N225", failed=True),
                MarketQuote(symbol="^GSPC", close=500, change=-2.5, change_rate=-0.5),
                MarketQuote(symbol="VOO", close=501, change=0, change_rate=0),
                MarketQuote(symbol="USDJPY=X", failed=True),
            ]
        )

        self.assertEqual(
            message,
            "\n".join(
                [
                    "株式市況",
                    "日本市場",
                    "⚠️ ^N225: 取得失敗",
                    "",
                    "米国市場",
                    "🔴 ^GSPC: 前日終値 500.00 / 前日比 -2.50 / 前日比率 -0.50%",
                    "⚪ VOO: 前日終値 501.00 / 前日比 0.00 / 前日比率 0.00%",
                    "",
                    "為替",
                    "⚠️ USDJPY=X: 取得失敗",
                    "",
                    "値動きサマリ",
                    "- S&P500/VOO/VTIの値動きから、米国株は上値の重い展開です。",
                    "- NASDAQ系の方向感は取得データ不足で判断を控えます。",
                    "- 為替の方向感は取得データ不足で判断を控えます。",
                    "- 日本株には外部環境の支えが限られる市況です。",
                    "- 投資助言ではなく、市況メモとしての整理です。",
                ]
            ),
        )

    def test_builds_block_kit_payload(self) -> None:
        quotes = [
            MarketQuote(symbol="^N225", close=39000, change=100, change_rate=0.25641),
            MarketQuote(symbol="^GSPC", close=500, change=-2.5, change_rate=-0.5),
            MarketQuote(symbol="VOO", close=501, change=0, change_rate=0),
            MarketQuote(symbol="QQQ", failed=True),
            MarketQuote(symbol="USDJPY=X", close=160, change=0.8, change_rate=0.5),
        ]

        blocks = build_blocks(quotes)

        self.assertEqual(blocks[0]["type"], "header")
        self.assertIn("*日本市場*", blocks[1]["text"]["text"])
        self.assertIn("🟢 ^N225", blocks[1]["text"]["text"])
        self.assertIn("*米国市場*", blocks[2]["text"]["text"])
        self.assertIn("🔴 ^GSPC", blocks[2]["text"]["text"])
        self.assertIn("⚪ VOO", blocks[2]["text"]["text"])
        self.assertIn("⚠️ QQQ: 取得失敗", blocks[2]["text"]["text"])
        self.assertIn("*為替*", blocks[3]["text"]["text"])
        self.assertIn("*値動きサマリ*", blocks[5]["text"]["text"])

    def test_build_payload_fetches_quotes_once_for_text_and_blocks(self) -> None:
        quotes = [MarketQuote(symbol="^N225", close=39000, change=100, change_rate=0.25641)]

        with patch("main.fetch_market_quotes", return_value=quotes) as fetch_market_quotes:
            payload = build_payload()

        fetch_market_quotes.assert_called_once_with()
        self.assertIn("blocks", payload)
        self.assertIn("text", payload)
        self.assertIn("🟢 ^N225", payload["text"])
        self.assertIn("🟢 ^N225", payload["blocks"][1]["text"]["text"])

    def test_generates_weak_market_summary(self) -> None:
        summary = generate_market_summary(
            [
                MarketQuote(symbol="^GSPC", change_rate=-0.3),
                MarketQuote(symbol="VOO", change_rate=-0.2),
                MarketQuote(symbol="VTI", change_rate=-0.1),
                MarketQuote(symbol="QQQ", change_rate=-0.4),
                MarketQuote(symbol="USDJPY=X", change_rate=-0.2),
            ]
        )

        self.assertEqual(
            summary,
            [
                "値動きサマリ",
                "- S&P500/VOO/VTIの値動きから、米国株は上値の重い展開です。",
                "- NASDAQ系はやや弱く、ハイテク株には慎重な地合いです。",
                "- USDJPYは低下しており、円高方向です。",
                "- 日本株には外部環境の支えが限られる市況です。",
                "- 投資助言ではなく、市況メモとしての整理です。",
            ],
        )


if __name__ == "__main__":
    unittest.main()
