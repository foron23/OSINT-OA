// =============================================================================
// OSINT News Aggregator - Frontend Application
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
        
        container.innerHTML = data.runs.map(run => `
            <div class="run-item" data-run-id="${run.id}">
                <span class="run-id">#${run.id}</span>
                <span class="run-query">${escapeHtml(truncate(run.query, 50))}</span>
                <span class="run-status ${run.status}">${run.status}</span>
                <span class="run-date">${formatDate(run.started_at)}</span>
                <div class="run-actions">
                    <button class="btn btn-sm btn-secondary" onclick="viewRun(${run.id})">View</button>
                    <button class="btn btn-sm btn-outline" onclick="showDeleteModal(${run.id})">🗑️</button>
                </div>
            </div>
        `).join('');
        
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
// Items
// =============================================================================

/**
 * Load items for a run
 */
async function loadItems(runId) {
    const section = document.getElementById('itemsSection');
    const container = document.getElementById('itemsList');
    
    section.classList.remove('hidden');
    container.innerHTML = '<p class="loading">Loading items...</p>';
    
    try {
        const data = await apiRequest(`/items?run_id=${runId}&limit=50`);
        
        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No items collected yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.items.map(item => `
            <div class="item-card">
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
        
    } catch (error) {
        container.innerHTML = `<p class="status-message error">Error loading items: ${error.message}</p>`;
    }
}

// =============================================================================
// Collection
// =============================================================================

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
        
        const result = await apiRequest('/collect', {
            method: 'POST',
            body: payload,
        });
        
        showStatus('collectStatus', 
            `✅ Collection complete! Run #${result.run_id}: ${result.items_count} items collected. ` +
            (result.report?.telegram_published ? 'Report published to Telegram.' : ''),
            'success'
        );
        
        // Refresh runs list
        loadRuns();
        
        // View the new run
        setTimeout(() => viewRun(result.run_id), 500);
        
    } catch (error) {
        showStatus('collectStatus', `❌ Collection failed: ${error.message}`, 'error');
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
    
    // Collection form
    document.getElementById('collectForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = {
            query: document.getElementById('query').value,
            limit: document.getElementById('limit').value,
            since: document.getElementById('since').value,
            scope: document.getElementById('scope').value,
        };
        await startCollection(formData);
        e.target.reset();
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
    
    // Auto refresh toggle
    document.getElementById('autoRefresh').addEventListener('change', (e) => {
        toggleAutoRefresh(e.target.checked);
    });
});

// Expose functions to global scope for onclick handlers
window.viewRun = viewRun;
window.showDeleteModal = showDeleteModal;
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
