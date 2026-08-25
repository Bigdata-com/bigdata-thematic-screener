// Excel export (Heatmap / Taxonomy / Evidence) — structure and color scheme
// modeled on Internal/Sample_Thematic_Screener.xlsx.
//
// Works on whatever report is currently displayed (window.lastReport), same as
// the "Export JSON" button — so it covers live analyses, Quick Start demos, and
// uploaded JSON reports alike. They all share the same native shape
// (theme_scoring / theme_taxonomy / content), normalized below mainly to unwrap
// RootModel-style {root: [...]} content and to default missing fields.

const HEATMAP_SLATE_ARGB = 'FF1E2A3A'; // "no evidence" cell color
const TITLE_BG_ARGB = 'FF0D1B2A';
const HEADER_BG_ARGB = 'FF16213E';
const COMPANY_BG_ARGB = 'FF1A1A2E';
const EVIDENCE_ZEBRA_ARGB = 'FF0F1E3A';
const TICKER_BG_ARGB = 'FF1A6FA8';
const INDUSTRY_FONT_ARGB = 'FFB0B8C4';
const WHITE_ARGB = 'FFFFFFFF';

function normalizeReport(raw) {
    const taxonomy = raw.theme_taxonomy || null;
    const scoringSource = raw.theme_scoring || {};
    const scoring = {};
    for (const [company, entry] of Object.entries(scoringSource)) {
        scoring[company] = {
            ticker: entry.ticker || '',
            industry: entry.industry || 'Unknown',
            composite_score: entry.composite_score || 0,
            motivation: entry.motivation || '',
            themes: entry.themes || {},
        };
    }

    let content = raw.content;
    if (content && typeof content === 'object' && !Array.isArray(content) && Array.isArray(content.root)) {
        content = content.root;
    }
    if (!Array.isArray(content)) content = [];

    return { taxonomy, scoring, content };
}

function rgbToArgb([r, g, b]) {
    const hex = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0').toUpperCase();
    return `FF${hex(r)}${hex(g)}${hex(b)}`;
}

function lerpRgb(from, to, t) {
    return from.map((v, i) => v + (to[i] - v) * t);
}

// Green intensity scale relative to a column's own max value, matching the reference workbook:
// R ramps 20 -> 10, G ramps 60 -> 255 (clamped), B ramps 80 -> 30, as value/colMax goes 0 -> 1.
// Empty/zero cells are slate.
function heatmapColor(value, colMax) {
    if (!value || !colMax) return HEATMAP_SLATE_ARGB;
    const ratio = Math.min(value / colMax, 1);
    const r = Math.floor(20 - 10 * ratio);
    const g = Math.min(255, Math.floor(60 + 195 * ratio));
    const b = Math.floor(80 - 50 * ratio);
    return rgbToArgb([r, g, b]);
}

function solidFill(argb) {
    return { type: 'pattern', pattern: 'solid', fgColor: { argb } };
}

function buildHeatmapSheet(workbook, mainTheme, scoring) {
    const sheet = workbook.addWorksheet('Heatmap', {
        views: [{ state: 'frozen', xSplit: 4, ySplit: 2 }],
    });

    const themeLabels = Array.from(
        new Set(Object.values(scoring).flatMap((c) => Object.keys(c.themes || {})))
    ).sort((a, b) => a.localeCompare(b));

    const headers = ['Company', 'Ticker', 'Industry', 'Score', ...themeLabels];
    sheet.columns = [
        { width: 30 },
        { width: 8 },
        { width: 22 },
        { width: 14 },
        ...themeLabels.map(() => ({ width: 6 })),
    ];

    sheet.mergeCells(1, 1, 1, headers.length);
    const titleCell = sheet.getCell(1, 1);
    titleCell.value = mainTheme;
    titleCell.font = { bold: true, color: { argb: WHITE_ARGB } };
    titleCell.fill = solidFill(TITLE_BG_ARGB);
    titleCell.alignment = { horizontal: 'left', vertical: 'center' };
    sheet.getRow(1).height = 24;

    const headerRow = sheet.getRow(2);
    headers.forEach((label, i) => {
        const cell = headerRow.getCell(i + 1);
        cell.value = label;
        cell.font = { bold: true, color: { argb: WHITE_ARGB } };
        cell.fill = solidFill(HEADER_BG_ARGB);
        cell.alignment =
            i < 4
                ? { horizontal: 'center', vertical: 'bottom' }
                : { horizontal: 'center', vertical: 'bottom', textRotation: 75 };
    });
    headerRow.height = 130;

    const colMax = {};
    themeLabels.forEach((label) => {
        colMax[label] = Math.max(0, ...Object.values(scoring).map((c) => c.themes[label] || 0));
    });
    const compositeMax = Math.max(0, ...Object.values(scoring).map((c) => c.composite_score || 0));

    const rows = Object.entries(scoring).sort(
        (a, b) => (b[1].composite_score || 0) - (a[1].composite_score || 0)
    );

    rows.forEach(([company, data], idx) => {
        const row = sheet.getRow(idx + 3);
        row.height = 15;

        const companyCell = row.getCell(1);
        companyCell.value = company;
        companyCell.font = { color: { argb: WHITE_ARGB } };
        companyCell.fill = solidFill(COMPANY_BG_ARGB);
        companyCell.alignment = { horizontal: 'left', vertical: 'center' };

        const tickerCell = row.getCell(2);
        tickerCell.value = data.ticker;
        tickerCell.font = { bold: true, color: { argb: WHITE_ARGB } };
        tickerCell.fill = solidFill(TICKER_BG_ARGB);
        tickerCell.alignment = { horizontal: 'center', vertical: 'center' };

        const industryCell = row.getCell(3);
        industryCell.value = data.industry;
        industryCell.font = { color: { argb: INDUSTRY_FONT_ARGB } };
        industryCell.fill = solidFill(COMPANY_BG_ARGB);
        industryCell.alignment = { horizontal: 'left', vertical: 'center' };

        const compositeCell = row.getCell(4);
        compositeCell.value = data.composite_score;
        compositeCell.font = { bold: true, color: { argb: WHITE_ARGB } };
        compositeCell.fill = solidFill(heatmapColor(data.composite_score, compositeMax));
        compositeCell.alignment = { horizontal: 'center', vertical: 'center' };

        themeLabels.forEach((label, i) => {
            const value = data.themes[label] || 0;
            const cell = row.getCell(5 + i);
            cell.value = value || null;
            cell.font = { color: { argb: WHITE_ARGB } };
            cell.fill = solidFill(heatmapColor(value, colMax[label]));
            cell.alignment = { horizontal: 'center', vertical: 'center' };
        });
    });
}

function taxonomyDepth(node, depth) {
    if (!node.children || node.children.length === 0) return depth;
    return Math.max(...node.children.map((child) => taxonomyDepth(child, depth + 1)));
}

const TAXONOMY_HEADER_START = [26, 82, 118]; // #1A5276
const TAXONOMY_HEADER_END = [46, 134, 193]; // #2E86C1
const TAXONOMY_ROW_BASE = [13, 27, 42]; // #0D1B2A (depth 1)
const TAXONOMY_ROW_STEP = [8, 5, 13]; // lightening per depth level
const TAXONOMY_MAX_SHADE_DEPTH = 6; // cap how far the lightening ramp goes

function buildTaxonomySheet(workbook, mainTheme, taxonomy) {
    const sheet = workbook.addWorksheet('Taxonomy');
    if (!taxonomy || !taxonomy.label) return;

    const maxDepth = taxonomyDepth(taxonomy, 1);
    const headers = Array.from({ length: maxDepth }, (_, i) => `Node ${i + 1}`).concat('Text');

    sheet.columns = [...Array.from({ length: maxDepth }, () => ({ width: 28 })), { width: 60 }];

    sheet.mergeCells(1, 1, 1, headers.length);
    const titleCell = sheet.getCell(1, 1);
    titleCell.value = mainTheme;
    titleCell.font = { bold: true, color: { argb: WHITE_ARGB } };
    titleCell.fill = solidFill(TITLE_BG_ARGB);
    titleCell.alignment = { horizontal: 'left', vertical: 'center' };
    sheet.getRow(1).height = 24;

    const headerRow = sheet.getRow(2);
    headers.forEach((label, i) => {
        const t = headers.length > 1 ? i / (headers.length - 1) : 0;
        const cell = headerRow.getCell(i + 1);
        cell.value = label;
        cell.font = { bold: true, color: { argb: WHITE_ARGB } };
        cell.fill = solidFill(rgbToArgb(lerpRgb(TAXONOMY_HEADER_START, TAXONOMY_HEADER_END, t)));
        cell.alignment = { horizontal: 'left', vertical: 'bottom', wrapText: true };
    });
    headerRow.height = 22;

    let excelRowIndex = 3;

    function walk(node, ancestorLabels, depth) {
        const row = sheet.getRow(excelRowIndex);
        for (let i = 0; i < depth; i++) {
            row.getCell(i + 1).value = ancestorLabels[i];
        }
        row.getCell(maxDepth + 1).value = node.summary || '';

        const shadeDepth = Math.min(depth - 1, TAXONOMY_MAX_SHADE_DEPTH);
        const shade = rgbToArgb(TAXONOMY_ROW_BASE.map((v, i) => v + TAXONOMY_ROW_STEP[i] * shadeDepth));
        for (let c = 1; c <= maxDepth + 1; c++) {
            const cell = row.getCell(c);
            cell.font = { bold: c <= depth, color: { argb: WHITE_ARGB } };
            cell.fill = solidFill(shade);
            cell.alignment =
                c === maxDepth + 1
                    ? { horizontal: 'left', vertical: 'center', wrapText: true }
                    : { horizontal: 'left', vertical: 'center', indent: depth - 1 };
        }
        row.height = 18;
        excelRowIndex++;

        for (const child of node.children || []) {
            walk(child, [...ancestorLabels, child.label], depth + 1);
        }
    }

    walk(taxonomy, [taxonomy.label], 1);
}

const EVIDENCE_TITLE = 'Evidence & Supporting Quotes';
const EVIDENCE_HEADERS = ['Time Period', 'Date', 'Company', 'Headline', 'Quote', 'Motivation', 'Theme'];
const EVIDENCE_WRAP_COLUMNS = new Set([3, 4, 5]); // Headline, Quote, Motivation (0-indexed)

function buildEvidenceSheet(workbook, content) {
    const sheet = workbook.addWorksheet('Evidence', { views: [{ state: 'frozen', ySplit: 2 }] });
    sheet.columns = [
        { width: 12 },
        { width: 12 },
        { width: 22 },
        { width: 40 },
        { width: 60 },
        { width: 40 },
        { width: 22 },
    ];

    sheet.mergeCells(1, 1, 1, EVIDENCE_HEADERS.length);
    const titleCell = sheet.getCell(1, 1);
    titleCell.value = EVIDENCE_TITLE;
    titleCell.font = { bold: true, color: { argb: WHITE_ARGB } };
    titleCell.fill = solidFill(TITLE_BG_ARGB);
    titleCell.alignment = { horizontal: 'left', vertical: 'center' };
    sheet.getRow(1).height = 24;

    const headerRow = sheet.getRow(2);
    EVIDENCE_HEADERS.forEach((label, i) => {
        const cell = headerRow.getCell(i + 1);
        cell.value = label;
        cell.font = { bold: true, color: { argb: WHITE_ARGB } };
        cell.fill = solidFill(HEADER_BG_ARGB);
        cell.alignment = { horizontal: 'center', vertical: 'bottom', wrapText: true };
    });
    headerRow.height = 22;

    const sorted = [...content].sort((a, b) => {
        const byCompany = (a.company || '').localeCompare(b.company || '');
        if (byCompany !== 0) return byCompany;
        return (a.date || '').localeCompare(b.date || '');
    });

    sorted.forEach((chunk, idx) => {
        const row = sheet.getRow(idx + 3);
        const values = [
            chunk.time_period,
            chunk.date,
            chunk.company,
            chunk.headline,
            chunk.quote,
            chunk.motivation,
            chunk.theme || '',
        ];
        const shade = idx % 2 === 0 ? COMPANY_BG_ARGB : EVIDENCE_ZEBRA_ARGB;
        values.forEach((value, i) => {
            const cell = row.getCell(i + 1);
            cell.value = value || '';
            cell.font = { color: { argb: WHITE_ARGB } };
            cell.fill = solidFill(shade);
            cell.alignment = { horizontal: 'left', vertical: 'top', wrapText: EVIDENCE_WRAP_COLUMNS.has(i) };
        });
    });
}

function slugify(text) {
    return (text || 'thematic_screener')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 60) || 'thematic_screener';
}

async function exportToExcel() {
    if (!window.lastReport) {
        alert('No report loaded to export.');
        return;
    }
    if (typeof ExcelJS === 'undefined') {
        alert('Excel export could not load its library (exceljs from a CDN). Check your network connection and try again.');
        return;
    }

    const btn = document.getElementById('exportExcelBtn');
    const originalHTML = btn ? btn.innerHTML : null;
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Exporting...';
    }

    try {
        const { taxonomy, scoring, content } = normalizeReport(window.lastReport);
        const mainTheme = (taxonomy && taxonomy.label) || window.currentConfig?.theme || 'Thematic Screener';

        const workbook = new ExcelJS.Workbook();
        buildHeatmapSheet(workbook, mainTheme, scoring);
        buildTaxonomySheet(workbook, mainTheme, taxonomy);
        buildEvidenceSheet(workbook, content);

        const buffer = await workbook.xlsx.writeBuffer();
        const blob = new Blob([buffer], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${slugify(mainTheme)}_thematic_screener.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } catch (err) {
        console.error('Excel export failed:', err);
        alert(`Excel export failed: ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            if (originalHTML !== null) btn.innerHTML = originalHTML;
        }
    }
}

window.exportToExcel = exportToExcel;
