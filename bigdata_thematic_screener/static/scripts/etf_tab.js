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

function renderEtfTab(themeScoring) {
    const container = document.querySelector('[data-tab-content="etfs"] .tab-actual-content');
    if (!container) return;

    if (themeScoring) {
        etfThemeScoring = themeScoring;
    }

    const scoring = getThemeScoring();
    const fmpKey = window.__FMP_API_KEY__ || '';
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
                    <div>
                        <button onclick="handleFindEtfs()" id="findEtfsBtn"
                            class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            ${!hasReport || !fmpKey ? 'disabled' : ''}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                            Find ETFs
                        </button>
                    </div>
                </div>`;

    if (!fmpKey) {
        html += `
                <div class="mt-3 text-sm text-amber-400 flex items-center gap-2">
                    <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    </svg>
                    FMP API key not configured. Set the <code class="bg-zinc-700 px-1 rounded text-xs">FMP_API_KEY</code> environment variable to enable ETF lookups.
                </div>`;
    } else if (!hasReport) {
        html += `
                <div class="mt-3 text-sm text-zinc-500 flex items-center gap-2">
                    <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Run a thematic analysis first to populate the company list.
                </div>`;
    } else {
        html += `
                <div class="mt-3 text-sm text-zinc-500">
                    ${companyCount} companies available · Using top ${defaultTopN} by score
                </div>`;
    }

    html += `
            </div>
        </div>

        <!-- Results container -->
        <div id="etfResultsContainer"></div>
    `;

    container.innerHTML = html;
}

async function handleFindEtfs() {
    const btn = document.getElementById('findEtfsBtn');
    const resultsContainer = document.getElementById('etfResultsContainer');
    if (!btn || !resultsContainer) return;

    const topN = parseInt(document.getElementById('etfTopN').value) || 10;
    const topK = parseInt(document.getElementById('etfTopK').value) || 10;
    const apiKey = window.__FMP_API_KEY__ || '';
    const scoring = getThemeScoring();

    if (!scoring) {
        resultsContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-red-400">
                <p class="text-lg font-medium">No company data available</p>
                <p class="text-sm text-zinc-400 mt-1">Run a thematic analysis first.</p>
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
            <span class="ml-3 text-zinc-400">Querying ETF exposure for top ${topN} tickers...</span>
        </div>`;

    try {
        etfResults = await runEtfPipeline(scoring, apiKey, topN, topK);
        renderEtfResultsTable(etfResults, topN);
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

function renderEtfResultsTable(results, topN) {
    const container = document.getElementById('etfResultsContainer');
    if (!container) return;

    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-zinc-400">
                <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                </svg>
                <p class="text-lg">No ETFs found matching the criteria</p>
                <p class="text-sm mt-1">Try increasing the number of top tickers or ETFs</p>
            </div>`;
        return;
    }

    const maxScore = Math.max(...results.map(r => r.themeScore));

    let html = `
        <div class="overflow-x-auto bg-zinc-800/50 rounded-lg border border-zinc-700">
            <table class="w-full border-collapse">
                <thead class="bg-gradient-to-r from-zinc-800 to-zinc-700">
                    <tr>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600 w-12">#</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">ETF</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600 min-w-[220px]">Theme Concentration Score</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-center text-sm font-semibold text-white border-b border-zinc-600">Holdings Match</th>
                        <th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-right text-sm font-semibold text-white border-b border-zinc-600">Avg Weight</th>
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

        const isLeveraged = etf.themeScore > 100;
        const leveragedBadge = isLeveraged
            ? `<span class="bg-amber-500/20 text-amber-400 border border-amber-500/30 px-1.5 py-0.5 rounded text-xs font-medium ml-1" title="Score exceeds 100% — likely a leveraged (2x/3x) or synthetic ETF">Leveraged</span>`
            : '';

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
                            ${leveragedBadge}${aliasHtml}
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
                            <span class="text-emerald-400 font-bold">${etf.matchCount}</span><span class="text-zinc-500">/${topN}</span>
                        </td>
                        <td class="px-4 py-3 text-sm text-right text-zinc-300">${etf.avgWeight.toFixed(2)}%</td>
                        <td class="px-4 py-3 text-sm text-right text-zinc-300">${etf.estAum > 0 ? formatCurrency(etf.estAum) : '—'} <span class="text-zinc-600 text-xs">Est.</span></td>
                    </tr>`;
    });

    html += `
                </tbody>
            </table>
        </div>
        <div class="mt-3 text-xs text-zinc-500">
            Showing top ${results.length} ETFs by Theme Concentration Score across ${topN} tickers.
            Cross-listed duplicates are merged. Est. AUM derived from holding market values — may differ from actual fund AUM.
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
              <p>The top N companies from your thematic screener (ranked by Score) are used as the input basket.</p>
            </div>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 2 — ETF Exposure Lookup</h4>
              <p>For each ticker, we query FMP's ETF Asset Exposure API to find all ETFs that hold that stock, along with the percentage weight it represents in each ETF. Holdings with invalid weight data (>100%) are discarded.</p>
            </div>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 3 — Theme Concentration Score</h4>
              <p>For each ETF, we <strong>sum</strong> the weight percentages across all matched tickers. For example, if an ETF allocates 8% to AAPL, 5% to MSFT, and 3% to AMZN from your basket, the score is 16%.</p>
              <div class="mt-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p class="text-amber-800 text-sm"><strong>Scores above 100%:</strong> A standard ETF's holdings always sum to ~100%, so a Theme Concentration Score above 100% indicates the fund is likely <strong>leveraged (2x/3x)</strong> or uses synthetic/derivative exposure. These ETFs report amplified weights that exceed a normal portfolio's capacity. They are flagged with a <span class="bg-amber-100 text-amber-700 border border-amber-300 px-1 rounded text-xs font-medium">Leveraged</span> badge in the results table.</p>
              </div>
            </div>
            
            <div>
              <h4 class="font-semibold text-gray-900 mb-1">Step 4 — Filtering &amp; Ranking</h4>
              <p>ETFs are filtered to remove:</p>
              <ul class="list-disc pl-6 mt-1 space-y-1">
                <li>ETFs holding only one thematic ticker (avoids coincidental matches)</li>
                <li>ETFs with estimated AUM below $100M (removes micro-funds and data anomalies)</li>
                <li>Cross-listed duplicates — the same fund listed on multiple exchanges is shown once, with the primary (typically US) ticker</li>
              </ul>
              <p class="mt-2">Remaining ETFs are ranked by Theme Concentration Score (highest first).</p>
            </div>
          </div>

          <hr class="my-5 border-gray-200">

          <h3 class="text-lg font-bold text-gray-900 mb-3">Column definitions</h3>
          <div class="text-sm text-gray-700 leading-relaxed space-y-3">
            <div>
              <span class="font-semibold text-gray-900">Theme Concentration Score</span> — 
              Sum of the ETF's weight percentages for all matched thematic tickers. Higher = more of the fund is allocated to your theme. For standard ETFs this caps at 100%; scores above 100% indicate leveraged or synthetic ETFs (flagged with a <span class="bg-amber-100 text-amber-700 border border-amber-300 px-1 rounded text-xs font-medium">Leveraged</span> badge).
            </div>
            <div>
              <span class="font-semibold text-gray-900">Holdings Match</span> — 
              How many of your top N thematic tickers this ETF holds. Shown as <em>matched / total</em> (e.g. 7/10).
            </div>
            <div>
              <span class="font-semibold text-gray-900">Avg Weight</span> — 
              Theme Concentration Score ÷ Holdings Match. The average portfolio weight per matched thematic stock. A high value means the ETF holds meaningful positions in your thematic tickers, not just token amounts.
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
