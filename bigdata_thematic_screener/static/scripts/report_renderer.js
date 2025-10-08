function renderScreenerReport(data) {
    if (!data || typeof data !== 'object') return '<span class="error">No data to display.</span>';
    let html = '<h2 class="text-3xl font-bold text-white mb-4">Thematic Screener Result</h2>';

    // Render theme_scoring (dict of ticker -> CompanyScoring)
    if (data.theme_scoring && data.theme_scoring) {
        html += '<h3 class="text-2xl font-bold text-white mb-4 flex items-center gap-2"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>Theme Scoring</h3>';
        html += '<div class="max-h-[500px] overflow-y-auto border border-zinc-700 rounded-lg shadow-lg p-4">'
        html += '<div class="flex flex-col gap-6 w-full">';

        // Dynamically get all themes
        let allThemes = new Set();
        for (const scoring of Object.values(data.theme_scoring)) {
            if (scoring.themes) {
                Object.keys(scoring.themes).forEach(theme => allThemes.add(theme));
            }
        }
        const themeList = Array.from(allThemes);

        // Render each company as a card
        for (const [company_name, scoring] of Object.entries(data.theme_scoring)) {
            html += '<div class="bg-gradient-to-br from-gray-50 to-gray-200 rounded-xl p-3 border-l-4 border-blue-500 transition-all duration-300 hover:shadow-2xl">';

            // Header with company info on left and composite score on right
            html += '<div class="flex justify-between items-start mb-2">';

            // Left side: Company header and industry
            html += '<div class="flex flex-col">';
            html += '<div class="flex items-center mb-2">';
            html += `<div class="bg-blue-500 text-white px-3 py-1 rounded-full font-bold text-sm mr-2">${escapeHtml(scoring.ticker)}</div>`;
            html += `<div class="text-xl font-bold text-gray-800">${escapeHtml(company_name)}</div>`;
            html += '</div>';
            html += '<div class="text-gray-600">';
            html += `<strong>Industry:</strong> ${escapeHtml(scoring.industry)}`;
            html += '</div>';
            html += '</div>';

            // Right side: Composite score
            html += '<div class="flex flex-col items-center justify-center">';
            html += `<div class="text-3xl text-blue-500 font-bold">${escapeHtml(scoring.composite_score)}</div>`;
            html += '<div class="text-gray-600 text-sm whitespace-nowrap">Composite Score</div>';
            html += '</div>';

            html += '</div>'; // Close header flex container

            // Themes grid - only show themes with score != 0
            html += '<div class="grid grid-cols-2 gap-2 mt-4">';
            themeList.forEach(theme => {
                const score = (scoring.themes && theme in scoring.themes) ? scoring.themes[theme] : 0;
                if (score !== 0) {
                    html += '<div class="flex justify-between items-center bg-white p-2 px-3 rounded-md text-sm">';
                    html += `<span class="text-gray-800">${escapeHtml(theme)}</span>`;
                    html += `<div class="bg-green-600 text-white w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs">${escapeHtml(score)}</div>`;
                    html += '</div>';
                }
            });
            html += '</div>';

            // Motivation
            html += '<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4 text-yellow-800 leading-relaxed cursor-pointer relative group" onclick="toggleMotivation(this)">';
            html += '<div class="motivation-text max-h-[2em] overflow-hidden">';
            html += `<strong>Key Innovations:</strong> ${escapeHtml(scoring.motivation)}`;
            html += '</div>';
            html += '<div class="text-blue-600 text-sm font-semibold mt-2 group-hover:text-blue-800">Click to expand</div>';
            html += '</div>';

            html += '</div>'; // Close card
        }
        html += '</div>'; // Close grid
        html += '</div>'; // Close container
    }

    // Render theme_taxonomy (tree)
    function renderTaxonomy(node, depth = 0) {
        if (!node) return '';
        let pad = '&nbsp;'.repeat(depth * 4);
        let html = `${pad}<b class="text-blue-400">${escapeHtml(node.label)}</b> <span class="text-zinc-500">(Node: ${escapeHtml(node.node)})</span>`;
        if (node.summary) html += ` <span class="text-zinc-300">- ${escapeHtml(node.summary)}</span>`;
        if (node.children && node.children.length) {
            html += '<ul class="ml-4 my-2 border-l-2 border-zinc-700 pl-4">';
            for (const child of node.children) {
                html += '<li class="my-1">' + renderTaxonomy(child, depth + 1) + '</li>';
            }
            html += '</ul>';
        }
        return html;
    }
    if (data.theme_taxonomy) {
        html += '<h3 class="text-2xl font-bold text-white mb-4 mt-8 flex items-center gap-2"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>Theme Taxonomy</h3>';
        html += '<div class="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6 shadow-lg">' + renderTaxonomy(data.theme_taxonomy) + '</div>';
    }

    // Render content (list of LabeledChunk)
    if (data.content && Array.isArray(data.content) && data.content.length) {
        html += '<h3 class="text-2xl font-bold text-white mb-4 mt-8 flex items-center gap-2"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>Labeled Content</h3>';
        html += '<div class="max-h-[500px] overflow-y-auto border border-zinc-700 rounded-lg shadow-lg">'
        html += '<table class="table-auto w-full border-collapse">';
        html += '<thead class="bg-gradient-to-r from-zinc-800 to-zinc-700">';
        html += '<tr>';
        html += '<th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">Time Period</th><th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">Date</th><th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">Company</th><th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600"><span>Headline</span><span><button type="button" class="text-blue-400 text-sm ml-1 hover:text-blue-300" onclick=showInfoModal(\'headline_comment\') title="Info">ⓘ</button></span></th><th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">Quote</th><th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">Motivation</th><th class="sticky top-0 z-10 bg-gradient-to-r from-zinc-800 to-zinc-700 px-4 py-3 text-left text-sm font-semibold text-white border-b border-zinc-600">Theme</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody class="divide-y divide-zinc-700 bg-zinc-900">';
        let rowIdx = 0;
        for (const chunk of data.content) {
            const bgClass = rowIdx % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-800/50';
            html += `<tr class="${bgClass} hover:bg-zinc-700/50 transition-colors duration-150">`;
            html += `<td class="px-4 py-3 text-sm text-zinc-300">${escapeHtml(chunk.time_period)}</td>`;
            html += `<td class="px-4 py-3 text-sm text-zinc-300">${escapeHtml(chunk.date)}</td>`;
            html += `<td class="px-4 py-3 text-sm font-medium text-zinc-200">${escapeHtml(chunk.company)}</td>`;
            html += `<td class="px-4 py-3 text-sm text-blue-400 cursor-pointer hover:text-blue-300 hover:underline" onclick="showDocumentModal('${chunk.document_id}')">${escapeHtml(chunk.headline)}</td>`;
            html += `<td class="px-4 py-3 text-sm text-zinc-300 italic">${escapeHtml(chunk.quote)}</td>`;
            html += `<td class="px-4 py-3 text-sm text-zinc-300">${escapeHtml(chunk.motivation)}</td>`;
            html += `<td class="px-4 py-3 text-sm font-medium text-green-400">${escapeHtml(chunk.theme)}</td>`;
            html += '</tr>';
            rowIdx++;
        }
        html += '</tbody>';
        html += '</table>';
        html += '</div>'
    }
    return html;
};