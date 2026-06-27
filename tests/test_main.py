import unittest

from main import MarketQuote, build_message


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
                    symbol="VOO",
                    close=500,
                    change=-2.5,
                    change_rate=-0.5,
                ),
            ]
        )

        self.assertEqual(
            message,
            "\n".join(
                [
                    "株式市況",
                    "^N225: 前日終値 39,000.00 / 前日比 +100.00 / 前日比率 +0.26%",
                    "VOO: 前日終値 500.00 / 前日比 -2.50 / 前日比率 -0.50%",
                ]
            ),
        )

    def test_marks_failed_quote_without_raising(self) -> None:
        message = build_message([MarketQuote(symbol="^TOPX", failed=True)])

        self.assertEqual(message, "株式市況\n^TOPX: 取得失敗")


if __name__ == "__main__":
    unittest.main()
