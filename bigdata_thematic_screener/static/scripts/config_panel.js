// Configuration Panel - Sliding Side Panel
let currentConfig = {
    theme: '',
    focus: '',
    companies: '',
    start_date: '',
    end_date: ''
};

function toggleConfigPanel() {
    const panel = document.getElementById('configPanel');
    const backdrop = document.getElementById('configBackdrop');
    
    if (panel && backdrop) {
        const isOpen = !panel.classList.contains('translate-x-full');
        
        if (isOpen) {
            // Close
            panel.classList.add('translate-x-full');
            backdrop.classList.add('hidden');
            backdrop.classList.remove('opacity-100');
        } else {
            // Open
            panel.classList.remove('translate-x-full');
            backdrop.classList.remove('hidden');
            setTimeout(() => backdrop.classList.add('opacity-100'), 10);
        }
    }
}

function closeConfigPanel() {
    const panel = document.getElementById('configPanel');
    const backdrop = document.getElementById('configBackdrop');
    
    if (panel && backdrop) {
        panel.classList.add('translate-x-full');
        backdrop.classList.add('hidden');
        backdrop.classList.remove('opacity-100');
    }
}

function loadQuickStartTemplate(type) {
    const jsonFiles = {
        'supply-chain': {
            file: '/static/data/example.json',
            theme: 'Supply Chain Reshaping',
            universe: 'Top 100 US Companies'
        },
        'ai-automation': {
            file: '/static/data/example3.json',
            theme: 'AI & Automation',
            universe: 'Nasdaq 100'
        },
        'climate-tech': {
            file: '/static/data/example2.json',
            theme: 'Climate Technology',
            universe: 'Top 100 US Companies'
        }
    };
    
    const template = jsonFiles[type];
    if (template) {
        closeConfigPanel();
        
        // Show spinner
        const spinner = document.getElementById('spinner');
        if (spinner) spinner.classList.remove('hidden');
        
        fetch(template.file)
            .then(res => res.json())
            .then(data => {
                if (spinner) spinner.classList.add('hidden');
                
                // Store the report globally
                window.lastReport = data;
                
                // Update config badge with demo info
                if (window.updateConfigBadge) {
                    updateConfigBadge({
                        theme: template.theme,
                        companies: template.universe,
                        isDemo: true
                    });
                }
                
                // Show JSON button
                const showJsonBtn = document.getElementById('showJsonBtn');
                if (showJsonBtn) showJsonBtn.style.display = 'inline-block';
                
                // Render the report
                if (window.renderScreenerReport) {
                    renderScreenerReport(data);
                }
            })
            .catch(err => {
                if (spinner) spinner.classList.add('hidden');
                console.error('Error loading demo:', err);
                alert('Failed to load demo data: ' + err.message);
            });
    }
}

function updateConfigBadge(config) {
    currentConfig = { ...currentConfig, ...config };
    
    const badge = document.getElementById('currentConfigBadge');
    if (badge && currentConfig.theme) {
        const universe = getUniverseName(currentConfig.companies);
        const runTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        badge.innerHTML = `
            <div class="flex items-center gap-2 justify-between">
                <div class="truncate flex-1">
                    <span class="font-semibold text-blue-400">${escapeHtml(currentConfig.theme)}</span>
                    <span class="text-zinc-500 mx-1">|</span>
                    <span class="text-zinc-400">${escapeHtml(universe)}</span>
                </div>
                <span class="text-xs text-zinc-500 flex-shrink-0">${runTime}</span>
            </div>
        `;
        badge.title = `Theme: ${currentConfig.theme}\nUniverse: ${universe}\nLast run: ${runTime}`;
    }
}

function getUniverseName(universeId) {
    // Try to find the universe name from the watchlists
    if (window.watchlists) {
        const watchlist = window.watchlists.find(w => w.id === universeId);
        if (watchlist) return watchlist.name;
    }
    
    // Fallback to ID
    return universeId || 'Unknown';
}

// Initialize config panel on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Close panel when clicking backdrop
    const backdrop = document.getElementById('configBackdrop');
    if (backdrop) {
        backdrop.addEventListener('click', closeConfigPanel);
    }
    
    // Close panel on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeConfigPanel();
        }
    });
});

// Make functions globally accessible
window.toggleConfigPanel = toggleConfigPanel;
window.closeConfigPanel = closeConfigPanel;
window.loadQuickStartTemplate = loadQuickStartTemplate;
window.updateConfigBadge = updateConfigBadge;

