"""Unit tests for server-side ETF exposure aggregation (no live FMP calls)."""

from bigdata_thematic_screener.api.fmp_etf import (
    MAX_BASKET_TICKERS,
    aggregate_etf_exposure,
    apply_etf_symbol_filter,
    build_focus_etf_row_from_holdings,
    normalize_focus_etf_list,
    normalize_symbol,
    resolve_ticker_basket,
    _holding_equity_symbol,
    _parse_fmp_rows,
    _parse_holdings_rows,
)
from bigdata_thematic_screener.api.models import TickersBasketMode


def test_normalize_symbol() -> None:
    assert normalize_symbol("  aapl  ") == "AAPL"


def test_resolve_ticker_basket_only_this_mode() -> None:
    scoring = {"Co A": {"ticker": "AAA", "composite_score": 10}}
    tickers, warnings = resolve_ticker_basket(
        scoring,
        top_n=1,
        extra_tickers=["  nvda ", "AAPL", "NVDA"],
        tickers_mode=TickersBasketMode.only,
    )
    assert tickers == ["NVDA", "AAPL"]
    assert warnings == []


def test_resolve_ticker_basket_only_mode_empty_warns() -> None:
    tickers, warnings = resolve_ticker_basket(
        {"X": {"ticker": "ZZZ", "composite_score": 1}},
        top_n=5,
        extra_tickers=[],
        tickers_mode=TickersBasketMode.only,
    )
    assert tickers == []
    assert warnings


def test_resolve_ticker_basket_top_n_and_extras() -> None:
    scoring = {
        "Co A": {"ticker": "AAA", "composite_score": 10},
        "Co B": {"ticker": "BBB", "composite_score": 5},
        "Co C": {"ticker": "CCC", "composite_score": 8},
    }
    tickers, warnings = resolve_ticker_basket(
        scoring, top_n=2, extra_tickers=["bbb", "ZZZ"]
    )
    assert tickers == ["AAA", "CCC", "BBB", "ZZZ"]
    assert warnings == []


def test_resolve_ticker_basket_cap_and_warning() -> None:
    scoring = {f"C{i}": {"ticker": f"T{i}", "composite_score": i} for i in range(50)}
    extras = [f"E{i}" for i in range(50)]
    tickers, warnings = resolve_ticker_basket(
        scoring, top_n=30, extra_tickers=extras, max_total=MAX_BASKET_TICKERS
    )
    assert len(tickers) == MAX_BASKET_TICKERS
    assert any("capped" in w.lower() for w in warnings)


def test_parse_fmp_rows_dedupes_by_max_weight() -> None:
    raw = [
        {"etfSymbol": "SPY", "weightPercentage": 5, "marketValue": 1e9},
        {"etfSymbol": "SPY", "weightPercentage": 8, "marketValue": 2e9},
    ]
    out = _parse_fmp_rows(raw)
    assert len(out) == 1
    assert out[0]["etfSymbol"] == "SPY"
    assert out[0]["weightPercentage"] == 8


def test_parse_fmp_rows_drops_invalid_weight() -> None:
    raw = [
        {"etfSymbol": "X", "weightPercentage": 101, "marketValue": 1},
        {"etfSymbol": "Y", "weightPercentage": 0, "marketValue": 1},
    ]
    assert _parse_fmp_rows(raw) == []


def test_aggregate_etf_exposure_min_match_and_aum() -> None:
    ticker_results = [
        {
            "ticker": "A",
            "exposures": [
                {"etfSymbol": "E1", "weightPercentage": 10, "marketValue": 1e10},
            ],
        },
        {
            "ticker": "B",
            "exposures": [
                {"etfSymbol": "E1", "weightPercentage": 5, "marketValue": 5e9},
            ],
        },
    ]
    etfs = aggregate_etf_exposure(ticker_results, min_match_count=2)
    assert len(etfs) == 1
    assert etfs[0]["etfSymbol"] == "E1"
    assert etfs[0]["matchCount"] == 2
    assert etfs[0]["themeScore"] == 15


def test_aggregate_excludes_theme_score_over_100_percent() -> None:
    ticker_results = [
        {"ticker": "A", "exposures": [{"etfSymbol": "HOT", "weightPercentage": 55, "marketValue": 2e10}]},
        {"ticker": "B", "exposures": [{"etfSymbol": "HOT", "weightPercentage": 60, "marketValue": 2e10}]},
        {"ticker": "C", "exposures": [{"etfSymbol": "OK", "weightPercentage": 6, "marketValue": 1e10}]},
        {"ticker": "D", "exposures": [{"etfSymbol": "OK", "weightPercentage": 7, "marketValue": 1e10}]},
    ]
    etfs = aggregate_etf_exposure(ticker_results, min_match_count=2)
    symbols = {e["etfSymbol"] for e in etfs}
    assert "HOT" not in symbols
    assert "OK" in symbols


def test_normalize_focus_etf_list_order_and_dedupe() -> None:
    assert normalize_focus_etf_list(["spy", "QQQ", "spy"]) == ["SPY", "QQQ"]


def test_parse_holdings_rows() -> None:
    raw = [
        {"symbol": "AAPL", "weightPercentage": 5, "marketValue": 1e9},
        {"symbol": "AAPL", "weightPercentage": 6, "marketValue": 2e9},
        {"symbol": "MSFT", "weightPercentage": 4, "marketValue": 1e9},
    ]
    rows = _parse_holdings_rows(raw)
    assert len(rows) == 2
    by_sym = {r["equitySymbol"]: r["weightPercentage"] for r in rows}
    assert by_sym["AAPL"] == 6


def test_parse_holdings_rows_fmp_stable_uses_asset_not_fund_symbol() -> None:
    """FMP stable: `symbol` is the ETF; constituents are in `asset`."""
    raw = [
        {
            "symbol": "SPY",
            "asset": "AAPL",
            "weightPercentage": 6.679,
            "marketValue": 4.3e10,
        },
        {
            "symbol": "SPY",
            "asset": "MSFT",
            "weightPercentage": 4.844,
            "marketValue": 3.1e10,
        },
    ]
    rows = _parse_holdings_rows(raw)
    syms = {r["equitySymbol"] for r in rows}
    assert syms == {"AAPL", "MSFT"}
    assert "SPY" not in syms


def test_holding_equity_symbol_precedence() -> None:
    assert _holding_equity_symbol({"asset": "X", "symbol": "FUND", "ticker": "T"}) == "X"
    assert _holding_equity_symbol({"symbol": "QQQ", "weightPercentage": 1}) == "QQQ"


def test_build_focus_etf_row_from_holdings() -> None:
    holdings = _parse_holdings_rows(
        [
            {"symbol": "NVDA", "weightPercentage": 8, "marketValue": 8e8},
            {"symbol": "AMD", "weightPercentage": 3, "marketValue": 3e8},
        ]
    )
    row = build_focus_etf_row_from_holdings("MYETF", holdings, ["NVDA", "TSLA"])
    assert row["etfSymbol"] == "MYETF"
    assert row["themeScore"] == 8.0
    assert row["matchCount"] == 1
    assert row["matchedTickers"] == ["NVDA"]
    assert row["totalTickers"] == 2


def test_apply_etf_symbol_filter_case_insensitive() -> None:
    etfs = [
        {"etfSymbol": "SPY", "themeScore": 10, "matchCount": 2, "rank": 1},
        {"etfSymbol": "QQQ", "themeScore": 8, "matchCount": 2, "rank": 2},
    ]
    filtered, warnings = apply_etf_symbol_filter(etfs, ["spy"])
    assert len(filtered) == 1
    assert filtered[0]["etfSymbol"] == "SPY"
    assert filtered[0]["rank"] == 1
    assert warnings == []


def test_apply_etf_symbol_filter_no_overlap_warning() -> None:
    etfs = [{"etfSymbol": "SPY", "themeScore": 10, "matchCount": 2, "rank": 1}]
    filtered, warnings = apply_etf_symbol_filter(etfs, ["IWM"])
    assert filtered == []
    assert warnings
