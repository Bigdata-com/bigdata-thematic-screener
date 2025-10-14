function renderScreenerReport(data) {
    if (!data || typeof data !== 'object') {
        // Show empty state in all tabs
        if (window.tabController) {
            window.tabController.showEmptyState('summary', 'No data to display');
            window.tabController.showEmptyState('companies', 'No data to display');
            window.tabController.showEmptyState('mindmap', 'No data to display');
            window.tabController.showEmptyState('evidence', 'No data to display');
        }
        return;
    }

    // Hide empty state, show dashboard
    const emptyState = document.getElementById('emptyState');
    const dashboardSection = document.getElementById('dashboardSection');
    
    if (emptyState) emptyState.classList.add('hidden');
    if (dashboardSection) dashboardSection.classList.remove('hidden');

    // Render dashboard cards first (main insights)
    if (window.renderDashboardCards) {
        renderDashboardCards(data);
    }

    // Update configuration badge
    if (window.updateConfigBadge) {
        const form = document.getElementById('screenerForm');
        if (form) {
            const config = {
                theme: form.elements['theme']?.value || '',
                focus: form.elements['focus']?.value || '',
                companies: form.elements['companies']?.value || ''
            };
            updateConfigBadge(config);
        }
    }

    // Render exploration tabs (detailed views)
    try {
        // Summary tab - Heatmap
        if (data.theme_scoring) {
            window.tabController.setLoadingState('summary', false);
            renderHeatmap(data.theme_scoring);
        }

        // Companies tab - Company cards
        if (data.theme_scoring) {
            window.tabController.setLoadingState('companies', false);
            renderCompanyCards(data.theme_scoring);
        }

        // Mindmap tab - Taxonomy visualization
        if (data.theme_taxonomy) {
            window.tabController.setLoadingState('mindmap', false);
            renderMindmap(data.theme_taxonomy);
        }

        // Evidence tab - Filterable table
        if (data.content) {
            window.tabController.setLoadingState('evidence', false);
            renderEvidenceTable(data.content);
        }
    } catch (error) {
        console.error('Error rendering report:', error);
    }
}
