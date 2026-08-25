"""Server-side FMP ETF asset-exposure fetch + aggregation (formerly client-side etf_aggregator.js)."""

from __future__ import annotations

import time
from typing import Any, TypeAlias

import httpx

from bigdata_thematic_screener import logger
from bigdata_thematic_screener.api.models import TickersBasketMode

FMP_ASSET_EXPOSURE_URL = "https://financialmodelingprep.com/stable/etf/asset-exposure"
FMP_ETF_HOLDINGS_URL = "https://financialmodelingprep.com/stable/etf/holdings"
MIN_AUM = 100_000_000
MAX_AUM_SPREAD = 5
DEFAULT_MIN_MATCH_COUNT = 2
BATCH_SIZE = 5
DELAY_MS = 200
MAX_BASKET_TICKERS = 40
# Cap ranked rows before slicing to top_k (limits memory on pathological FMP payloads).
MAX_AGGREGATE_CANDIDATES = 300
MAX_THEME_CONCENTRATION_PCT = 100.0

RawExposure: TypeAlias = dict[str, Any]


def normalize_symbol(raw: str) -> str:
    s = raw.strip().upper()
    return s


def resolve_ticker_basket(
    theme_scoring: dict[str, Any],
    top_n: int,
    extra_tickers: list[str],
    max_total: int = MAX_BASKET_TICKERS,
    tickers_mode: TickersBasketMode = TickersBasketMode.merge,
) -> tuple[list[str], list[str]]:
    """Build equity basket: merge = top_n from scoring then Tickers; only = Tickers alone."""
    warnings: list[str] = []
    if tickers_mode == TickersBasketMode.only:
        ordered_only: list[str] = []
        seen_only: set[str] = set()
        for raw in extra_tickers:
            sym = normalize_symbol(str(raw))
            if not sym or sym in seen_only:
                continue
            seen_only.add(sym)
            ordered_only.append(sym)
        if len(ordered_only) > max_total:
            warnings.append(
                f"Ticker basket capped at {max_total} symbols; truncated {len(ordered_only) - max_total}"
            )
            ordered_only = ordered_only[:max_total]
        if not ordered_only:
            warnings.append(
                "Add at least one symbol in Tickers when using Only this mode."
            )
        return ordered_only, warnings

    if not theme_scoring:
        return [], ["theme_scoring is empty"]

    companies: list[tuple[str, float]] = []
    for _name, scoring in theme_scoring.items():
        if not isinstance(scoring, dict):
            continue
        ticker = scoring.get("ticker")
        if not ticker or not str(ticker).strip():
            continue
        score = float(scoring.get("composite_score") or 0)
        companies.append((str(ticker), score))

    companies.sort(key=lambda x: x[1], reverse=True)
    ordered: list[str] = []
    seen: set[str] = set()
    for t, _s in companies[:top_n]:
        sym = normalize_symbol(t)
        if sym and sym not in seen:
            seen.add(sym)
            ordered.append(sym)

    for raw in extra_tickers:
        sym = normalize_symbol(str(raw))
        if not sym or sym in seen:
            continue
        seen.add(sym)
        ordered.append(sym)

    if len(ordered) > max_total:
        warnings.append(
            f"Ticker basket capped at {max_total} symbols; truncated {len(ordered) - max_total}"
        )
        ordered = ordered[:max_total]

    if not ordered:
        warnings.append("No valid tickers in theme_scoring or extra_tickers")

    return ordered, warnings


def _parse_fmp_rows(data: Any) -> list[RawExposure]:
    if not isinstance(data, list):
        return []
    items: list[RawExposure] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_symbol = (item.get("etfSymbol") or item.get("symbol") or "").strip().upper()
        wp = float(item.get("weightPercentage") or 0)
        if wp <= 0 or wp > 100:
            continue
        mv = float(item.get("marketValue") or 0)
        items.append(
            {
                "etfSymbol": raw_symbol,
                "weightPercentage": wp,
                "marketValue": mv,
            }
        )
    deduped: dict[str, RawExposure] = {}
    for it in items:
        sym = it["etfSymbol"]
        if not sym:
            continue
        existing = deduped.get(sym)
        if not existing or it["weightPercentage"] > existing["weightPercentage"]:
            deduped[sym] = it
    return list(deduped.values())


def fetch_asset_exposure_for_ticker(
    client: httpx.Client, ticker: str, api_key: str
) -> list[RawExposure]:
    response = client.get(
        FMP_ASSET_EXPOSURE_URL,
        params={"symbol": ticker, "apikey": api_key},
        timeout=30.0,
    )
    response.raise_for_status()
    return _parse_fmp_rows(response.json())


def normalize_focus_etf_list(symbols: list[str]) -> list[str]:
    """Dedupe ETF symbols preserving first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        sym = normalize_symbol(str(raw))
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def _holding_equity_symbol(item: dict[str, Any]) -> str:
    """
    Underlying security ticker for one holdings row.

    FMP stable `/etf/holdings` uses `symbol` for the fund (e.g. SPY) and `asset` for
    each constituent (e.g. AAPL). Older/alternate payloads may put the stock in
    `symbol` or `ticker` only.
    """
    for key in ("asset", "ticker", "symbol"):
        raw = item.get(key)
        if raw is None:
            continue
        s = str(raw).strip().upper()
        if s:
            return s
    return ""


def _parse_holdings_rows(data: Any) -> list[dict[str, Any]]:
    """Parse FMP ETF holdings: equity line items with weight in the fund."""
    if not isinstance(data, list):
        return []
    items: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        sym = _holding_equity_symbol(item)
        wp = float(
            item.get("weightPercentage")
            or item.get("holdingPercent")
            or item.get("weight")
            or 0
        )
        mv = float(item.get("marketValue") or 0)
        if not sym or wp <= 0 or wp > 100:
            continue
        items.append({"equitySymbol": sym, "weightPercentage": wp, "marketValue": mv})
    deduped: dict[str, dict[str, Any]] = {}
    for it in items:
        es = it["equitySymbol"]
        existing = deduped.get(es)
        if not existing or it["weightPercentage"] > existing["weightPercentage"]:
            deduped[es] = it
    return list(deduped.values())


def fetch_etf_holdings(
    client: httpx.Client, etf_symbol: str, api_key: str
) -> list[dict[str, Any]]:
    response = client.get(
        FMP_ETF_HOLDINGS_URL,
        params={"symbol": normalize_symbol(etf_symbol), "apikey": api_key},
        timeout=30.0,
    )
    response.raise_for_status()
    return _parse_holdings_rows(response.json())


def build_focus_etf_row_from_holdings(
    etf_symbol: str,
    holdings: list[dict[str, Any]],
    basket: list[str],
) -> dict[str, Any]:
    """Theme score = sum of holding weights for equities in the basket."""
    basket_set = {normalize_symbol(x) for x in basket}
    theme_score = 0.0
    matched: list[str] = []
    matched_set: set[str] = set()
    total_mv = 0.0
    total_w = 0.0
    aum_estimates: list[float] = []
    for h in holdings:
        hsym = h["equitySymbol"]
        if hsym not in basket_set:
            continue
        wp = float(h["weightPercentage"])
        mv = float(h["marketValue"])
        theme_score += wp
        total_mv += mv
        total_w += wp
        if wp > 0 and mv > 0:
            aum_estimates.append(mv / (wp / 100.0))
        if hsym not in matched_set:
            matched_set.add(hsym)
            matched.append(hsym)
    est_aum = (total_mv / total_w) * 100 if total_w > 0 else 0.0
    return {
        "etfSymbol": normalize_symbol(etf_symbol),
        "themeScore": theme_score,
        "matchCount": len(matched_set),
        "matchedTickers": matched,
        "totalTickers": len(basket),
        "estAum": est_aum,
        "_aum_estimates": aum_estimates,
    }


def run_focus_etf_holdings_pipeline(
    client: httpx.Client,
    api_key: str,
    basket: list[str],
    focus_etf_symbols: list[str],
    top_k: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Score only the given ETF symbols by summing portfolio weights on basket names.
    Every listed symbol gets a row (scores may be zero if holdings missing or no overlap).
    """
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    for i, etf_sym in enumerate(focus_etf_symbols):
        if i > 0:
            time.sleep(DELAY_MS / 1000.0)
        try:
            holdings = fetch_etf_holdings(client, etf_sym, api_key)
        except Exception as e:
            logger.warning("fmp_etf_holdings_failed", etf=etf_sym, error=str(e))
            warnings.append(f"Could not load holdings for {etf_sym}.")
            holdings = []
        row = build_focus_etf_row_from_holdings(etf_sym, holdings, basket)
        if row["themeScore"] > MAX_THEME_CONCENTRATION_PCT:
            warnings.append(
                f"Excluded {row['etfSymbol']}: theme concentration over 100%."
            )
            continue
        estimates = row.get("_aum_estimates") or []
        if len(estimates) >= 2 and not _is_aum_consistent(estimates):
            warnings.append(
                f"Excluded {row['etfSymbol']}: inconsistent AUM from holdings."
            )
            continue
        row.pop("_aum_estimates", None)
        rows.append(row)
    rows.sort(key=lambda x: x["themeScore"], reverse=True)
    rows = rows[:top_k]
    for idx, r in enumerate(rows):
        r["rank"] = idx + 1
        r["aliases"] = None
    return rows, warnings


def fetch_asset_exposure_batched(
    client: httpx.Client,
    tickers: list[str],
    api_key: str,
    batch_size: int = BATCH_SIZE,
    delay_ms: int = DELAY_MS,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        for ticker in batch:
            try:
                exposures = fetch_asset_exposure_for_ticker(client, ticker, api_key)
            except Exception as e:
                logger.warning("fmp_fetch_failed", ticker=ticker, error=str(e))
                exposures = []
            results.append({"ticker": ticker, "exposures": exposures})
        if i + batch_size < len(tickers):
            time.sleep(delay_ms / 1000.0)
    return results


def _is_aum_consistent(estimates: list[float]) -> bool:
    if not estimates or len(estimates) < 2:
        return True
    sorted_est = sorted(estimates)
    lo, hi = sorted_est[0], sorted_est[-1]
    if lo <= 0:
        return False
    return (hi / lo) <= MAX_AUM_SPREAD


def deduplicate_etfs(etfs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    for etf in etfs:
        placed = False
        for group in groups:
            ref = group[0]
            if ref["matchCount"] != etf["matchCount"]:
                continue
            score_diff = abs(ref["themeScore"] - etf["themeScore"])
            max_score = max(ref["themeScore"], etf["themeScore"])
            if max_score > 0 and score_diff > max_score * 0.01:
                continue
            a_r, a_e = ref["estAum"], etf["estAum"]
            aum_ratio = (
                max(a_r, a_e) / min(a_r, a_e) if a_r > 0 and a_e > 0 else float("inf")
            )
            if aum_ratio > 1.2:
                continue
            group.append(etf)
            placed = True
            break
        if not placed:
            groups.append([etf])

    primaries: list[dict[str, Any]] = []
    for group in groups:
        group.sort(
            key=lambda x: (
                1 if "." in x["etfSymbol"] else 0,
                len(x["etfSymbol"]),
            )
        )
        primary = {**group[0]}
        if len(group) > 1:
            primary["aliases"] = [e["etfSymbol"] for e in group[1:]]
        else:
            primary["aliases"] = None
        primaries.append(primary)
    return primaries


def aggregate_etf_exposure(
    ticker_results: list[dict[str, Any]],
    min_match_count: int = DEFAULT_MIN_MATCH_COUNT,
    max_candidates: int = MAX_AGGREGATE_CANDIDATES,
) -> list[dict[str, Any]]:
    etf_map: dict[str, dict[str, Any]] = {}
    total_tickers = len(ticker_results)

    for tr in ticker_results:
        ticker = tr["ticker"]
        exposures = tr.get("exposures") or []
        if not isinstance(exposures, list):
            continue
        for ex in exposures:
            if not isinstance(ex, dict):
                continue
            etf_symbol = ex.get("etfSymbol")
            if not etf_symbol:
                continue
            wp = float(ex.get("weightPercentage") or 0)
            mv = float(ex.get("marketValue") or 0)
            if etf_symbol not in etf_map:
                etf_map[etf_symbol] = {
                    "etfSymbol": etf_symbol,
                    "themeScore": 0.0,
                    "matchCount": 0,
                    "matchedTickers": [],
                    "_ticker_set": set(),
                    "_aum_estimates": [],
                    "totalMarketValue": 0.0,
                    "totalWeight": 0.0,
                }
            entry = etf_map[etf_symbol]
            entry["themeScore"] += wp
            entry["totalMarketValue"] += mv
            entry["totalWeight"] += wp
            if wp > 0 and mv > 0:
                entry["_aum_estimates"].append(mv / (wp / 100.0))
            if ticker not in entry["_ticker_set"]:
                entry["_ticker_set"].add(ticker)
                entry["matchCount"] += 1
                entry["matchedTickers"].append(ticker)

    etf_array: list[dict[str, Any]] = []
    for etf in etf_map.values():
        total_w = etf["totalWeight"]
        est_aum = (etf["totalMarketValue"] / total_w) * 100 if total_w > 0 else 0.0
        estimates: list[float] = etf["_aum_estimates"]
        if etf["matchCount"] < min_match_count:
            continue
        if est_aum < MIN_AUM:
            continue
        if not _is_aum_consistent(estimates):
            continue
        if etf["themeScore"] > MAX_THEME_CONCENTRATION_PCT:
            continue
        etf_array.append(
            {
                "etfSymbol": etf["etfSymbol"],
                "themeScore": etf["themeScore"],
                "matchCount": etf["matchCount"],
                "matchedTickers": list(etf["matchedTickers"]),
                "totalTickers": total_tickers,
                "estAum": est_aum,
            }
        )

    etf_array.sort(key=lambda x: x["themeScore"], reverse=True)
    etf_array = deduplicate_etfs(etf_array)
    etf_array = etf_array[:max_candidates]
    return etf_array


def apply_etf_symbol_filter(
    etfs: list[dict[str, Any]], symbols_filter: list[str] | None
) -> tuple[list[dict[str, Any]], list[str]]:
    if not symbols_filter:
        return etfs, []
    allow = {normalize_symbol(s) for s in symbols_filter if normalize_symbol(s)}
    if not allow:
        return etfs, []
    filtered = [e for e in etfs if normalize_symbol(e["etfSymbol"]) in allow]
    warnings: list[str] = []
    if not filtered and etfs:
        warnings.append("No ETFs matched the focus list for this equity basket.")
    for i, e in enumerate(filtered):
        e["rank"] = i + 1
    return filtered, warnings


def run_etf_exposure_pipeline(
    theme_scoring: dict[str, Any],
    top_n: int,
    top_k: int,
    api_key: str,
    extra_tickers: list[str],
    etf_symbols_filter: list[str] | None,
    tickers_mode: TickersBasketMode = TickersBasketMode.merge,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    """Returns (etf dicts for response model, total_tickers_used, all warnings)."""
    all_warnings: list[str] = []
    tickers, basket_warnings = resolve_ticker_basket(
        theme_scoring, top_n, extra_tickers, tickers_mode=tickers_mode
    )
    all_warnings.extend(basket_warnings)
    if not tickers:
        return [], 0, all_warnings

    close_client = False
    if client is None:
        client = httpx.Client()
        close_client = True
    try:
        focus_list = normalize_focus_etf_list(etf_symbols_filter or [])
        had_focus_input = bool(
            etf_symbols_filter and any(str(s).strip() for s in etf_symbols_filter)
        )
        if focus_list:
            etfs, focus_warnings = run_focus_etf_holdings_pipeline(
                client, api_key, tickers, focus_list, top_k
            )
            all_warnings.extend(focus_warnings)
        else:
            if had_focus_input:
                all_warnings.append(
                    "Focus ETFs had no valid symbols; running full discovery instead."
                )
            ticker_results = fetch_asset_exposure_batched(client, tickers, api_key)
            etfs = aggregate_etf_exposure(ticker_results)
            etfs = etfs[:top_k]
            for idx, etf in enumerate(etfs):
                etf["rank"] = idx + 1
        for etf in etfs:
            etf.setdefault("aliases", None)
        return etfs, len(tickers), all_warnings
    finally:
        if close_client:
            client.close()
