document.getElementById('screenerForm').onsubmit = async function (e) {
    e.preventDefault();
    const output = document.getElementById('output');
    const spinner = document.getElementById('spinner');
    const showJsonBtn = document.getElementById('showJsonBtn');
    const submitBtn = document.querySelector('button[type="submit"]');
    output.innerHTML = '';
    output.classList.remove('error');
    showJsonBtn.style.display = 'none';
    lastReport = null;

    // Validate date range first
    const startDateInput = document.getElementById('start_date').value;
    const endDateInput = document.getElementById('end_date').value;
    const frequencyInput = document.getElementById('frequency').value;

    const dateValidation = validateDateRange(startDateInput, endDateInput, frequencyInput);
    if (!dateValidation.isValid) {
        output.innerHTML = `<span class="error">❌ ${dateValidation.message}</span>`;
        output.classList.add('error');
        return;
    }

    // Disable the submit button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Waiting for response...';

    try {
        // Gather form data
        const theme = document.getElementById('theme').value.trim();
        const focus = document.getElementById('focus').value.trim();
        // Get companies and check if its available in the watchlists
        let companies = document.getElementById('companies_text').value.trim();
        const foundWatchlist = watchlists.find(w => w.name === companies);
        if (foundWatchlist) {
            companies = foundWatchlist.id;
        }
        else if (!companies) {
            output.innerHTML = `<span class="error">❌ Error: Company Universe is required.</span>`;
            output.classList.add('error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Run Screener';
            return;
        }
        const start_date = document.getElementById('start_date').value;
        const end_date = document.getElementById('end_date').value;
        let fiscal_year = document.getElementById('fiscal_year').value.trim();
        if (fiscal_year.includes(',')) {
            fiscal_year = fiscal_year.split(',').map(s => s.trim()).filter(Boolean);
            // Check if all entries are numbers
            if (!fiscal_year.every(yr => Number(yr))) {
                throw new Error('Fiscal Year must be a number or a comma-separated list of numbers.');
            }
        } else if (fiscal_year) {
            fiscal_year = fiscal_year;
        } else {
            fiscal_year = undefined;
        }

        const llm_model = document.getElementById('llm_model').value.trim();
        const document_type = document.getElementById('document_type').value;
        const rerank_threshold = document.getElementById('rerank_threshold').value;
        const frequency = document.getElementById('frequency').value;
        const document_limit = document.getElementById('document_limit').value;
        const batch_size = document.getElementById('batch_size').value;

        // Build request payload
        let payload = {
            theme,
            focus,
            focus,
            fiscal_year,
            llm_model,
            document_type,
            frequency,
            document_limit: document_limit ? parseInt(document_limit) : undefined,
            batch_size: batch_size ? parseInt(batch_size) : undefined
        };

        // A list of companies
        if (companies.includes(',')) {
            payload.companies = companies.split(',').map(s => s.trim()).filter(Boolean);
            // A single RP Entity ID
        } else if (companies.length === 6) {
            payload.companies = [companies];
            // A watchlist ID
        } else if (companies.length > 6) {
            payload.companies = companies;
        }

        if (start_date) payload.start_date = start_date;
        if (end_date) payload.end_date = end_date;
        if (rerank_threshold) payload.rerank_threshold = parseFloat(rerank_threshold);

        // Add token from URL param if present
        const params = new URLSearchParams();
        const token = getUrlParam('token');
        if (token) {
            params.append("token", token);
        }


        const response = await fetch(`/thematic-screener?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
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
                            output.innerHTML = renderScreenerReport(statusData.report)
                            showJsonBtn.style.display = 'inline-block';
                            lastReport = statusData.report;
                        }
                        spinner.style.display = 'none';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Run Screener';
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
        output.innerHTML = `<span class="error">❌ Error: ${err.message}</span>`;
        output.classList.add('error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Run Screener';
        spinner.style.display = 'none';
    }
};