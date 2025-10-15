async function loadRequestId(requestId) {
    const showJsonBtn = document.getElementById('showJsonBtn');
    
    // Close config panel if open
    if (window.closeConfigPanel) {
        closeConfigPanel();
    }
    
    showJsonBtn.style.display = 'none';
    lastReport = null;
    
    // Reset frontend: hide empty state, clear dashboard
    const emptyState = document.getElementById('emptyState');
    const dashboardSection = document.getElementById('dashboardSection');
    const dashboardCards = document.getElementById('dashboardCards');
    
    if (emptyState) emptyState.style.display = 'none';
    if (dashboardSection) dashboardSection.classList.add('hidden');
    if (dashboardCards) dashboardCards.innerHTML = '';
    
    // Reset tabs
    if (window.tabController) {
        window.tabController.reset();
    }

    const params = new URLSearchParams();
    const token = getUrlParam('token');
    if (token) {
        params.append("token", token);
    }
    const logViewer = document.getElementById('logViewer');
    const statusResp = await fetch(`/status/${requestId}?${params}`);
    if (!statusResp.ok) {
        throw new Error(`Status HTTP error ${statusResp.status}`);
    }
    const statusData = await statusResp.json();
    // Render logs if available
    if (statusData.logs && Array.isArray(statusData.logs)) {
        logViewer.innerHTML = statusData.logs.map(line => {
            let base = 'mb-1';
            let color = '';
            if (line.toLowerCase().includes('error')) color = 'text-red-400';
            else if (line.toLowerCase().includes('success')) color = 'text-green-400';
            else if (line.toLowerCase().includes('info')) color = 'text-sky-400';
            return `<div class='${base} ${color}'>${line}</div>`;
        }).join('');
        logViewer.scrollTop = logViewer.scrollHeight;
    } else if (statusData.log) {
        logViewer.textContent = statusData.log;
    } else {
        logViewer.textContent = 'No logs yet.';
    }
    if (statusData.status === 'completed') {
        renderScreenerReport(statusData.report);
        showJsonBtn.style.display = 'inline-block';
        lastReport = statusData.report;
    }
};