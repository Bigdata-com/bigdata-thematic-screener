document.getElementById('screenerForm').onsubmit = async function (e) {
    e.preventDefault();
    const spinner = document.getElementById('spinner');
    const showJsonBtn = document.getElementById('showJsonBtn');
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    const submitBtn = document.querySelector('button[type="submit"]');

    // Close config panel
    if (window.closeConfigPanel) {
        closeConfigPanel();
    }

    showJsonBtn.style.display = 'none';
    if (exportExcelBtn) exportExcelBtn.style.display = 'none';
    window.lastReport = null;

    // Reset frontend: hide results, show empty state, clear dashboard
    const emptyState = document.getElementById('emptyState');
    const dashboardSection = document.getElementById('dashboardSection');
    const dashboardCards = document.getElementById('dashboardCards');

    if (emptyState) emptyState.style.display = 'none';
    if (dashboardSection) dashboardSection.classList.add('hidden');
    if (dashboardCards) dashboardCards.innerHTML = '';

    // Open process logs
    const logViewerContainer = document.getElementById('logViewerContainer');
    const logsIcon = document.getElementById('logsIcon');
    if (logViewerContainer && logViewerContainer.classList.contains('hidden')) {
        logViewerContainer.classList.remove('hidden');
        if (logsIcon) logsIcon.style.transform = 'rotate(180deg)';
    }

    // Clear logs
    const logViewer = document.getElementById('logViewer');
    if (logViewer) logViewer.innerHTML = '<div class="text-zinc-400">Starting analysis...</div>';

    // Reset all tabs
    if (window.tabController) {
        window.tabController.reset();
    }

    // Validate date range first
    const startDateInput = document.getElementById('start_date').value;
    const endDateInput = document.getElementById('end_date').value;

    const dateValidation = validateDateRange(startDateInput, endDateInput);
    if (!dateValidation.isValid) {
        alert(`❌ ${dateValidation.message}`);
        return;
    }

    // Disable the submit button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    try {
        // Gather form data
        const theme = document.getElementById('theme').value.trim();
        const focus = document.getElementById('focus').value.trim();
        const companiesText = document.getElementById('companies_text').value.trim();
        const companiesFileInput = document.getElementById('companies_file');
        const companiesFile = companiesFileInput && companiesFileInput.files[0];

        if (!companiesFile && !companiesText) {
            alert('❌ Error: provide a comma-separated list of RP entity IDs, or upload a CSV.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Run Analysis';
            return;
        }

        const start_date = document.getElementById('start_date').value;
        const end_date = document.getElementById('end_date').value;
        const llm_model = document.getElementById('llm_model').value.trim();
        const rerank_threshold = document.getElementById('rerank_threshold').value;
        const chunk_percentage = document.getElementById('chunk_percentage').value;
        const max_leaf_labels = document.getElementById('max_leaf_labels').value;
        const max_taxonomy_depth = document.getElementById('max_taxonomy_depth').value;

        // Build the shared request payload (everything except the company universe)
        let payload = { theme, focus };
        if (start_date) payload.start_date = start_date;
        if (end_date) payload.end_date = end_date;
        if (llm_model) payload.llm_model = llm_model;
        if (rerank_threshold) payload.rerank_threshold = parseFloat(rerank_threshold);
        // The field is entered as a percentage (0-100) in the UI; the API expects a 0-1 fraction.
        if (chunk_percentage) payload.chunk_percentage = parseFloat(chunk_percentage) / 100;
        if (max_leaf_labels) payload.max_leaf_labels = parseInt(max_leaf_labels);
        if (max_taxonomy_depth) payload.max_taxonomy_depth = parseInt(max_taxonomy_depth);

        // Add token from URL param if present
        const params = new URLSearchParams();
        const token = getUrlParam('token');
        if (token) {
            params.append("token", token);
        }

        let response;
        if (companiesFile) {
            const formData = new FormData();
            formData.append('file', companiesFile);
            formData.append('request', JSON.stringify(payload));
            response = await fetch(`/thematic-screener/upload?${params}`, {
                method: 'POST',
                body: formData
            });
        } else {
            payload.companies = companiesText.split(',').map(s => s.trim()).filter(Boolean);
            response = await fetch(`/thematic-screener?${params}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }
        if (!response.ok) {
            const errorData = await response.json();
            // Iterate over errorData.detail if it's an array show the loc and msg fields
            if (errorData.detail && Array.isArray(errorData.detail)) {
                const messages = errorData.detail.map(err => {
                    if (err.loc && err.loc.length > 1) {
                        return `${err.loc.join(', ')}: ${err.msg}`;
                    } else {
                        return err.msg;
                    }
                }).join('<br>');
                throw new Error('Form submission error:<br>' + messages);
            }
            throw new Error(`HTTP error ${response.status}`);
        }
        const data = await response.json();
        // Start polling status endpoint every 5 seconds using request_id
        if (data && data.request_id) {
            const requestId = data.request_id;
            let polling = true;
            const logViewer = document.getElementById('logViewer');
            async function pollStatus() {

                try {
                    const statusResp = await fetch(`/status/${requestId}?${params}`);
                    if (!statusResp.ok) {
                        throw new Error(`Status HTTP error ${statusResp.status}`);
                    }
                    const statusData = await statusResp.json();
                    spinner.style.display = 'block';
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
                    // Stop polling if status is 'completed' or 'failed'
                    if (statusData.status === 'completed' || statusData.status === 'failed') {
                        polling = false;
                        if (statusData.status === 'completed') {
                            // Update config badge BEFORE rendering so dashboard has access to it
                            if (window.updateConfigBadge) {
                                updateConfigBadge({
                                    theme: theme,
                                    companies: companiesFile ? companiesFile.name : (companiesText || 'Custom Universe'),
                                    isDemo: false
                                });
                            }

                            window.lastReport = statusData.report;
                            renderScreenerReport(statusData.report);
                            showJsonBtn.style.display = 'inline-block';
                            if (exportExcelBtn) exportExcelBtn.style.display = 'inline-block';
                        }
                        spinner.style.display = 'none';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Run Analysis';
                        return;
                    }
                } catch (err) {
                    logViewer.innerHTML = `<div class=\"log-line log-error\">❌ Status Error: ${err.message}</div>`;
                }
                if (polling) {
                    setTimeout(pollStatus, 5000);
                }
            }
            pollStatus();
        }
    } catch (err) {
        alert(`❌ Error: ${err.message}`);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Run Analysis';
        spinner.style.display = 'none';
    }
};
