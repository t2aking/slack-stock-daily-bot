import unittest
from datetime import date
from unittest.mock import Mock, patch

from main import (
    DEFAULT_MARKET_CONFIG,
    MarketConfig,
    MarketEvent,
    MarketQuote,
    MarketSymbol,
    build_gemini_model_candidates,
    build_blocks,
    build_event_data_for_ai,
    build_ai_summary_prompt,
    build_market_data_for_ai,
    build_message,
    build_payload,
    extract_gemini_output_text,
    extract_text_from_gemini_node,
    fetch_market_quote,
    filter_relevant_events,
    format_exception_summary,
    format_event_line,
    generate_ai_market_summary,
    generate_market_summary,
    parse_market_events,
    parse_market_config,
    parse_model_list,
    parse_non_negative_int,
    parse_positive_float,
    request_ai_market_summary,
    should_try_next_gemini_model,
    summarize_response_data,
)


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
                    "- 米国市場の値動きから、米国株は堅調です。",
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
                    "- 米国市場の値動きから、米国株は上値の重い展開です。",
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
        events = [MarketEvent(date=date(2026, 7, 29), category="FOMC", title="FOMC政策金利発表", region="米国")]

        with (
            patch("main.load_market_config", return_value=DEFAULT_MARKET_CONFIG),
            patch("main.load_relevant_market_events", return_value=events),
            patch("main.fetch_market_quotes", return_value=quotes) as fetch_market_quotes,
            patch("main.generate_ai_market_summary", return_value=None) as generate_ai_market_summary,
        ):
            payload = build_payload()

        fetch_market_quotes.assert_called_once_with(DEFAULT_MARKET_CONFIG.all_symbols())
        generate_ai_market_summary.assert_called_once_with(quotes, DEFAULT_MARKET_CONFIG, events=events)
        self.assertIn("blocks", payload)
        self.assertIn("text", payload)
        self.assertIn("🟢 ^N225", payload["text"])
        self.assertIn("🟢 ^N225", payload["blocks"][1]["text"]["text"])
        self.assertIn("FOMC政策金利発表", payload["text"])

    def test_builds_message_with_ai_summary(self) -> None:
        quotes = [MarketQuote(symbol="^N225", close=39000, change=100, change_rate=0.25641)]
        ai_summary = "米国株と為替の動きを踏まえると、日本株は外部環境を確認しながら底堅さを探る展開です。"

        message = build_message(quotes, ai_summary=ai_summary)
        blocks = build_blocks(quotes, ai_summary=ai_summary)

        self.assertIn("値動きサマリ\n" + ai_summary, message)
        self.assertNotIn("- 投資助言ではなく", message)
        self.assertIn(ai_summary, blocks[5]["text"]["text"])

    def test_build_payload_uses_ai_summary_when_available(self) -> None:
        quotes = [MarketQuote(symbol="^N225", close=39000, change=100, change_rate=0.25641)]

        with (
            patch("main.load_market_config", return_value=DEFAULT_MARKET_CONFIG),
            patch("main.load_relevant_market_events", return_value=[]),
            patch("main.fetch_market_quotes", return_value=quotes),
            patch("main.generate_ai_market_summary", return_value="自然な市況メモです。"),
        ):
            payload = build_payload()

        self.assertIn("自然な市況メモです。", payload["text"])
        self.assertIn("自然な市況メモです。", payload["blocks"][5]["text"]["text"])

    def test_builds_all_failed_alert_payload(self) -> None:
        quotes = [
            MarketQuote(symbol=symbol.symbol, name=symbol.name, failed=True)
            for symbol in DEFAULT_MARKET_CONFIG.all_symbols()
        ]

        message = build_message(quotes)
        blocks = build_blocks(quotes)

        self.assertIn("⚠️ 全銘柄の株価取得に失敗しました。", message)
        self.assertIn("yfinanceまたはネットワークの状態を確認してください。", message)
        self.assertEqual(blocks[0]["text"]["text"], "株式市況取得エラー")
        self.assertIn("⚠️ 全銘柄の株価取得に失敗しました。", blocks[1]["text"]["text"])

    def test_fetch_market_quote_logs_unexpected_exception(self) -> None:
        yfinance = Mock()
        yfinance.Ticker.return_value.history.side_effect = RuntimeError("boom")

        with (
            patch.dict("sys.modules", {"yfinance": yfinance}),
            patch("main.logging.exception") as log_exception,
        ):
            quote = fetch_market_quote("^N225", "日経平均")

        self.assertTrue(quote.failed)
        self.assertEqual(quote.symbol, "^N225")
        self.assertEqual(quote.name, "日経平均")
        log_exception.assert_called_once_with("株価取得に失敗しました: %s", "^N225")

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
                "- 米国市場の値動きから、米国株は上値の重い展開です。",
                "- NASDAQ系はやや弱く、ハイテク株には慎重な地合いです。",
                "- USDJPYは低下しており、円高方向です。",
                "- 日本株には外部環境の支えが限られる市況です。",
                "- 投資助言ではなく、市況メモとしての整理です。",
            ],
        )

    def test_builds_message_from_custom_config(self) -> None:
        config = MarketConfig(
            japan_indices=(
                MarketSymbol(symbol="^N225", name="日経平均"),
                MarketSymbol(symbol="^TOPX", name="TOPIX"),
            ),
            us_indices=(MarketSymbol(symbol="VOO", name="VOO"),),
            fx=(MarketSymbol(symbol="USDJPY=X", name="USD/JPY"),),
        )
        message = build_message(
            [
                MarketQuote(symbol="^N225", name="日経平均", close=39000, change=100, change_rate=0.2),
                MarketQuote(symbol="^TOPX", name="TOPIX", close=2800, change=-10, change_rate=-0.36),
                MarketQuote(symbol="VOO", name="VOO", close=501, change=1, change_rate=0.2),
                MarketQuote(symbol="USDJPY=X", name="USD/JPY", close=160, change=0.8, change_rate=0.5),
            ],
            config,
        )

        self.assertIn("🟢 日経平均 (^N225): 前日終値 39,000.00", message)
        self.assertIn("🔴 TOPIX (^TOPX): 前日終値 2,800.00", message)
        self.assertIn("🟢 VOO: 前日終値 501.00", message)
        self.assertIn("🟢 USD/JPY (USDJPY=X): 前日終値 160.00", message)

    def test_builds_message_with_market_events(self) -> None:
        events = [
            MarketEvent(
                date=date(2026, 7, 29),
                end_date=date(2026, 7, 30),
                category="FOMC",
                title="FOMC政策金利発表",
                region="米国",
                importance="高",
                note="政策金利と声明文に注目",
            )
        ]

        message = build_message(
            [MarketQuote(symbol="^N225", close=39000, change=100, change_rate=0.2)],
            events=events,
        )
        blocks = build_blocks(
            [MarketQuote(symbol="^N225", close=39000, change=100, change_rate=0.2)],
            events=events,
        )

        expected_line = "📅 2026-07-29〜2026-07-30 FOMC FOMC政策金利発表 (米国) [高] - 政策金利と声明文に注目"
        self.assertIn("注目イベント\n" + expected_line, message)
        self.assertIn("*注目イベント*\n" + expected_line, blocks[4]["text"]["text"])

    def test_parses_market_config(self) -> None:
        config = parse_market_config(
            {
                "indices": {
                    "japan": [{"symbol": "^N225", "name": "日経平均"}],
                    "us": [{"symbol": "VOO", "name": "VOO"}],
                },
                "fx": [{"symbol": "USDJPY=X", "name": "USD/JPY"}],
            }
        )

        self.assertEqual(config.japan_indices[0], MarketSymbol(symbol="^N225", name="日経平均"))
        self.assertEqual(config.us_indices[0], MarketSymbol(symbol="VOO", name="VOO"))
        self.assertEqual(config.fx[0], MarketSymbol(symbol="USDJPY=X", name="USD/JPY"))

    def test_parses_market_events(self) -> None:
        events = parse_market_events(
            {
                "events": [
                    {
                        "date": "2026-07-29",
                        "end_date": "2026-07-30",
                        "category": "FOMC",
                        "title": "FOMC政策金利発表",
                        "region": "米国",
                        "importance": "高",
                        "note": "政策金利と声明文に注目",
                        "url": "https://example.com/fomc",
                    }
                ]
            }
        )

        self.assertEqual(
            events[0],
            MarketEvent(
                date=date(2026, 7, 29),
                end_date=date(2026, 7, 30),
                category="FOMC",
                title="FOMC政策金利発表",
                region="米国",
                importance="高",
                note="政策金利と声明文に注目",
                url="https://example.com/fomc",
            ),
        )

    def test_filters_relevant_market_events(self) -> None:
        events = [
            MarketEvent(date=date(2026, 6, 25), category="古い", title="対象外"),
            MarketEvent(date=date(2026, 6, 27), category="CPI", title="米CPI"),
            MarketEvent(date=date(2026, 7, 4), category="雇用統計", title="米雇用統計"),
            MarketEvent(date=date(2026, 7, 10), category="遠い", title="対象外"),
        ]

        relevant_events = filter_relevant_events(
            events,
            today=date(2026, 6, 28),
            lookback_days=1,
            lookahead_days=7,
        )

        self.assertEqual([event.title for event in relevant_events], ["米CPI", "米雇用統計"])

    def test_formats_event_line_without_optional_fields(self) -> None:
        self.assertEqual(
            format_event_line(MarketEvent(date=date(2026, 7, 3), category="雇用統計", title="米雇用統計")),
            "📅 2026-07-03 雇用統計 米雇用統計",
        )

    def test_formats_event_line_with_url(self) -> None:
        self.assertEqual(
            format_event_line(
                MarketEvent(
                    date=date(2026, 7, 29),
                    category="FOMC",
                    title="FOMC政策金利発表",
                    url="https://example.com/fomc",
                )
            ),
            "📅 2026-07-29 FOMC FOMC政策金利発表 / 詳細: https://example.com/fomc",
        )

    def test_builds_event_data_for_ai(self) -> None:
        data = build_event_data_for_ai(
            [MarketEvent(date=date(2026, 7, 3), category="雇用統計", title="米雇用統計", region="米国")]
        )

        self.assertIn("米雇用統計", data)

    def test_build_ai_summary_prompt_includes_events(self) -> None:
        prompt = build_ai_summary_prompt(
            [],
            events=[MarketEvent(date=date(2026, 7, 3), category="雇用統計", title="米雇用統計")],
        )

        self.assertIn("注目イベント:", prompt)
        self.assertIn("米雇用統計", prompt)

    def test_builds_market_data_for_ai(self) -> None:
        data = build_market_data_for_ai(
            [
                MarketQuote(symbol="^N225", name="日経平均", close=39000, change=100, change_rate=0.26),
                MarketQuote(symbol="^GSPC", name="S&P 500", failed=True),
            ]
        )

        self.assertIn("日本市場", data)
        self.assertIn("日経平均 (^N225): 前日終値 39,000.00, 前日比 +100.00, 前日比率 +0.26%", data)
        self.assertIn("S&P 500 (^GSPC): 取得失敗", data)

    def test_extracts_gemini_output_text_from_response(self) -> None:
        self.assertEqual(
            extract_gemini_output_text(
                {
                    "output_text": "自然な市況メモ",
                }
            ),
            "自然な市況メモ",
        )

    def test_extracts_gemini_output_text_from_candidates_response(self) -> None:
        self.assertEqual(
            extract_gemini_output_text(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "自然な"},
                                    {"text": "市況メモ"},
                                ]
                            }
                        }
                    ]
                }
            ),
            "自然な市況メモ",
        )

    def test_extracts_gemini_output_text_from_interactions_steps_response(self) -> None:
        self.assertEqual(
            extract_gemini_output_text(
                {
                    "status": "completed",
                    "steps": [
                        {
                            "response": {
                                "output_text": "米国株は堅調で、為替も円安方向です。"
                            }
                        }
                    ],
                }
            ),
            "米国株は堅調で、為替も円安方向です。",
        )

    def test_extracts_nested_text_from_gemini_node(self) -> None:
        self.assertEqual(
            extract_text_from_gemini_node(
                [
                    {
                        "output": [
                            {
                                "content": {
                                    "parts": [
                                        {"text": "自然な"},
                                        {"text": "市況メモ"},
                                    ]
                                }
                            }
                        ]
                    }
                ]
            ),
            "自然な市況メモ",
        )

    def test_summarizes_empty_gemini_response_data(self) -> None:
        self.assertEqual(
            summarize_response_data({"candidates": []}),
            'レスポンスキー: candidates. レスポンス抜粋: {"candidates":[]}',
        )

    def test_request_ai_market_summary_reports_empty_response_shape(self) -> None:
        response = Mock()
        response.json.return_value = {"candidates": []}
        requests = Mock()
        requests.post.return_value = response

        with patch.dict("sys.modules", {"requests": requests}):
            with self.assertRaisesRegex(RuntimeError, "レスポンスキー: candidates"):
                request_ai_market_summary("prompt", "test-api-key", "test-model")

    def test_request_ai_market_summary_posts_to_gemini_api(self) -> None:
        response = Mock()
        response.json.return_value = {"output_text": "自然な市況メモです。"}
        requests = Mock()
        requests.post.return_value = response

        with patch.dict("sys.modules", {"requests": requests}):
            summary = request_ai_market_summary("prompt", "test-api-key", "test-model")

        self.assertEqual(summary, "自然な市況メモです。")
        requests.post.assert_called_once()
        _, kwargs = requests.post.call_args
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "test-api-key")
        self.assertEqual(kwargs["json"]["model"], "test-model")
        self.assertEqual(kwargs["json"]["input"], "prompt")
        self.assertEqual(kwargs["json"]["generation_config"]["temperature"], 0.4)
        self.assertEqual(kwargs["json"]["generation_config"]["thinking_level"], "low")
        self.assertEqual(kwargs["timeout"], (5, 45.0))
        response.raise_for_status.assert_called_once()

    def test_request_ai_market_summary_uses_custom_timeout(self) -> None:
        response = Mock()
        response.json.return_value = {"output_text": "自然な市況メモです。"}
        requests = Mock()
        requests.post.return_value = response

        with patch.dict("sys.modules", {"requests": requests}):
            request_ai_market_summary("prompt", "test-api-key", "test-model", 60)

        _, kwargs = requests.post.call_args
        self.assertEqual(kwargs["timeout"], (5, 60))

    def test_generate_ai_market_summary_returns_none_without_api_key(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("main.request_ai_market_summary") as request_ai_market_summary,
        ):
            summary = generate_ai_market_summary([])

        self.assertIsNone(summary)
        request_ai_market_summary.assert_not_called()

    def test_generate_ai_market_summary_falls_back_on_error(self) -> None:
        with (
            patch("main.request_ai_market_summary", side_effect=RuntimeError("boom")),
            patch("main.logging.warning") as log_warning,
        ):
            summary = generate_ai_market_summary([], api_key="test-api-key", model="test-model")

        self.assertIsNone(summary)
        log_warning.assert_called_once_with(
            "AI要約の生成に失敗しました。ルールベースのサマリにフォールバックします。原因: %s",
            "test-model: RuntimeError: boom",
        )

    def test_generate_ai_market_summary_tries_fallback_model_on_retryable_error(self) -> None:
        response = Mock()
        response.status_code = 500
        response.text = '{"error":{"message":"high demand"}}'
        exc = RuntimeError("Gemini API error")
        exc.response = response

        with (
            patch.dict("os.environ", {"GEMINI_FALLBACK_MODELS": "fallback-model"}, clear=True),
            patch("main.request_ai_market_summary", side_effect=[exc, "fallback summary"]) as request_summary,
            patch("main.logging.warning") as log_warning,
        ):
            summary = generate_ai_market_summary([], api_key="test-api-key", model="primary-model")

        self.assertEqual(summary, "fallback summary")
        self.assertEqual(request_summary.call_args_list[0].args[2], "primary-model")
        self.assertEqual(request_summary.call_args_list[1].args[2], "fallback-model")
        log_warning.assert_called_once()
        self.assertIn("別のGeminiモデルで再試行します", log_warning.call_args.args[0])

    def test_generate_ai_market_summary_does_not_try_fallback_on_non_retryable_error(self) -> None:
        response = Mock()
        response.status_code = 400
        response.text = '{"error":{"message":"bad request"}}'
        exc = RuntimeError("Gemini API error")
        exc.response = response

        with (
            patch.dict("os.environ", {"GEMINI_FALLBACK_MODELS": "fallback-model"}, clear=True),
            patch("main.request_ai_market_summary", side_effect=exc) as request_summary,
            patch("main.logging.warning") as log_warning,
        ):
            summary = generate_ai_market_summary([], api_key="test-api-key", model="primary-model")

        self.assertIsNone(summary)
        request_summary.assert_called_once()
        log_warning.assert_called_once()
        self.assertIn("ルールベースのサマリにフォールバックします", log_warning.call_args.args[0])

    def test_formats_http_exception_summary(self) -> None:
        response = Mock()
        response.status_code = 400
        response.text = '{\n  "error": {"message": "invalid api key"}\n}'
        exc = RuntimeError("Gemini API error")
        exc.response = response

        self.assertEqual(
            format_exception_summary(exc),
            'RuntimeError: HTTPステータス: 400. Gemini API error レスポンス: { "error": {"message": "invalid api key"} }',
        )

    def test_parse_positive_float_returns_default_for_invalid_values(self) -> None:
        self.assertEqual(parse_positive_float(None, 45), 45)
        self.assertEqual(parse_positive_float("", 45), 45)
        self.assertEqual(parse_positive_float("invalid", 45), 45)
        self.assertEqual(parse_positive_float("0", 45), 45)
        self.assertEqual(parse_positive_float("60", 45), 60)

    def test_parse_non_negative_int_returns_default_for_invalid_values(self) -> None:
        self.assertEqual(parse_non_negative_int(None, 7), 7)
        self.assertEqual(parse_non_negative_int("", 7), 7)
        self.assertEqual(parse_non_negative_int("invalid", 7), 7)
        self.assertEqual(parse_non_negative_int("-1", 7), 7)
        self.assertEqual(parse_non_negative_int("0", 7), 0)
        self.assertEqual(parse_non_negative_int("14", 7), 14)

    def test_parse_model_list(self) -> None:
        self.assertEqual(parse_model_list(None), ())
        self.assertEqual(parse_model_list(" gemini-a, ,gemini-b "), ("gemini-a", "gemini-b"))

    def test_build_gemini_model_candidates_deduplicates_models(self) -> None:
        with patch.dict("os.environ", {"GEMINI_FALLBACK_MODELS": "fallback,primary"}, clear=True):
            self.assertEqual(build_gemini_model_candidates("primary"), ("primary", "fallback"))

    def test_should_try_next_gemini_model_for_retryable_status(self) -> None:
        response = Mock()
        response.status_code = 500
        exc = RuntimeError("server error")
        exc.response = response

        self.assertTrue(should_try_next_gemini_model(exc))

    def test_should_not_try_next_gemini_model_for_bad_request(self) -> None:
        response = Mock()
        response.status_code = 400
        exc = RuntimeError("bad request")
        exc.response = response

        self.assertFalse(should_try_next_gemini_model(exc))


if __name__ == "__main__":
    unittest.main()
