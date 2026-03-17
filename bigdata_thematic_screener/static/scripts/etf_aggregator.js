// ETF Aggregator — pure utility for fetching and aggregating ETF exposure data

/**
 * Fetch ETF asset exposure for a single ticker from FMP API.
 * Validates weightPercentage: a single holding can never exceed 100% of a fund,
 * so values above 100 indicate bad data (usually market values leaked into the field).
 */
async function fetchEtfExposure(ticker, apiKey) {
    const url = `https://financialmodelingprep.com/stable/etf/asset-exposure?symbol=${encodeURIComponent(ticker)}&apikey=${encodeURIComponent(apiKey)}`;
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`FMP API error for ${ticker}: ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    if (!Array.isArray(data)) return [];

    const items = data
        .map(item => {
            const rawSymbol = (item.etfSymbol || item.symbol || '').trim().toUpperCase();
            const wp = parseFloat(item.weightPercentage) || 0;
            return {
                etfSymbol: rawSymbol,
                weightPercentage: (wp > 0 && wp <= 100) ? wp : 0,
                marketValue: parseFloat(item.marketValue) || 0,
            };
        })
        .filter(item => item.etfSymbol && item.weightPercentage > 0);

    const beforeCount = items.length;
    // Deduplicate: FMP can return multiple rows for the same ETF per ticker.
    // Keep the entry with the highest weightPercentage to avoid inflating scores.
    const deduped = new Map();
    items.forEach(item => {
        const existing = deduped.get(item.etfSymbol);
        if (!existing || item.weightPercentage > existing.weightPercentage) {
            deduped.set(item.etfSymbol, item);
        }
    });
    const result = Array.from(deduped.values());
    if (result.length < beforeCount) {
        console.debug(`[ETF Fetch] ${ticker}: deduped ${beforeCount} → ${result.length} entries (removed ${beforeCount - result.length} duplicates)`);
    }
    return result;
}

/**
 * Fetch ETF exposure for a batch of tickers with a delay between batches
 * to avoid FMP rate limits.
 */
async function fetchEtfExposureBatched(tickers, apiKey, batchSize = 5, delayMs = 200) {
    const results = [];
    for (let i = 0; i < tickers.length; i += batchSize) {
        const batch = tickers.slice(i, i + batchSize);
        const batchResults = await Promise.all(
            batch.map(ticker => fetchEtfExposure(ticker, apiKey).catch(err => {
                console.warn(`ETF fetch failed for ${ticker}:`, err.message);
                return [];
            }))
        );
        batch.forEach((ticker, idx) => {
            results.push({ ticker, exposures: batchResults[idx] });
        });
        if (i + batchSize < tickers.length) {
            await new Promise(resolve => setTimeout(resolve, delayMs));
        }
    }
    return results;
}

const MIN_AUM = 100_000_000; // $100M

/**
 * Deduplicate cross-listed ETFs (same fund on different exchanges).
 * Two ETFs are considered duplicates when they share the same matchCount,
 * similar themeScore (within 1%), and similar estAum (within 20%).
 * Keeps the primary listing: prefers symbols without dots (US tickers), then shortest.
 */
function deduplicateEtfs(etfs) {
    const groups = [];

    etfs.forEach(etf => {
        let placed = false;
        for (const group of groups) {
            const ref = group[0];
            if (ref.matchCount !== etf.matchCount) continue;
            const scoreDiff = Math.abs(ref.themeScore - etf.themeScore);
            if (scoreDiff > Math.max(ref.themeScore, etf.themeScore) * 0.01) continue;
            const aumRatio = ref.estAum > 0 && etf.estAum > 0
                ? Math.max(ref.estAum, etf.estAum) / Math.min(ref.estAum, etf.estAum)
                : Infinity;
            if (aumRatio > 1.2) continue;
            group.push(etf);
            placed = true;
            break;
        }
        if (!placed) groups.push([etf]);
    });

    return groups.map(group => {
        group.sort((a, b) => {
            const aDot = a.etfSymbol.includes('.') ? 1 : 0;
            const bDot = b.etfSymbol.includes('.') ? 1 : 0;
            if (aDot !== bDot) return aDot - bDot;
            return a.etfSymbol.length - b.etfSymbol.length;
        });
        const primary = group[0];
        if (group.length > 1) {
            primary.aliases = group.slice(1).map(e => e.etfSymbol);
        }
        return primary;
    });
}

function formatAumDebug(v) {
    if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
    if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
    return v.toFixed(0);
}

/**
 * Check whether per-holding AUM estimates are consistent.
 * For a legitimate ETF, every holding should imply roughly the same total AUM
 * because AUM = marketValue / (weight/100). If the ratio between the highest
 * and lowest estimate exceeds MAX_AUM_SPREAD, the underlying data is unreliable
 * (e.g. FMP returning holdings that don't actually belong to the fund).
 */
const MAX_AUM_SPREAD = 5;

function isAumConsistent(estimates) {
    if (!estimates || estimates.length < 2) return true;
    const sorted = [...estimates].sort((a, b) => a - b);
    const lo = sorted[0];
    const hi = sorted[sorted.length - 1];
    if (lo <= 0) return false;
    return (hi / lo) <= MAX_AUM_SPREAD;
}

/**
 * Aggregate ETF exposure across multiple tickers.
 * Filters: matchCount >= minMatchCount, estAum >= MIN_AUM, AUM consistency.
 * Deduplicates cross-listed ETFs.
 */
function aggregateEtfExposure(tickerResults, topK = 10, minMatchCount = 2) {
    const etfMap = new Map();
    const totalTickers = tickerResults.length;

    tickerResults.forEach(({ ticker, exposures }) => {
        if (!Array.isArray(exposures)) return;
        exposures.forEach(({ etfSymbol, weightPercentage, marketValue }) => {
            if (!etfSymbol) return;
            if (!etfMap.has(etfSymbol)) {
                etfMap.set(etfSymbol, {
                    etfSymbol,
                    themeScore: 0,
                    matchCount: 0,
                    matchedTickers: [],
                    _tickerSet: new Set(),
                    _contributions: [],
                    _aumEstimates: [],
                    totalMarketValue: 0,
                    totalWeight: 0,
                });
            }
            const entry = etfMap.get(etfSymbol);
            entry.themeScore += weightPercentage;
            entry.totalMarketValue += marketValue;
            entry.totalWeight += weightPercentage;
            entry._contributions.push({ ticker, weightPercentage, marketValue });
            if (weightPercentage > 0 && marketValue > 0) {
                entry._aumEstimates.push(marketValue / (weightPercentage / 100));
            }
            if (!entry._tickerSet.has(ticker)) {
                entry._tickerSet.add(ticker);
                entry.matchCount += 1;
                entry.matchedTickers.push(ticker);
            }
        });
    });

    // Log detailed contributions for top ETFs to help diagnose scoring
    const topByScore = Array.from(etfMap.values())
        .sort((a, b) => b.themeScore - a.themeScore)
        .slice(0, 20);
    topByScore.forEach(etf => {
        if (etf.matchCount >= minMatchCount) {
            console.debug(
                `[ETF Aggregate] ${etf.etfSymbol}: score=${etf.themeScore.toFixed(2)}% match=${etf.matchCount}`,
                etf._contributions.map(c => `${c.ticker}→${c.weightPercentage.toFixed(3)}%`).join(', ')
            );
        }
    });

    let etfArray = Array.from(etfMap.values())
        .map(etf => ({
            etfSymbol: etf.etfSymbol,
            themeScore: etf.themeScore,
            matchCount: etf.matchCount,
            matchedTickers: etf.matchedTickers,
            totalTickers,
            estAum: etf.totalWeight > 0 ? (etf.totalMarketValue / etf.totalWeight) * 100 : 0,
            _aumEstimates: etf._aumEstimates,
        }))
        .filter(etf => {
            if (etf.matchCount < minMatchCount) return false;
            if (etf.estAum < MIN_AUM) return false;
            if (!isAumConsistent(etf._aumEstimates)) {
                console.debug(`ETF ${etf.etfSymbol} excluded: inconsistent AUM estimates`, etf._aumEstimates.map(a => formatAumDebug(a)));
                return false;
            }
            return true;
        })
        .sort((a, b) => b.themeScore - a.themeScore);

    etfArray.forEach(etf => delete etf._aumEstimates);

    etfArray = deduplicateEtfs(etfArray);

    etfArray = etfArray.slice(0, topK);
    etfArray.forEach((etf, idx) => {
        etf.rank = idx + 1;
    });

    return etfArray;
}

/**
 * Full ETF pipeline: take ranked companies from state, fetch exposures, aggregate.
 */
async function runEtfPipeline(themeScoring, apiKey, topN = 10, topK = 10) {
    if (!themeScoring || typeof themeScoring !== 'object') {
        throw new Error('No company scoring data available. Run an analysis first.');
    }
    if (!apiKey) {
        throw new Error('FMP API key is not configured. Set the FMP_API_KEY environment variable.');
    }

    const companies = Object.entries(themeScoring)
        .map(([name, scoring]) => ({
            name,
            ticker: scoring.ticker,
            score: scoring.composite_score || 0,
        }))
        .sort((a, b) => b.score - a.score)
        .slice(0, topN);

    const tickers = companies.map(c => c.ticker).filter(Boolean);
    if (tickers.length === 0) {
        throw new Error('No valid tickers found in the top companies.');
    }

    const tickerResults = await fetchEtfExposureBatched(tickers, apiKey);

    console.debug('[ETF Pipeline] Tickers:', tickers);
    tickerResults.forEach(({ ticker, exposures }) => {
        console.debug(`[ETF Pipeline] ${ticker}: ${exposures.length} ETFs found`);
    });

    const results = aggregateEtfExposure(tickerResults, topK);
    console.debug('[ETF Pipeline] Final results:', results.map(r => `${r.rank}. ${r.etfSymbol} score=${r.themeScore.toFixed(2)}% match=${r.matchCount}/${tickers.length}`));
    return results;
}
