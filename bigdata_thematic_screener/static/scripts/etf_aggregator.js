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

    return data
        .map(item => {
            const wp = parseFloat(item.weightPercentage) || 0;
            return {
                etfSymbol: item.etfSymbol || item.symbol || '',
                weightPercentage: (wp > 0 && wp <= 100) ? wp : 0,
                marketValue: parseFloat(item.marketValue) || 0,
            };
        })
        .filter(item => item.etfSymbol && item.weightPercentage > 0);
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
 * Groups by fingerprint (matchCount + rounded themeScore + rounded estAum),
 * keeps the primary listing: prefers symbols without dots (US tickers), then shortest.
 */
function deduplicateEtfs(etfs) {
    const groups = new Map();
    etfs.forEach(etf => {
        const key = `${etf.matchCount}_${etf.themeScore.toFixed(4)}_${Math.round(etf.estAum / 1e6)}`;
        if (!groups.has(key)) {
            groups.set(key, []);
        }
        groups.get(key).push(etf);
    });

    return Array.from(groups.values()).map(group => {
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

/**
 * Aggregate ETF exposure across multiple tickers.
 * Filters: matchCount >= minMatchCount, estAum >= MIN_AUM.
 * Deduplicates cross-listed ETFs.
 */
function aggregateEtfExposure(tickerResults, topK = 10, minMatchCount = 2) {
    const etfMap = new Map();
    const totalTickers = tickerResults.length;

    tickerResults.forEach(({ exposures }) => {
        if (!Array.isArray(exposures)) return;
        exposures.forEach(({ etfSymbol, weightPercentage, marketValue }) => {
            if (!etfSymbol) return;
            if (!etfMap.has(etfSymbol)) {
                etfMap.set(etfSymbol, {
                    etfSymbol,
                    themeScore: 0,
                    matchCount: 0,
                    totalMarketValue: 0,
                    totalWeight: 0,
                });
            }
            const entry = etfMap.get(etfSymbol);
            entry.themeScore += weightPercentage;
            entry.matchCount += 1;
            entry.totalMarketValue += marketValue;
            entry.totalWeight += weightPercentage;
        });
    });

    let etfArray = Array.from(etfMap.values())
        .map(etf => ({
            etfSymbol: etf.etfSymbol,
            themeScore: etf.themeScore,
            matchCount: etf.matchCount,
            totalTickers,
            avgWeight: etf.matchCount > 0 ? etf.themeScore / etf.matchCount : 0,
            estAum: etf.totalWeight > 0 ? (etf.totalMarketValue / etf.totalWeight) * 100 : 0,
        }))
        .filter(etf => etf.matchCount >= minMatchCount && etf.estAum >= MIN_AUM)
        .sort((a, b) => b.themeScore - a.themeScore);

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
    return aggregateEtfExposure(tickerResults, topK);
}
