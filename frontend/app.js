// =============================================================================
// OSINT OA - Frontend Application
// =============================================================================

/**
 * API Configuration
 */
const API_BASE = '/api';

/**
 * State
 */
let currentRunId = null;
let autoRefreshInterval = null;
let deleteRunId = null;

// =============================================================================
// Markdown Rendering
// =============================================================================

/**
 * Configure marked.js for secure Markdown rendering
 */
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });
}

/**
 * Render Markdown to safe HTML
 */
function renderMarkdown(text) {
    if (!text) return '';
    
    try {
        // Parse markdown
        const html = typeof marked !== 'undefined' ? marked.parse(text) : text;
        
        // Sanitize HTML if DOMPurify is available
        if (typeof DOMPurify !== 'undefined') {
            return DOMPurify.sanitize(html, {
                ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr', 
                              'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre', 
                              'blockquote', 'a', 'table', 'thead', 'tbody', 'tr', 
                              'th', 'td', 'span', 'div'],
                ALLOWED_ATTR: ['href', 'target', 'rel', 'class']
            });
        }
        
        return html;
    } catch (e) {
        console.error('Markdown rendering error:', e);
        return escapeHtml(text);
    }
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Make an API request
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    const config = {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options,
    };

    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    
    try {
        const date = new Date(dateStr);
        return date.toLocaleString();
    } catch {
        return dateStr;
    }
}

/**
 * Show status message
 */
function showStatus(elementId, message, type = 'info') {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    el.className = `status-message ${type}`;
    el.textContent = message;
    el.classList.remove('hidden');
    
    if (type === 'success') {
        setTimeout(() => el.classList.add('hidden'), 5000);
    }
}

/**
 * Hide status message
 */
function hideStatus(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.add('hidden');
}

/**
 * Truncate text
 */
function truncate(text, maxLength = 100) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// =============================================================================
// Runs (Investigations)
// =============================================================================

/**
 * Load and display runs
 */
async function loadRuns(filters = {}) {
    const container = document.getElementById('runsList');
    container.innerHTML = '<p class="loading">Loading...</p>';
    
    try {
        // Build query string
        const params = new URLSearchParams();
        if (filters.q) params.set('q', filters.q);
        if (filters.status) params.set('status', filters.status);
        if (filters.since) params.set('since', filters.since);
        if (filters.until) params.set('until', filters.until);
        
        const queryStr = params.toString() ? `?${params.toString()}` : '';
        const data = await apiRequest(`/runs${queryStr}`);
        
        if (!data.runs || data.runs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>No investigations found</p>
                    <p>Start a new collection above</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.runs.map(run => {
            const canContinue = run.status === 'completed' || run.status === 'partial';
            const continueButton = canContinue 
                ? `<button class="btn btn-sm btn-primary" onclick="showContinueModal(${run.id}, '${escapeHtml(run.query).replace(/'/g, "\\'")}')">▶ Continue</button>`
                : '';
            
            return `
                <div class="run-item" data-run-id="${run.id}">
                    <span class="run-id">#${run.id}</span>
                    <span class="run-query">${escapeHtml(truncate(run.query, 50))}</span>
                    <span class="run-status ${run.status}">${run.status}</span>
                    <span class="run-date">${formatDate(run.started_at)}</span>
                    <div class="run-actions">
                        ${continueButton}
                        <button class="btn btn-sm btn-secondary" onclick="viewRun(${run.id})">View</button>
                        <button class="btn btn-sm btn-outline" onclick="showDeleteModal(${run.id})">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        container.innerHTML = `<p class="status-message error">Error loading runs: ${error.message}</p>`;
    }
}

/**
 * View run detail
 */
async function viewRun(runId) {
    currentRunId = runId;
    
    const detailSection = document.getElementById('runDetail');
    const contentEl = document.getElementById('runDetailContent');
    const itemsSection = document.getElementById('itemsSection');
    
    detailSection.classList.remove('hidden');
    contentEl.innerHTML = '<p class="loading">Loading...</p>';
    
    try {
        const run = await apiRequest(`/runs/${runId}`);
        
        // Parse stats if available
        let stats = {};
        if (run.stats_json) {
            try {
                stats = JSON.parse(run.stats_json);
            } catch {}
        }
        
        contentEl.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <label>Query</label>
                    <div class="value">${escapeHtml(run.query)}</div>
                </div>
                <div class="detail-item">
                    <label>Status</label>
                    <div class="value"><span class="run-status ${run.status}">${run.status}</span></div>
                </div>
                <div class="detail-item">
                    <label>Started</label>
                    <div class="value">${formatDate(run.started_at)}</div>
                </div>
                <div class="detail-item">
                    <label>Finished</label>
                    <div class="value">${formatDate(run.finished_at)}</div>
                </div>
                <div class="detail-item">
                    <label>Items Count</label>
                    <div class="value">${run.items_count || 0}</div>
                </div>
                <div class="detail-item">
                    <label>Scope</label>
                    <div class="value">${escapeHtml(run.scope || 'None')}</div>
                </div>
            </div>
            ${run.report ? `
                <div class="report-section">
                    <h4>📄 Report</h4>
                    <div class="report-content markdown-body">${renderMarkdown(run.report.report || run.report.summary || 'No report available')}</div>
                    ${run.report.telegram_message_id ? 
                        `<p class="telegram-published">✅ Published to Telegram</p>` : ''}
                </div>
            ` : ''}
            
            <div class="run-detail-actions">
                <button class="btn btn-secondary" onclick="loadTraces(${runId})">
                    🔬 View Execution Traces
                </button>
                ${run.status === 'completed' || run.status === 'partial' ? `
                    <button class="btn continue-btn" onclick="showContinueModal(${runId}, '${escapeHtml(run.query).replace(/'/g, "\\'")}')">
                        🔄 Continue Investigation
                    </button>
                ` : ''}
                <button class="btn btn-danger" onclick="showDeleteModal(${runId})">
                    🗑️ Delete
                </button>
            </div>
        `;
        
        // Load items for this run
        loadItems(runId);
        
        // Scroll to detail
        detailSection.scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        contentEl.innerHTML = `<p class="status-message error">Error loading run: ${error.message}</p>`;
    }
}

/**
 * Close run detail view
 */
function closeDetail() {
    document.getElementById('runDetail').classList.add('hidden');
    document.getElementById('itemsSection').classList.add('hidden');
    currentRunId = null;
}

// =============================================================================
// Evidence Items (Extracted from Report)
// =============================================================================

/**
 * Extract findings from report markdown
 */
function extractFindingsFromReport(reportText) {
    if (!reportText) return [];
    
    const findings = [];
    const lines = reportText.split('\n');
    
    let currentSection = '';
    let currentFinding = null;
    
    for (const line of lines) {
        // Detect section headers
        if (line.match(/^##\s+(.+)/)) {
            currentSection = line.replace(/^##\s+/, '').trim();
            continue;
        }
        
        // Detect numbered findings or bullet points with links
        const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
        const bulletMatch = line.match(/^[\-\*\d\.]+\s+\*?\*?([^*]+)\*?\*?/);
        
        if (linkMatch) {
            findings.push({
                title: linkMatch[1],
                url: linkMatch[2],
                section: currentSection,
                description: line.replace(/\[([^\]]+)\]\([^)]+\)/, '').replace(/^[\-\*\d\.]+\s+/, '').trim()
            });
        } else if (bulletMatch && currentSection.toLowerCase().includes('finding')) {
            // Capture findings from "Key Findings" section
            const title = bulletMatch[1].replace(/\*\*/g, '').trim();
            if (title.length > 10) {
                findings.push({
                    title: title.substring(0, 80),
                    section: currentSection,
                    description: line.replace(/^[\-\*\d\.]+\s+/, '').trim()
                });
            }
        }
    }
    
    // Also extract IOCs from markdown tables
    const iocTableMatch = reportText.match(/\|.*Type.*\|.*Value.*\|[\s\S]*?(?=\n\n|\n##|$)/i);
    if (iocTableMatch) {
        const tableLines = iocTableMatch[0].split('\n').filter(l => l.includes('|') && !l.includes('---'));
        for (let i = 1; i < tableLines.length; i++) {
            const cols = tableLines[i].split('|').map(c => c.trim()).filter(c => c);
            if (cols.length >= 2) {
                findings.push({
                    title: `IOC: ${cols[1]}`,
                    section: 'Indicators of Compromise',
                    type: cols[0],
                    description: cols[2] || '',
                    isIOC: true
                });
            }
        }
    }
    
    return findings.slice(0, 20); // Limit to 20 items
}

/**
 * Load items for a run - now extracts from report
 */
async function loadItems(runId) {
    const section = document.getElementById('itemsSection');
    const container = document.getElementById('itemsList');
    
    section.classList.remove('hidden');
    container.innerHTML = '<p class="loading">Loading evidence...</p>';
    
    try {
        // First try to get traditional items
        const data = await apiRequest(`/items?run_id=${runId}&limit=50`);
        
        if (data.items && data.items.length > 0) {
            // Traditional items exist
            renderTraditionalItems(container, data.items);
            return;
        }
        
        // No traditional items - extract from report
        const run = await apiRequest(`/runs/${runId}`);
        const reportText = run.report?.report || run.report?.summary || '';
        
        if (!reportText) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No evidence collected yet</p>
                    <p class="hint">Evidence will appear once the investigation completes</p>
                </div>
            `;
            return;
        }
        
        const findings = extractFindingsFromReport(reportText);
        
        if (findings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>Report generated without structured findings</p>
                    <p class="hint">View the full report above for details</p>
                </div>
            `;
            return;
        }
        
        // Render extracted findings
        container.innerHTML = findings.map((item, idx) => `
            <div class="item-card finding-card ${item.isIOC ? 'ioc-card' : ''}" style="animation-delay: ${idx * 0.05}s">
                <div class="item-content">
                    <div class="item-section-badge">${escapeHtml(item.section || 'Finding')}</div>
                    <h3 class="item-title">
                        ${item.url ? 
                            `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
                                ${escapeHtml(truncate(item.title, 80))}
                            </a>` : 
                            escapeHtml(truncate(item.title, 80))
                        }
                    </h3>
                    ${item.description ? `<p class="item-summary">${escapeHtml(truncate(item.description, 150))}</p>` : ''}
                    ${item.isIOC ? `<span class="ioc-badge">${escapeHtml(item.type || 'IOC')}</span>` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        container.innerHTML = `<p class="status-message error">Error loading evidence: ${getErrorMessage(error)}</p>`;
    }
}

/**
 * Render traditional items (legacy format)
 */
function renderTraditionalItems(container, items) {
    container.innerHTML = items.map((item, idx) => `
        <div class="item-card" style="animation-delay: ${idx * 0.05}s">
            ${item.image_url ? `<img src="${escapeHtml(item.image_url)}" alt="" class="item-image" onerror="this.style.display='none'">` : ''}
            <div class="item-content">
                <h3 class="item-title">
                    <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
                        ${escapeHtml(truncate(item.title, 80))}
                    </a>
                </h3>
                <p class="item-summary">${escapeHtml(truncate(item.summary, 150))}</p>
                <div class="item-meta">
                    <span class="item-source">${escapeHtml(item.source_name || 'Unknown')}</span>
                    <span class="item-date">${formatDate(item.published_at)}</span>
                </div>
                ${item.tags && item.tags.length ? `
                    <div class="item-tags">
                        ${item.tags.slice(0, 5).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// =============================================================================
// Collection
// =============================================================================

/**
 * Get user-friendly error message
 */
function getErrorMessage(error) {
    const message = error.message || String(error);
    
    // Map common errors to user-friendly messages
    const errorMappings = {
        'database is read-only': '⚠️ Database permission error. Please contact administrator.',
        'database_readonly': '⚠️ Database permission error. Please contact administrator.',
        'database not initialized': '⚠️ Database not ready. Please restart the application.',
        'database_not_initialized': '⚠️ Database not ready. Please restart the application.',
        'database is busy': '⏳ Server is busy. Please try again in a moment.',
        'database_locked': '⏳ Server is busy. Please try again in a moment.',
        'failed to fetch': '🔌 Connection error. Please check your network.',
        'network error': '🔌 Connection error. Please check your network.',
        'internal server error': '🔧 Server error. Please try again later.',
    };
    
    const lowerMessage = message.toLowerCase();
    for (const [key, friendlyMessage] of Object.entries(errorMappings)) {
        if (lowerMessage.includes(key)) {
            return friendlyMessage;
        }
    }
    
    return message;
}

/**
 * Start a new collection
 */
async function startCollection(formData) {
    const btn = document.getElementById('collectBtn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Collecting...';
    hideStatus('collectStatus');
    
    try {
        const payload = {
            query: formData.query,
            limit: parseInt(formData.limit) || 20,
        };
        
        if (formData.since) payload.since = formData.since;
        if (formData.scope) payload.scope = formData.scope;
        if (formData.agents) payload.agents = formData.agents;
        
        const result = await apiRequest('/collect', {
            method: 'POST',
            body: payload,
        });
        
        // Build status message based on result
        let statusMsg = `✅ Collection complete! Run #${result.run_id}: `;
        
        if (result.status === 'partial') {
            statusMsg = `⚠️ Partial completion. Run #${result.run_id}: `;
            const meta = result.investigation?.metadata || {};
            statusMsg += `${meta.agents_succeeded || 0} agents succeeded, ${meta.agents_failed || 0} failed. `;
        }
        
        statusMsg += result.report?.telegram_published ? 'Report published to Telegram.' : '';
        
        const statusType = result.status === 'partial' ? 'warning' : 
                          result.status === 'failed' ? 'error' : 'success';
        
        showStatus('collectStatus', statusMsg, statusType);
        
        // Refresh runs list
        loadRuns();
        
        // View the new run
        setTimeout(() => viewRun(result.run_id), 500);
        
    } catch (error) {
        showStatus('collectStatus', `❌ Collection failed: ${getErrorMessage(error)}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// =============================================================================
// Delete
// =============================================================================

/**
 * Show delete confirmation modal
 */
function showDeleteModal(runId) {
    deleteRunId = runId;
    document.getElementById('deleteModal').classList.remove('hidden');
}

/**
 * Hide delete modal
 */
function hideDeleteModal() {
    deleteRunId = null;
    document.getElementById('deleteModal').classList.add('hidden');
}

/**
 * Confirm and delete run
 */
async function confirmDelete() {
    if (!deleteRunId) return;
    
    try {
        await apiRequest(`/runs/${deleteRunId}`, { method: 'DELETE' });
        
        hideDeleteModal();
        
        // Close detail if viewing the deleted run
        if (currentRunId === deleteRunId) {
            closeDetail();
        }
        
        // Refresh list
        loadRuns();
        
    } catch (error) {
        alert(`Failed to delete: ${error.message}`);
    }
}

// =============================================================================
// Continue Investigation
// =============================================================================

let continueRunId = null;
let continueRunQuery = null;

/**
 * Show continue investigation modal
 */
function showContinueModal(runId, query) {
    continueRunId = runId;
    continueRunQuery = query;
    
    document.getElementById('continueRunId').value = runId;
    document.getElementById('continueFromQuery').textContent = query;
    document.getElementById('newInstructions').value = '';
    document.getElementById('continueDepth').value = 'standard';
    document.getElementById('continueAgentModeAuto').checked = true;
    document.getElementById('continueAgentCheckboxes').classList.add('hidden');
    
    // Uncheck all agents
    document.querySelectorAll('input[name="continueAgents"]').forEach(cb => cb.checked = false);
    
    // Load previous IOCs if available
    loadPreviousIocs(runId);
    
    document.getElementById('continueModal').classList.remove('hidden');
}

/**
 * Hide continue modal
 */
function hideContinueModal() {
    continueRunId = null;
    continueRunQuery = null;
    document.getElementById('continueModal').classList.add('hidden');
}

/**
 * Load previous IOCs from a run for selection
 */
async function loadPreviousIocs(runId) {
    const section = document.getElementById('previousIocsSection');
    const container = document.getElementById('previousIocs');
    
    try {
        // Try to get traces with evidence
        const traces = await apiRequest(`/runs/${runId}/traces?include_data=true`);
        
        // Extract IOCs from traces
        const iocs = new Map(); // Use Map to deduplicate
        
        if (traces && Array.isArray(traces)) {
            for (const trace of traces) {
                if (trace.evidence && Array.isArray(trace.evidence)) {
                    for (const ev of trace.evidence) {
                        if (ev.type && ev.value) {
                            const key = `${ev.type}:${ev.value}`;
                            if (!iocs.has(key)) {
                                iocs.set(key, { type: ev.type, value: ev.value });
                            }
                        }
                    }
                }
            }
        }
        
        if (iocs.size > 0) {
            container.innerHTML = Array.from(iocs.values()).slice(0, 20).map(ioc => `
                <label class="evidence-item">
                    <input type="checkbox" name="selectedIocs" value="${escapeHtml(ioc.value)}">
                    <span class="ioc-type">[${escapeHtml(ioc.type)}]</span>
                    <span class="ioc-value">${escapeHtml(ioc.value)}</span>
                </label>
            `).join('');
            section.classList.remove('hidden');
        } else {
            container.innerHTML = '<p class="hint">No IOCs found in previous investigation.</p>';
            section.classList.add('hidden');
        }
    } catch (error) {
        console.warn('Could not load previous IOCs:', error);
        section.classList.add('hidden');
    }
}

/**
 * Submit continue investigation request
 */
async function submitContinueInvestigation() {
    if (!continueRunId) return;
    
    const btn = document.getElementById('confirmContinue');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Continuing...';
    
    try {
        const payload = {
            new_instructions: document.getElementById('newInstructions').value,
            depth: document.getElementById('continueDepth').value,
        };
        
        // Check if manual agent selection
        const autoMode = document.getElementById('continueAgentModeAuto');
        if (!autoMode.checked) {
            const selectedAgents = Array.from(
                document.querySelectorAll('input[name="continueAgents"]:checked')
            ).map(cb => cb.value);
            
            if (selectedAgents.length === 0) {
                alert('Please select at least one agent or enable auto mode.');
                btn.disabled = false;
                btn.innerHTML = originalText;
                return;
            }
            
            payload.agents = selectedAgents;
        }
        
        // Get selected IOCs
        const selectedIocs = Array.from(
            document.querySelectorAll('input[name="selectedIocs"]:checked')
        ).map(cb => cb.value);
        
        if (selectedIocs.length > 0) {
            payload.selected_iocs = selectedIocs;
        }
        
        const result = await apiRequest(`/runs/${continueRunId}/continue`, {
            method: 'POST',
            body: payload,
        });
        
        hideContinueModal();
        
        // Show success message
        let statusMsg = `✅ Continued investigation started! New Run #${result.run_id}`;
        if (result.status === 'partial') {
            statusMsg = `⚠️ Continuation partial. New Run #${result.run_id}`;
        }
        
        showStatus('collectStatus', statusMsg, result.status === 'partial' ? 'warning' : 'success');
        
        // Refresh runs list and view new run
        loadRuns();
        setTimeout(() => viewRun(result.run_id), 500);
        
    } catch (error) {
        alert(`Continue failed: ${getErrorMessage(error)}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// =============================================================================
// Auto Refresh
// =============================================================================

/**
 * Toggle auto refresh
 */
function toggleAutoRefresh(enabled) {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    
    if (enabled) {
        autoRefreshInterval = setInterval(() => {
            loadRuns(getCurrentFilters());
        }, 60000); // 60 seconds
    }
}

/**
 * Get current filter values
 */
function getCurrentFilters() {
    return {
        q: document.getElementById('filterQ').value,
        status: document.getElementById('filterStatus').value,
        since: document.getElementById('filterSince').value,
        until: document.getElementById('filterUntil').value,
    };
}

/**
 * Clear filters
 */
function clearFilters() {
    document.getElementById('filterQ').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterSince').value = '';
    document.getElementById('filterUntil').value = '';
    loadRuns();
}

// =============================================================================
// Utility
// =============================================================================

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// Event Listeners
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    loadRuns();
    
    // Agent mode toggle
    const agentModeAuto = document.getElementById('agentModeAuto');
    const agentCheckboxes = document.getElementById('agentCheckboxes');
    
    if (agentModeAuto && agentCheckboxes) {
        agentModeAuto.addEventListener('change', (e) => {
            if (e.target.checked) {
                agentCheckboxes.classList.add('hidden');
            } else {
                agentCheckboxes.classList.remove('hidden');
            }
        });
    }
    
    // Select/Deselect all agents
    const selectAllBtn = document.getElementById('selectAllAgents');
    const deselectAllBtn = document.getElementById('deselectAllAgents');
    
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="agents"]').forEach(cb => cb.checked = true);
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="agents"]').forEach(cb => cb.checked = false);
        });
    }
    
    // Collection form
    document.getElementById('collectForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Build form data
        const formData = {
            query: document.getElementById('query').value,
            limit: document.getElementById('limit').value,
            since: document.getElementById('since').value,
            scope: document.getElementById('scope').value,
        };
        
        // Check if auto mode is disabled (manual agent selection)
        const autoMode = document.getElementById('agentModeAuto');
        if (autoMode && !autoMode.checked) {
            const selectedAgents = Array.from(
                document.querySelectorAll('input[name="agents"]:checked')
            ).map(cb => cb.value);
            
            if (selectedAgents.length === 0) {
                showStatus('collectStatus', '⚠️ Please select at least one agent or enable auto mode.', 'warning');
                return;
            }
            
            formData.agents = selectedAgents;
        }
        
        await startCollection(formData);
        e.target.reset();
        
        // Reset agent mode to auto after submission
        if (agentModeAuto) {
            agentModeAuto.checked = true;
            agentCheckboxes.classList.add('hidden');
        }
    });
    
    // Filter form
    document.getElementById('filterForm').addEventListener('submit', (e) => {
        e.preventDefault();
        loadRuns(getCurrentFilters());
    });
    
    // Clear filters
    document.getElementById('clearFilters').addEventListener('click', clearFilters);
    
    // Close detail
    document.getElementById('closeDetail').addEventListener('click', closeDetail);
    
    // Delete modal
    document.getElementById('cancelDelete').addEventListener('click', hideDeleteModal);
    document.getElementById('confirmDelete').addEventListener('click', confirmDelete);
    
    // Close modal on backdrop click
    document.getElementById('deleteModal').addEventListener('click', (e) => {
        if (e.target.id === 'deleteModal') hideDeleteModal();
    });
    
    // Continue investigation modal
    const continueAgentModeAuto = document.getElementById('continueAgentModeAuto');
    const continueAgentCheckboxes = document.getElementById('continueAgentCheckboxes');
    
    if (continueAgentModeAuto && continueAgentCheckboxes) {
        continueAgentModeAuto.addEventListener('change', (e) => {
            if (e.target.checked) {
                continueAgentCheckboxes.classList.add('hidden');
            } else {
                continueAgentCheckboxes.classList.remove('hidden');
            }
        });
    }
    
    document.getElementById('cancelContinue').addEventListener('click', hideContinueModal);
    document.getElementById('continueForm').addEventListener('submit', (e) => {
        e.preventDefault();
        submitContinueInvestigation();
    });
    
    // Close continue modal on backdrop click
    document.getElementById('continueModal').addEventListener('click', (e) => {
        if (e.target.id === 'continueModal') hideContinueModal();
    });
    
    // Auto refresh toggle
    document.getElementById('autoRefresh').addEventListener('change', (e) => {
        toggleAutoRefresh(e.target.checked);
    });
});

// Expose functions to global scope for onclick handlers
window.viewRun = viewRun;
window.showDeleteModal = showDeleteModal;
window.showContinueModal = showContinueModal;
window.loadTraces = loadTraces;
window.viewTraceDetail = viewTraceDetail;
window.closeTraceDetail = closeTraceDetail;


// =============================================================================
// Traces (Execution Traceability)
// =============================================================================

let showFullTraceData = false;

/**
 * Load and display traces for a run
 */
async function loadTraces(runId) {
    const section = document.getElementById('tracesSection');
    const summaryContainer = document.getElementById('tracesSummary');
    const timelineContainer = document.getElementById('tracesTimeline');
    
    section.classList.remove('hidden');
    summaryContainer.innerHTML = '<p class="loading">Loading traces...</p>';
    timelineContainer.innerHTML = '';
    
    try {
        // Load summary
        const summary = await apiRequest(`/runs/${runId}/traces/summary`);
        renderTracesSummary(summary, summaryContainer);
        
        // Load traces
        const data = await apiRequest(`/runs/${runId}/traces`);
        renderTracesTimeline(data.traces, timelineContainer);
        
        // Scroll to traces
        section.scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        summaryContainer.innerHTML = `<p class="status-message error">Error loading traces: ${error.message}</p>`;
    }
}

/**
 * Render traces summary
 */
function renderTracesSummary(summary, container) {
    const totalDuration = summary.total_duration_ms ? (summary.total_duration_ms / 1000).toFixed(2) : '0';
    const avgConfidence = summary.avg_confidence ? (summary.avg_confidence * 100).toFixed(0) : 'N/A';
    
    container.innerHTML = `
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-value">${summary.total_traces || 0}</div>
                <div class="summary-label">Total Traces</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">${summary.total_evidence || 0}</div>
                <div class="summary-label">Evidence Found</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">${avgConfidence}%</div>
                <div class="summary-label">Avg Confidence</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">${totalDuration}s</div>
                <div class="summary-label">Total Duration</div>
            </div>
            <div class="summary-card ${summary.failed_traces > 0 ? 'error' : ''}">
                <div class="summary-value">${summary.completed_traces || 0}/${summary.total_traces || 0}</div>
                <div class="summary-label">Completed</div>
            </div>
        </div>
        
        ${summary.by_agent && summary.by_agent.length > 0 ? `
            <div class="summary-agents">
                <h4>By Agent</h4>
                <div class="agent-chips">
                    ${summary.by_agent.map(a => `
                        <span class="agent-chip">
                            ${escapeHtml(a.agent_name || 'Unknown')}: ${a.trace_count} traces, ${a.evidence_count || 0} evidence
                        </span>
                    `).join('')}
                </div>
            </div>
        ` : ''}
        
        ${summary.by_tool && summary.by_tool.length > 0 ? `
            <div class="summary-tools">
                <h4>By Tool</h4>
                <div class="tool-chips">
                    ${summary.by_tool.map(t => `
                        <span class="tool-chip">
                            ${escapeHtml(t.tool_name || 'Unknown')}: ${t.trace_count}x 
                            (avg ${t.avg_duration_ms ? (t.avg_duration_ms / 1000).toFixed(2) : '0'}s)
                        </span>
                    `).join('')}
                </div>
            </div>
        ` : ''}
    `;
}

/**
 * Render traces timeline
 */
function renderTracesTimeline(traces, container) {
    if (!traces || traces.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No traces recorded for this investigation</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="timeline">
            ${traces.map((trace, idx) => renderTraceItem(trace, idx)).join('')}
        </div>
    `;
}

/**
 * Render a single trace item
 */
function renderTraceItem(trace, index) {
    const statusClass = getTraceStatusClass(trace.status);
    const typeIcon = getTraceTypeIcon(trace.trace_type);
    const duration = trace.duration_ms ? (trace.duration_ms / 1000).toFixed(2) : '-';
    
    return `
        <div class="timeline-item ${statusClass}" data-trace-id="${trace.id}">
            <div class="timeline-marker">
                <span class="timeline-number">${index + 1}</span>
            </div>
            <div class="timeline-content">
                <div class="trace-header">
                    <span class="trace-icon">${typeIcon}</span>
                    <span class="trace-type">${escapeHtml(trace.trace_type)}</span>
                    <span class="trace-status ${statusClass}">${trace.status}</span>
                    ${trace.duration_ms ? `<span class="trace-duration">${duration}s</span>` : ''}
                </div>
                
                <div class="trace-info">
                    ${trace.agent_name ? `<span class="trace-agent">🤖 ${escapeHtml(trace.agent_name)}</span>` : ''}
                    ${trace.tool_name ? `<span class="trace-tool">🔧 ${escapeHtml(trace.tool_name)}</span>` : ''}
                </div>
                
                ${trace.instruction ? `
                    <div class="trace-instruction">
                        <strong>Instruction:</strong> ${escapeHtml(truncate(trace.instruction, 200))}
                    </div>
                ` : ''}
                
                ${trace.reasoning ? `
                    <div class="trace-reasoning">
                        <strong>Reasoning:</strong> ${escapeHtml(truncate(trace.reasoning, 200))}
                    </div>
                ` : ''}
                
                ${trace.evidence_count > 0 ? `
                    <div class="trace-evidence">
                        <span class="evidence-badge">📋 ${trace.evidence_count} evidence items</span>
                        ${trace.confidence_score ? `<span class="confidence-badge">${(trace.confidence_score * 100).toFixed(0)}% confidence</span>` : ''}
                    </div>
                ` : ''}
                
                ${trace.error_message ? `
                    <div class="trace-error">
                        <strong>Error:</strong> ${escapeHtml(truncate(trace.error_message, 200))}
                    </div>
                ` : ''}
                
                <div class="trace-actions">
                    <button class="btn btn-outline btn-sm" onclick="viewTraceDetail(${trace.run_id}, ${trace.id})">
                        View Details
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Get CSS class for trace status
 */
function getTraceStatusClass(status) {
    const statusMap = {
        'pending': 'pending',
        'running': 'running',
        'completed': 'completed',
        'failed': 'failed',
        'skipped': 'skipped'
    };
    return statusMap[status] || '';
}

/**
 * Get icon for trace type
 */
function getTraceTypeIcon(type) {
    const iconMap = {
        'tool_call': '🔧',
        'agent_action': '🤖',
        'llm_reasoning': '💭',
        'decision': '🎯',
        'error': '❌',
        'checkpoint': '📍'
    };
    return iconMap[type] || '📝';
}

/**
 * View trace detail
 */
async function viewTraceDetail(runId, traceId) {
    const modal = document.getElementById('traceDetailModal');
    const body = document.getElementById('traceDetailBody');
    
    modal.classList.remove('hidden');
    body.innerHTML = '<p class="loading">Loading...</p>';
    
    try {
        const trace = await apiRequest(`/runs/${runId}/traces/${traceId}`);
        
        body.innerHTML = `
            <div class="trace-detail-grid">
                <div class="detail-row">
                    <label>Type</label>
                    <div>${getTraceTypeIcon(trace.trace_type)} ${escapeHtml(trace.trace_type)}</div>
                </div>
                <div class="detail-row">
                    <label>Status</label>
                    <div class="trace-status ${getTraceStatusClass(trace.status)}">${trace.status}</div>
                </div>
                ${trace.agent_name ? `
                    <div class="detail-row">
                        <label>Agent</label>
                        <div>🤖 ${escapeHtml(trace.agent_name)}</div>
                    </div>
                ` : ''}
                ${trace.tool_name ? `
                    <div class="detail-row">
                        <label>Tool</label>
                        <div>🔧 ${escapeHtml(trace.tool_name)}</div>
                    </div>
                ` : ''}
                <div class="detail-row">
                    <label>Duration</label>
                    <div>${trace.duration_ms ? (trace.duration_ms / 1000).toFixed(2) + 's' : '-'}</div>
                </div>
                <div class="detail-row">
                    <label>Started</label>
                    <div>${formatDate(trace.started_at)}</div>
                </div>
            </div>
            
            ${trace.instruction ? `
                <div class="detail-section">
                    <h4>📝 Instruction</h4>
                    <pre class="code-block">${escapeHtml(trace.instruction)}</pre>
                </div>
            ` : ''}
            
            ${trace.reasoning ? `
                <div class="detail-section">
                    <h4>💭 Reasoning</h4>
                    <pre class="code-block">${escapeHtml(trace.reasoning)}</pre>
                </div>
            ` : ''}
            
            ${trace.input_params ? `
                <div class="detail-section">
                    <h4>📥 Input Parameters</h4>
                    <pre class="code-block json">${escapeHtml(JSON.stringify(trace.input_params, null, 2))}</pre>
                </div>
            ` : ''}
            
            ${trace.output_data ? `
                <div class="detail-section">
                    <h4>📤 Output Data</h4>
                    <pre class="code-block json">${escapeHtml(JSON.stringify(trace.output_data, null, 2))}</pre>
                </div>
            ` : ''}
            
            ${trace.evidence_found && trace.evidence_found.length > 0 ? `
                <div class="detail-section">
                    <h4>📋 Evidence Found (${trace.evidence_count})</h4>
                    <div class="evidence-list">
                        ${trace.evidence_found.map(e => `
                            <div class="evidence-item">
                                <pre class="code-block json">${escapeHtml(JSON.stringify(e, null, 2))}</pre>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${trace.error_message ? `
                <div class="detail-section error-section">
                    <h4>❌ Error</h4>
                    <div class="error-type">${escapeHtml(trace.error_type || 'UnknownError')}</div>
                    <pre class="code-block error">${escapeHtml(trace.error_message)}</pre>
                </div>
            ` : ''}
            
            ${trace.children && trace.children.length > 0 ? `
                <div class="detail-section">
                    <h4>🔗 Child Traces (${trace.children.length})</h4>
                    <div class="children-list">
                        ${trace.children.map(c => `
                            <div class="child-trace" onclick="viewTraceDetail(${c.run_id}, ${c.id})">
                                ${getTraceTypeIcon(c.trace_type)} ${escapeHtml(c.trace_type)}
                                - ${escapeHtml(c.tool_name || c.agent_name || 'Unknown')}
                                <span class="trace-status ${getTraceStatusClass(c.status)}">${c.status}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        
    } catch (error) {
        body.innerHTML = `<p class="status-message error">Error loading trace: ${error.message}</p>`;
    }
}

/**
 * Close trace detail modal
 */
function closeTraceDetail() {
    document.getElementById('traceDetailModal').classList.add('hidden');
}
