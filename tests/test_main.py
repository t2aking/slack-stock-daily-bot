import unittest

from main import MarketQuote, build_message, generate_market_summary


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
                    "^N225: 前日終値 39,000.00 / 前日比 +100.00 / 前日比率 +0.26%",
                    "^GSPC: 前日終値 500.00 / 前日比 +2.50 / 前日比率 +0.50%",
                    "VOO: 前日終値 501.00 / 前日比 +1.00 / 前日比率 +0.20%",
                    "VTI: 前日終値 250.00 / 前日比 +1.25 / 前日比率 +0.50%",
                    "QQQ: 前日終値 450.00 / 前日比 +4.50 / 前日比率 +1.00%",
                    "USDJPY=X: 前日終値 160.00 / 前日比 +0.80 / 前日比率 +0.50%",
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
        message = build_message([MarketQuote(symbol="^TOPX", failed=True)])

        self.assertEqual(
            message,
            "\n".join(
                [
                    "株式市況",
                    "^TOPX: 取得失敗",
                    "",
                    "値動きサマリ",
                    "- 米国株の方向感は取得データ不足で判断を控えます。",
                    "- NASDAQ系の方向感は取得データ不足で判断を控えます。",
                    "- 為替の方向感は取得データ不足で判断を控えます。",
                    "- 日本株には外部環境の支えが限られる市況です。",
                    "- 投資助言ではなく、市況メモとしての整理です。",
                ]
            ),
        )

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
