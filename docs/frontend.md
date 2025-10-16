# Frontend Quick Start Guide
Note that this guide was AI-generated, but it still provides an useful overview of the frontend code structure and key components. Please refer to the actual code files for the most accurate and up-to-date information.

## For Developers

### File Structure
```
bigdata_thematic_screener/
├── static/
│   └── scripts/
│       ├── tab_controller.js      # Tab management
│       ├── heatmap.js             # Summary tab heatmap
│       ├── company_cards.js       # Companies tab cards
│       ├── mindmap.js             # Mindmap tab visualizations
│       ├── evidence_table.js      # Evidence tab table
│       ├── report_renderer.js     # Main orchestrator
│       ├── form.js                # Form submission
│       ├── load_example.js        # Example loading
│       ├── validators.js          # Form validation
│       └── visualization.js       # Shared utilities
└── templates/
    └── api/
        ├── base.html.jinja        # Base template (D3.js added)
        └── index.html.jinja       # Main page (tabs added)
```

### Key Components

#### 1. Tab Controller (`tab_controller.js`)
Manages tab state and visibility.

**API:**
```javascript
// Initialize tabs
window.tabController.init();

// Switch to a tab
window.tabController.switchTab('summary' | 'companies' | 'mindmap' | 'evidence');

// Set loading state
window.tabController.setLoadingState(tabName, isLoading);

// Show empty state
window.tabController.showEmptyState(tabName, message);

// Reset all tabs
window.tabController.reset();
```

#### 2. Report Renderer (`report_renderer.js`)
Main orchestrator that distributes data to specialized renderers.

**Entry Point:**
```javascript
renderScreenerReport(data);
// data = { theme_scoring, theme_taxonomy, content }
```

#### 3. Specialized Renderers

**Heatmap** (`heatmap.js`):
```javascript
renderHeatmap(themeScoring);
// themeScoring = { "Company Name": CompanyScoring, ... }
```

**Company Cards** (`company_cards.js`):
```javascript
renderCompanyCards(themeScoring);
// Includes search, sort, and collapsible sections
```

**Mindmap** (`mindmap.js`):
```javascript
renderMindmap(taxonomy);
// Provides both tree and D3.js graph views
switchMindmapView('tree' | 'graph');
```

**Evidence Table** (`evidence_table.js`):
```javascript
renderEvidenceTable(content);
// content = [LabeledChunk, ...]
// Includes filters, pagination, export
```

### Data Flow

```
Form Submit → POST /thematic-screener
    ↓
Request ID returned
    ↓
Poll /status/{request_id} every 5s
    ↓
Status: completed + report data
    ↓
renderScreenerReport(data)
    ↓
┌─────────┬──────────┬──────────┬──────────┐
│ Summary │Companies │ Mindmap  │ Evidence │
└─────────┴──────────┴──────────┴──────────┘
```

### Adding a New Tab

1. **Add tab button** in `index.html.jinja`:
```html
<button data-tab="newtab" class="...">
  <svg>...</svg>
  New Tab
</button>
```

2. **Add tab content** in `index.html.jinja`:
```html
<div data-tab-content="newtab" class="hidden p-6">
  <div class="loading-indicator hidden">...</div>
  <div class="tab-actual-content"></div>
</div>
```

3. **Create renderer** `newtab.js`:
```javascript
function renderNewTab(data) {
  const container = document.querySelector('[data-tab-content="newtab"] .tab-actual-content');
  if (!container || !data) return;
  
  // Render your content
  container.innerHTML = '...';
}
```

4. **Add to report renderer** in `report_renderer.js`:
```javascript
if (data.some_field) {
  window.tabController.setLoadingState('newtab', false);
  renderNewTab(data.some_field);
}
```

5. **Import script** in `index.html.jinja`:
```html
<script src="static/scripts/newtab.js"></script>
```

### Styling Guidelines

**Color Palette:**
```css
/* Backgrounds */
bg-zinc-900   /* Main background */
bg-zinc-800   /* Panels */
bg-zinc-700   /* Borders */

/* Text */
text-white         /* Primary */
text-zinc-300      /* Secondary */
text-zinc-400      /* Muted */

/* Accents */
bg-blue-500        /* Primary actions */
bg-emerald-500     /* Success/positive */
bg-amber-500       /* Warnings */
text-blue-400      /* Links */
```

**Common Patterns:**
```html
<!-- Card -->
<div class="bg-zinc-800/50 rounded-lg border border-zinc-700 p-6">
  Content
</div>

<!-- Button Primary -->
<button class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
  Action
</button>

<!-- Button Secondary -->
<button class="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors">
  Action
</button>

<!-- Input -->
<input class="px-3 py-2 bg-zinc-900 border border-zinc-600 rounded-lg text-zinc-200 focus:ring-2 focus:ring-blue-500">
```

### Common Tasks

#### Change Default Tab
In `tab_controller.js`:
```javascript
constructor() {
  this.activeTab = 'companies'; // Change from 'summary'
}
```

#### Add New Filter to Evidence
In `evidence_table.js`, update the filter section and `applyEvidenceFilters()` function.

#### Customize Heatmap Colors
In `heatmap.js`, modify the `emeraldShades` array in the rendering loop.

#### Add Mindmap Node Details
In `mindmap.js`, extend the tooltip content in both `renderTreeView` and `renderGraphView`.

### Debugging Tips

1. **Check Tab Controller:**
```javascript
console.log(window.tabController.activeTab);
console.log(window.tabController.loadingStates);
```

2. **Check Last Report:**
```javascript
console.log(lastReport);
```

3. **Check Data in Specific Tab:**
```javascript
// After rendering
const container = document.querySelector('[data-tab-content="summary"] .tab-actual-content');
console.log(container.innerHTML);
```

4. **Monitor Tab Switches:**
Add to `tab_controller.js`:
```javascript
switchTab(tabName) {
  console.log('Switching to:', tabName);
  // ... existing code
}
```

### Performance Optimization

1. **Lazy Rendering**: Tabs only render when first viewed
2. **Pagination**: Evidence table uses 50 items/page
3. **Debouncing**: Search inputs should debounce (can be added)
4. **Virtual Scrolling**: For very large tables (future enhancement)

### Browser Support

**Required:**
- ES6+ (arrow functions, template literals, classes)
- D3.js v7 compatible browser
- CSS Grid and Flexbox

**Tested:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Dependencies

**External:**
- TailwindCSS (via CDN)
- D3.js v7 (via CDN)

**No Build Step Required!**
All code runs directly in the browser.

### Troubleshooting

**Tabs not switching:**
- Check if `tab_controller.js` is loaded
- Check for console errors
- Verify `data-tab` and `data-tab-content` attributes match

**Data not rendering:**
- Check if `renderScreenerReport()` is being called
- Verify data structure matches expected format
- Check individual renderer console logs

**D3 graph not showing:**
- Ensure D3.js loaded before mindmap.js
- Check SVG container has height set
- Verify data structure is hierarchical

**Export not working:**
- Check browser allows downloads
- Verify data is in `filteredEvidenceData`
- Check console for blob/download errors

### Getting Help

1. Check browser console for errors
2. Review `TESTING_CHECKLIST.md` for common issues
3. Read `FRONTEND_REDESIGN_SUMMARY.md` for architecture
4. Check individual file comments for specific functionality

### Making Changes

1. **Test in Browser First**: Make changes in dev tools
2. **Update Source Files**: Apply changes to actual files
3. **Clear Cache**: Force refresh (Cmd+Shift+R / Ctrl+F5)
4. **Test All Tabs**: Ensure no regressions
5. **Check Console**: No errors should appear

### Best Practices

1. **Preserve Function Signatures**: Don't change parameters of existing functions
2. **Use Global Window**: Make shared functions available via `window.functionName`
3. **Escape HTML**: Always use `escapeHtml()` for user data
4. **Handle Missing Data**: Check if data exists before rendering
5. **Maintain Consistency**: Follow existing patterns and styles
6. **Comment Complex Logic**: Help future maintainers
7. **Test Edge Cases**: Empty data, single item, 100+ items

---

## Quick Commands

**Start Server:**
```bash
# Depends on your setup, typically:
python -m bigdata_thematic_screener
# or
make run
```

**View in Browser:**
```
http://localhost:8000
```

**Clear Browser Cache:**
- Chrome/Edge: Cmd+Shift+R (Mac) / Ctrl+F5 (Windows)
- Firefox: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)
- Safari: Cmd+Option+R

**Check for JavaScript Errors:**
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for red error messages

---

Happy Coding! 🚀

