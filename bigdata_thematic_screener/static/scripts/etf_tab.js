// ETF Tab — UI controls, results table, methodology modal

let etfResults = [];
let etfThemeScoring = null;

function formatCurrency(value) {
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(1) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(1) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(1) + 'M';
    if (value >= 1e3) return '$' + (value / 1e3).toFixed(1) + 'K';
    return '$' + value.toFixed(0);
}

function getScoreColor(score, maxScore) {
    if (score <= 0 || maxScore <= 0) return { bg: 'bg-zinc-800', text: 'text-zinc-500', barColor: '#3f3f46' };
    const intensity = score / maxScore;
    const shades = [
        { threshold: 0.2, bg: 'bg-emerald-900', text: 'text-emerald-300', barColor: '#064e3b' },
        { threshold: 0.4, bg: 'bg-emerald-800', text: 'text-emerald-200', barColor: '#065f46' },
        { threshold: 0.6, bg: 'bg-emerald-700', text: 'text-emerald-100', barColor: '#047857' },
        { threshold: 0.8, bg: 'bg-emerald-600', text: 'text-white', barColor: '#059669' },
        { threshold: 1.0, bg: 'bg-emerald-500', text: 'text-white', barColor: '#10b981' },
    ];
    for (const shade of shades) {
        if (intensity <= shade.threshold) return shade;
    }
    return shades[shades.length - 1];
}

function etfYahooUrl(symbol) {
    return `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/holdings/`;
}

function getThemeScoring() {
    if (etfThemeScoring) return etfThemeScoring;
    if (window.lastReport && window.lastReport.theme_scoring) return window.lastReport.theme_scoring;
    return null;
}

/** Comma or newline separated symbols for optional inputs */
function parseSymbolsFromInput(raw) {
    if (!raw || typeof raw !== 'string') return [];
    const parts = raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean);
    return parts;
}

function buildEtfExposureApiUrl() {
    const params = new URLSearchParams();
    const pageParams = new URLSearchParams(window.location.search);
    const token = pageParams.get('token');
    if (token) params.append('token', token);
    const qs = params.toString();
    return qs ? `/api/etf-exposure?${qs}` : '/api/etf-exposure';
}

function renderEtfTab(themeScoring) {
    const container = document.querySelector('[data-tab-content="etfs"] .tab-actual-content');
    if (!container) return;

    if (themeScoring) {
        etfThemeScoring = themeScoring;
    }

    const scoring = getThemeScoring();
    const fmpEnabled = window.__FMP_ETF_LOOKUP_ENABLED__ === true;
    const hasReport = scoring && typeof scoring === 'object' && Object.keys(scoring).length > 0;
    const companyCount = hasReport ? Object.keys(scoring).length : 0;
    const defaultTopN = Math.min(10, companyCount || 10);

    let html = `
        <div class="mb-6">
            <div class="flex justify-between items-start mb-4">
                <div>
                    <h3 class="text-2xl font-bold text-white mb-1 flex items-center gap-2">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                        </svg>
                        Top Thematic ETFs
                    </h3>
                    <p class="text-zinc-400 text-sm">
                        ETFs most concentrated in your thematic basket, ranked by cumulative weight exposure
                        · <a href="#" onclick="showEtfMethodologyModal(); return false;" class="text-blue-400 hover:text-blue-300 underline">How it works</a>
                    </p>
                </div>
            </div>

            <!-- Controls Row -->
            <div class="bg-zinc-800/50 rounded-lg border border-zinc-700 p-4 mb-4">
                <div class="flex flex-wrap items-end gap-4">
                    <div>
                        <label class="block text-sm font-medium text-zinc-300 mb-2">Top tickers</label>
                        <input type="number" id="etfTopN" value="${defaultTopN}" min="1" max="${companyCount || 50}"
                            class="w-24 px-3 py-2 bg-zinc-900 border border-zinc-600 rounded-lg text-zinc-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                            ${!hasReport ? 'disabled' : ''}>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-zinc-300 mb-2">Show top ETFs</label>
                        <input type="number" id="etfTopK" value="10" min="1" max="50"
                            class="w-24 px-3 py-2 bg-zinc-900 border border-zinc-600 rounded-lg text-zinc-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                            ${!hasReport ? 'disabled' : ''}>
                    </div>
                </div>
                <details class="mt-5 border-t border-zinc-700 pt-4 open:[&_summary>svg]:rotate-90">
                    <summary class="flex cursor-pointer list-none items-center gap-2 text-sm font-medium text-zinc-200 select-none hover:text-white [&::-webkit-details-marker]:hidden">
                        <svg class="h-4 w-4 shrink-0 text-zinc-500 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                        Optional lists — Tickers &amp; Focus ETFs
                    </summary>
                    <div class="mt-3 space-y-4 pb-1">
                        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <div>
                                <div class="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                                    <span class="font-medium text-zinc-300">Tickers</span>
                                    <span class="font-normal text-zinc-500">(</span>
                                    <label class="inline-flex cursor-pointer items-center gap-2 font-normal text-zinc-300">
                                        <input type="radio" name="etfTickersMode" value="merge" class="text-blue-500" checked ${!hasReport ? 'disabled' : ''}>
                                        <span>Merge</span>
                                    </label>
                                    <span class="font-normal text-zinc-500">/</span>
                                    <label class="inline-flex cursor-pointer items-center gap-2 font-normal text-zinc-300">
                                        <input type="radio" name="etfTickersMode" value="only" class="text-blue-500" ${!hasReport ? 'disabled' : ''}>
                                        <span>Only this</span>
                                    </label>
                                    <span class="font-normal text-zinc-500">)</span>
                                </div>
                                <textarea id="etfTickersInput" rows="2" placeholder="e.g. AAPL, MSFT"
                                    class="min-h-[2.5rem] w-full resize-y rounded-lg border border-zinc-600 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                                    ${!hasReport ? 'disabled' : ''}></textarea>
                                <p id="etfTickersHint" class="mt-1 text-xs text-zinc-500">Merge: combined with top N from the report. Only this: basket is only symbols here (Top tickers N is ignored).</p>
                            </div>
                            <div>
                                <label class="mb-2 block text-sm font-medium text-zinc-300">Focus ETFs (optional)</label>
                                <textarea id="etfFocusSymbols" rows="2" placeholder="e.g. SPY, QQQ"
                                    class="min-h-[2.5rem] w-full resize-y rounded-lg border border-zinc-600 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                                    ${!hasReport ? 'disabled' : ''}></textarea>
                                <p class="mt-1 text-xs text-zinc-500">If set, results are <strong>only</strong> these funds: each is scored from its holdings vs your equity basket (e.g. compare your firm’s ETFs on theme exposure). Leave blank to discover ETFs from the basket instead.</p>
                            </div>
                        </div>
                        ${hasReport ? `<div class="text-sm text-zinc-500">${companyCount} companies in report · <span class="text-zinc-600">Merge: top tickers + Tickers field. Only this: Tickers field only.</span></div>` : ''}
                    </div>
                </details>`;

    let alertStatusInner = '';
    if (!fmpEnabled) {
        alertStatusInner = `
                    <div class="flex items-center gap-2 text-sm text-amber-400">
                        <svg class="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                        </svg>
                        <span>ETF lookup is disabled on the server. Set <code class="rounded bg-zinc-700 px-1 text-xs">FMP_API_KEY</code> on the service (never sent to the browser).</span>
                    </div>`;
    } else if (!hasReport) {
        alertStatusInner = `
                    <div class="flex items-center gap-2 text-sm text-zinc-500">
                        <svg class="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <span>Run a thematic analysis first to populate the company list.</span>
                    </div>`;
    }

    const findDisabled = !hasReport || !fmpEnabled;
    html += `
                <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <div class="min-w-[14rem] flex-1">${alertStatusInner}</div>
                    <div class="flex-shrink-0">
                        <button type="button" onclick="handleFindEtfs()" id="findEtfsBtn"
                            class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            ${findDisabled ? 'disabled' : ''}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                            Find ETFs
                        </button>
                    </div>
                </div>`;

    html += `
            </div>
        </div>

        <!-- Results container -->
        <div id="etfResultsContainer"></div>
    `;

    container.innerHTML = html;
    wireEtfTickersModeControls(hasReport);
}

function wireEtfTickersModeControls(hasReport) {
    const topNInput = document.getElementById('etfTopN');
    const hint = document.getElementById('etfTickersHint');
    const sync = () => {
        const checked = document.querySelector('input[name="etfTickersMode"]:checked');
        const only = checked && checked.value === 'only';
        if (topNInput) {
            topNInput.disabled = !hasReport || only;
        }
        if (hint) {
            hint.textContent = only
                ? 'Only this: the basket is exactly these symbols (comma or space). Top tickers N is ignored.'
                : 'Merge: these symbols are added after the top N names from the report (deduped).';
        }
    };
    document.querySelectorAll('input[name="etfTickersMode"]').forEach((r) => {
        r.addEventListener('change', sync);
    });
    sync();
}

async function handleFindEtfs() {
    const btn = document.getElementById('findEtfsBtn');
    const resultsContainer = document.getElementById('etfResultsContainer');
    if (!btn || !resultsContainer) return;

    const topN = parseInt(document.getElementById('etfTopN').value) || 10;
    const topK = parseInt(document.getElementById('etfTopK').value) || 10;
    const tickersInput = document.getElementById('etfTickersInput');
    const focusRaw = document.getElementById('etfFocusSymbols');
    const extraTickers = tickersInput ? parseSymbolsFromInput(tickersInput.value) : [];
    const modeRadio = document.querySelector('input[name="etfTickersMode"]:checked');
    const tickersMode = modeRadio && modeRadio.value === 'only' ? 'only' : 'merge';
    const focusList = focusRaw ? parseSymbolsFromInput(focusRaw.value) : [];
    const etfSymbolsFilter = focusList.length > 0 ? focusList : null;
    const scoring = getThemeScoring();

    if (!scoring) {
        resultsContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-red-400">
                <p class="text-lg font-medium">No company data available</p>
                <p class="text-sm text-zinc-400 mt-1">Run a thematic analysis first.</p>
            </div>`;
        return;
    }

    if (tickersMode === 'only' && extraTickers.length === 0) {
        resultsContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-amber-400">
                <p class="text-lg font-medium">Tickers required</p>
                <p class="text-sm text-zinc-400 mt-1">Choose <strong>Only this</strong> and enter at least one symbol in Tickers, or switch to Merge.</p>
            </div>`;
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
        Fetching...`;

    resultsContainer.innerHTML = `
        <div class="flex items-center justify-center py-16">
            <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
            <span class="ml-3 text-zinc-400">Querying ETF exposure on the server…</span>
        </div>`;

    try {
        const response = await fetch(buildEtfExposureApiUrl(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                theme_scoring: scoring,
                top_n: topN,
                top_k: topK,
                extra_tickers: extraTickers,
                tickers_mode: tickersMode,
                etf_symbols_filter: etfSymbolsFilter,
            }),
        });
        if (!response.ok) {
            let detail = response.statusText;
            try {
                const errBody = await response.json();
                if (errBody.detail) {
                    detail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
                }
            } catch (_e) { /* ignore */ }
            throw new Error(detail || `HTTP ${response.status}`);
        }
        const data = await response.json();
        etfResults = data.etfs || [];
        const basketSize = typeof data.total_tickers_used === 'number' ? data.total_tickers_used : topN;
        const warnings = Array.isArray(data.warnings) ? data.warnings : [];
        renderEtfResultsTable(etfResults, basketSize, warnings);
    } catch (err) {
        resultsContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-red-400">
                <svg class="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-lg font-medium mb-1">ETF Lookup Failed</p>
                <p class="text-sm text-zinc-400">${escapeHtml(err.message)}</p>
            </div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            Find ETFs`;
    }
}

function renderEtfResultsTable(results, basketSize, warnings) {
    const container = document.getElementById('etfResultsContainer');
    if (!container) return;

    warnings = warnings || [];
    let warnBanner = '';
    if (warnings.length > 0) {
        warnBanner = `
        <div class="mb-3 text-sm text-amber-300 bg-amber-950/40 border border-amber-800/50 rounded-lg px-3 py-2">
            ${warnings.map(w => `<div>${escapeHtml(w)}</div>`).join('')}
        </div>`;
    }

    if (!results || results.length === 0) {
        container.innerHTML = warnBanner + `
            <div class="flex flex-col items-center justify-center py-16 text-zinc-400">
                <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                </svg>
                <p class="text-lg">No ETFs found matching the criteria</p>
                <p class="text-sm mt-1">Try increasing the number of top tickers or ETFs, or adjust Focus ETFs</p>
            </div>`;
        return;
    }

    const maxScore = Math.max(...results.map(r => r.themeScore));

    let html = warnBanner + `
        <div class="overflow-x-auto bg-zinc-800/50 rounded-lg border border-zinc-700">
            <table class="w-full border-collapse">
                <thead class="bg-gradient-to-r from-zinc-800 to-zinc-700">
                    <tr>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600 w-12">#</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">ETF</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600 min-w-[220px]">Theme Concentration Score</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-center text-sm font-semibold text-white border-b border-zinc-600">Holdings Match</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-right text-sm font-semibold text-white border-b border-zinc-600">Est. AUM</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-zinc-700 bg-zinc-900">`;

    results.forEach((etf, idx) => {
        const bgClass = idx % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-800/50';
        const color = getScoreColor(etf.themeScore, maxScore);
        const barWidth = maxScore > 0 ? (etf.themeScore / maxScore) * 100 : 0;
        const yahooLink = etfYahooUrl(etf.etfSymbol);

        let aliasHtml = '';
        if (etf.aliases && etf.aliases.length > 0) {
            aliasHtml = `<span class="text-zinc-500 text-xs ml-1" title="Also listed as: ${etf.aliases.join(', ')}">+${etf.aliases.length} listing${etf.aliases.length > 1 ? 's' : ''}</span>`;
        }

        html += `
                    <tr class="${bgClass} hover:bg-zinc-700/50 transition-colors duration-150">
                        <td class="px-4 py-3 text-sm text-zinc-400 font-mono">${etf.rank}</td>
                        <td class="px-4 py-3 text-sm">
                            <a href="${yahooLink}" target="_blank" rel="noopener noreferrer"
                                class="bg-blue-500 hover:bg-blue-400 text-white px-2 py-0.5 rounded font-bold text-xs font-mono inline-flex items-center gap-1 transition-colors"
                                title="View ${escapeHtml(etf.etfSymbol)} holdings on Yahoo Finance">
                                ${escapeHtml(etf.etfSymbol)}
                                <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                </svg>
                            </a>
                            ${aliasHtml}
                        </td>
                        <td class="px-4 py-3 text-sm">
                            <div class="flex items-center gap-2">
                                <div class="flex-1 h-5 bg-zinc-800 rounded overflow-hidden border border-zinc-700">
                                    <div class="h-full rounded transition-all duration-500" style="width: ${barWidth.toFixed(1)}%; background-color: ${color.barColor};"></div>
                                </div>
                                <span class="${color.text} font-bold text-xs min-w-[50px] text-right">${etf.themeScore.toFixed(2)}%</span>
                            </div>
                        </td>
                        <td class="px-4 py-3 text-sm text-center">
                            <span class="relative cursor-pointer group inline-block">
                                <span class="text-emerald-400 font-bold">${etf.matchCount}</span><span class="text-zinc-500">/${basketSize}</span>
                                <svg class="w-3 h-3 inline-block ml-0.5 text-zinc-500 group-hover:text-zinc-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                                <div class="hidden group-hover:block absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs">
                                    <div class="bg-zinc-900 border border-zinc-600 rounded-lg shadow-xl px-3 py-2 text-left">
                                        <div class="text-xs text-zinc-400 mb-1">Matched Holdings</div>
                                        <div class="flex flex-wrap gap-1">${(etf.matchedTickers || []).map(t => `<span class="bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1.5 py-0.5 rounded text-xs font-mono font-medium">${escapeHtml(t)}</span>`).join('')}</div>
                                    </div>
                                    <div class="w-2 h-2 bg-zinc-900 border-r border-b border-zinc-600 rotate-45 absolute left-1/2 -translate-x-1/2 -bottom-1"></div>
                                </div>
                            </span>
                        </td>
                        <td class="px-4 py-3 text-sm text-right text-zinc-300">${etf.estAum > 0 ? formatCurrency(etf.estAum) : '—'} <span class="text-zinc-600 text-xs">Est.</span></td>
                    </tr>`;
    });

    html += `
                </tbody>
            </table>
        </div>
        <div class="mt-3 text-xs text-zinc-500">
            Showing top ${results.length} ETFs by Theme Concentration Score across ${basketSize} equity symbol(s) in the basket.
            Cross-listed duplicates are merged. ETFs with total weight over 100% are excluded. Est. AUM is approximate.
        </div>`;

    container.innerHTML = html;
}

function showEtfMethodologyModal() {
    let container = document.getElementById('infoModalsContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onclick="if(event.target===this)this.style.display='none'">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl p-6 relative border border-gray-200 animate-in max-h-[90vh] overflow-y-auto">
          <button class="absolute top-4 right-4 text-gray-500 hover:text-gray-900 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors" onclick="this.closest('.fixed').style.display='none'">&times;</button>
          <h2 class="text-xl font-bold text-gray-900 mb-4">How ETFs are ranked</h2>
          <div class="text-base text-gray-700 leading-relaxed space-y-4">
            <p>This tab identifies ETFs most concentrated in your thematic basket.</p>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 1 — Ticker Selection</h4>
              <p><strong>Top tickers</strong> sets how many report names to use when <strong>Tickers</strong> mode is <strong>Merge</strong> (ranked by score, then symbols from the Tickers box are appended, deduped). With <strong>Only this</strong>, the basket is <em>only</em> what you type in Tickers; Top tickers is ignored. Basket size is capped on the server.</p>
            </div>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 2 — ETF Exposure Lookup</h4>
              <p>Your browser sends one request to this app; the server calls Financial Modeling Prep's ETF Asset Exposure API for each symbol (the API key never leaves the server). For each equity, we get ETFs that hold that stock and the percentage weight. Holdings with invalid weight data (&gt;100%) are discarded.</p>
              <p class="mt-2">Optional <strong>Focus ETFs</strong>: if you list symbols, only those funds are scored—using each fund’s reported holdings against your basket—so you can rank a fixed list (e.g. your firm’s ETFs) by theme exposure. Leave blank to discover ETFs via asset exposure across the basket.</p>
            </div>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 3 — Theme Concentration Score</h4>
              <p>For each ETF, we <strong>sum</strong> the weight percentages across all matched tickers. For example, if an ETF allocates 8% to AAPL, 5% to MSFT, and 3% to AMZN from your basket, the score is 16%.</p>
              <p class="mt-2">ETFs whose summed weights exceed <strong>100%</strong> (typical of leveraged or synthetic funds) are <strong>excluded</strong> so scores stay within a normal long-only interpretation.</p>
            </div>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 4 — Filtering &amp; Ranking</h4>
              <p>ETFs are filtered to remove:</p>
              <ul class="list-disc pl-6 mt-1 space-y-1">
                <li>ETFs holding only one thematic ticker (avoids coincidental matches)</li>
                <li>ETFs with estimated AUM below $100M (removes micro-funds and data anomalies)</li>
                <li>Cross-listed duplicates — the same fund listed on multiple exchanges is shown once, with the primary (typically US) ticker</li>
              </ul>
              <p class="mt-2">Remaining ETFs are ranked by Theme Concentration Score (highest first; scores above 100% are excluded).</p>
            </div>
          </div>

          <hr class="my-5 border-gray-200">

          <h3 class="text-lg font-bold text-gray-900 mb-3">Column definitions</h3>
          <div class="text-sm text-gray-700 leading-relaxed space-y-3">
            <div>
              <span class="font-semibold text-gray-900">Theme Concentration Score</span> — 
              Sum of the ETF's weight percentages for all matched basket tickers. Higher means more of the fund is allocated to your theme. Results exclude ETFs whose sum exceeds 100%.
            </div>
            <div>
              <span class="font-semibold text-gray-900">Holdings Match</span> — 
              How many symbols in your equity basket this ETF holds. Shown as <em>matched / total</em> (basket is either merged top N + Tickers, or only Tickers, after deduplication and caps).
            </div>
            <div>
              <span class="font-semibold text-gray-900">Est. AUM</span> — 
              Estimated Assets Under Management. Derived from: <code class="bg-gray-100 px-1 rounded text-xs">holding marketValue ÷ (weightPercentage / 100)</code>. This is an approximation — actual fund AUM may differ. ETFs below $100M estimated AUM are excluded.
            </div>
          </div>
        </div>
      </div>
    `;
}

// Lazy initialization: if the tab is clicked but content is empty, populate it
document.addEventListener('DOMContentLoaded', function() {
    const etfTabBtn = document.querySelector('[data-tab="etfs"]');
    if (etfTabBtn) {
        etfTabBtn.addEventListener('click', function() {
            setTimeout(function() {
                const container = document.querySelector('[data-tab-content="etfs"] .tab-actual-content');
                if (container && container.innerHTML.trim() === '') {
                    renderEtfTab();
                }
            }, 50);
        });
    }
});

window.handleFindEtfs = handleFindEtfs;
window.showEtfMethodologyModal = showEtfMethodologyModal;
window.renderEtfTab = renderEtfTab;
