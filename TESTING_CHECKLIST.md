# Frontend Redesign - Testing Checklist

## Pre-Testing Setup
- [ ] Ensure application server is running
- [ ] Open browser to the application URL
- [ ] Clear browser cache if needed

## Initial Load Testing
- [ ] Page loads without console errors
- [ ] Welcome message is visible
- [ ] Form sidebar is visible and expanded
- [ ] All form fields are populated with default values
- [ ] "Run Screener" button is enabled
- [ ] "See Example" button is visible

## Example Loading Test
- [ ] Click "See Example" button
- [ ] Welcome message disappears
- [ ] Results container appears with 4 tabs
- [ ] Form automatically collapses
- [ ] Summary tab is active by default
- [ ] Logs appear at the bottom
- [ ] "Show raw JSON" button appears

## Tab Navigation Test
### Summary Tab
- [ ] Heatmap renders correctly
- [ ] Companies are listed as rows
- [ ] Themes are listed as columns
- [ ] Color scaling is visible (dark to emerald)
- [ ] Scores are displayed in cells
- [ ] Summary statistics cards show correct data
- [ ] Table is scrollable if needed
- [ ] Hover shows company/theme details

### Companies Tab
- [ ] Click "Companies" tab
- [ ] Company cards render with all information
- [ ] Search box is functional
- [ ] Sort dropdown works (all 4 options)
- [ ] Each card shows:
  - [ ] Company name and ticker
  - [ ] Industry
  - [ ] Composite score
- [ ] "Theme Scores" section expands/collapses
- [ ] Theme chips are color-coded
- [ ] "Key Insights" section expands/collapses
- [ ] Motivation text is readable

### Mindmap Tab
- [ ] Click "Mindmap" tab
- [ ] Tree View is shown by default
- [ ] Tree structure is hierarchical
- [ ] Nodes can be expanded/collapsed
- [ ] Node details are visible (label, summary, keywords)
- [ ] Click "Interactive Graph" button
- [ ] D3.js graph renders
- [ ] Nodes are draggable
- [ ] Zoom works (scroll wheel)
- [ ] Pan works (drag background)
- [ ] Hover shows tooltips
- [ ] Links connect parent-child nodes
- [ ] Switch back to Tree View works

### Evidence Tab
- [ ] Click "Evidence" tab
- [ ] Evidence table renders
- [ ] All columns are visible
- [ ] Company filter dropdown works
- [ ] Theme filter dropdown works
- [ ] Search box filters results
- [ ] Filter count updates correctly
- [ ] "Clear Filters" button works
- [ ] Pagination controls work
- [ ] Page numbers update correctly
- [ ] Headlines are clickable (show document modal)
- [ ] "Export CSV" button downloads file
- [ ] "Export JSON" button downloads file
- [ ] CSV file opens correctly in Excel/spreadsheet
- [ ] JSON file is valid JSON

## Form Collapse/Expand Test
- [ ] Click "Hide Form" button
- [ ] Form content collapses smoothly
- [ ] Button text changes to "Show Form"
- [ ] Icon rotates
- [ ] Click "Show Form" button
- [ ] Form content expands smoothly
- [ ] Button text changes to "Hide Form"
- [ ] Icon rotates back
- [ ] All form values are preserved

## Custom Screener Test
- [ ] Expand form if collapsed
- [ ] Modify theme field
- [ ] Modify focus field
- [ ] Select different company universe
- [ ] Adjust date range
- [ ] Click "Advanced Options"
- [ ] Modify frequency
- [ ] Click "Run Screener"
- [ ] Button text changes to "Waiting for response..."
- [ ] Button is disabled during processing
- [ ] Logs start appearing
- [ ] Results populate when complete
- [ ] Form collapses automatically
- [ ] All 4 tabs have data
- [ ] "Show raw JSON" button appears

## Error Handling Test
- [ ] Clear required field (e.g., theme)
- [ ] Try to submit form
- [ ] Error alert appears
- [ ] Form stays visible
- [ ] Set invalid date range (end before start)
- [ ] Try to submit form
- [ ] Validation error appears

## Modal Functionality Test
- [ ] Click info icon (ⓘ) next to any field
- [ ] Info modal appears
- [ ] Modal content is correct
- [ ] Click X to close modal
- [ ] Modal closes
- [ ] Click outside modal
- [ ] Modal closes
- [ ] Click "Show raw JSON" button
- [ ] JSON modal appears with formatted JSON
- [ ] Click "Copy" button
- [ ] Success message appears
- [ ] Close JSON modal

## Responsive Design Test
- [ ] Resize browser window to tablet size
- [ ] Layout adjusts appropriately
- [ ] Resize to mobile size
- [ ] All content is accessible
- [ ] Resize back to desktop
- [ ] Layout returns to normal

## Drag-to-Resize Test
- [ ] Hover over dragbar between sidebar and content
- [ ] Cursor changes to resize cursor
- [ ] Drag left to shrink sidebar
- [ ] Sidebar width decreases
- [ ] Drag right to expand sidebar
- [ ] Sidebar width increases (up to max)
- [ ] Form content reflows appropriately

## Browser Console Test
- [ ] Open browser developer console
- [ ] Check for any errors (should be none)
- [ ] Check for any warnings (note any found)
- [ ] Network tab shows successful requests
- [ ] No 404 errors for static files

## Performance Test
- [ ] Page loads quickly (< 2 seconds)
- [ ] Tab switching is instant
- [ ] Filters respond immediately
- [ ] Animations are smooth (60 FPS)
- [ ] Large datasets (50+ companies) render well
- [ ] Mindmap graph performs well with many nodes
- [ ] Evidence table pagination handles large datasets

## Accessibility Quick Check
- [ ] Tab through interactive elements
- [ ] Focus indicators are visible
- [ ] Buttons are keyboard accessible
- [ ] Form can be completed with keyboard only
- [ ] Color contrast is sufficient for text

## Cross-Browser Test (if possible)
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari
- [ ] All features work in each browser

## Data Integrity Test
- [ ] Compare heatmap scores with company cards
- [ ] Verify scores match across tabs
- [ ] Check evidence quotes match companies/themes
- [ ] Verify taxonomy structure is logical
- [ ] Export data matches displayed data

## Edge Cases
- [ ] Load with 0 companies (if possible)
- [ ] Load with 1 company
- [ ] Load with 100+ companies
- [ ] Load with very long company names
- [ ] Load with special characters in text
- [ ] Load with missing optional fields

## Final Verification
- [ ] All planned features are working
- [ ] No console errors
- [ ] No visual glitches
- [ ] User experience is smooth and intuitive
- [ ] Documentation is accurate
- [ ] Ready for production deployment

---

## Notes
Record any issues found during testing:

**Issues Found:**
1. 
2. 
3. 

**Browser-Specific Issues:**
1. 
2. 
3. 

**Performance Concerns:**
1. 
2. 
3. 

**Recommendations:**
1. 
2. 
3. 

