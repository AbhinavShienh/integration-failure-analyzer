/**
 * Enterprise Integration Failure Analyzer — Frontend Logic v2
 * Supports Form mode, JSON paste mode, 14 presets, raw JSON viewer, and file ingestion.
 */

// ─── State ────────────────────────────────────────────────────
let selectedFile = null;
let currentTableData = [];
let charts = {};
let currentInputMode = 'form';  // 'form' | 'json'
let lastRawResult = null;

// ─── Preset Data ──────────────────────────────────────────────
const PRESETS = {
    auth_401: {
        interface: "Customer_Master_Sync", source: "Salesforce_CRM", target: "S4HANA",
        status_code: 401, retry_count: 3, processing_time: 320,
        timestamp: "2026-10-07T08:14:00Z",
        error_message: "Unauthorized client: Bearer token expired or invalid JWT signature during OAuth handshake [Ref: MSG-10492]"
    },
    timeout_504: {
        interface: "Order_Create_Inbound", source: "Shopify_Storefront", target: "S4HANA",
        status_code: 504, retry_count: 4, processing_time: 62400,
        timestamp: "2026-10-07T09:22:11Z",
        error_message: "Gateway Timeout: Upstream SAP S/4HANA took longer than 60000ms to respond to BAPI call [Ref: MSG-84912]"
    },
    lock_500: {
        interface: "General_Ledger_Batch_Post", source: "BillingEngine", target: "S4HANA",
        status_code: 500, retry_count: 4, processing_time: 85000,
        timestamp: "2026-10-07T02:01:45Z",
        error_message: "Internal Server Error: SAP enqueue server lock table overflow (transaction SM12) [Ref: MSG-49102]"
    },
    idoc_500: {
        interface: "Invoice_Post_Out", source: "S4HANA", target: "SAP_CPI",
        status_code: 500, retry_count: 3, processing_time: 4300,
        timestamp: "2026-10-07T06:45:00Z",
        error_message: "IDoc status 51: Application document not posted due to database deadlock in posting engine [Ref: MSG-61230]"
    },
    tunnel_502: {
        interface: "Payment_Status_Update", source: "Payment_Stripe", target: "S4HANA",
        status_code: 502, retry_count: 3, processing_time: 950,
        timestamp: "2026-10-07T11:05:30Z",
        error_message: "Bad Gateway: SAP Cloud Connector subaccount tunnel hana-prd-s4 is offline [Ref: MSG-99120]"
    },
    cert_403: {
        interface: "Invoice_Post_Out", source: "S4HANA", target: "SAP_CPI",
        status_code: 403, retry_count: 2, processing_time: 420,
        timestamp: "2026-10-07T13:45:00Z",
        error_message: "Forbidden: Client certificate missing or not trusted in SAP CPI Keystore [Ref: MSG-72100]"
    },
    pool_503: {
        interface: "Order_Create_Inbound", source: "Shopify_Storefront", target: "S4HANA",
        status_code: 503, retry_count: 4, processing_time: 1500,
        timestamp: "2026-10-07T07:15:00Z",
        error_message: "Service Unavailable: Backend connection pool exhausted — max 150 active connections reached [Ref: MSG-38200]"
    },
    abap_500: {
        interface: "Order_Create_Inbound", source: "Shopify_Storefront", target: "S4HANA",
        status_code: 500, retry_count: 2, processing_time: 2100,
        timestamp: "2026-10-07T10:00:00Z",
        error_message: "Internal Server Error: SAP ABAP runtime dump DYNPRO_NOT_FOUND in function module BAPI_SALESORDER_CREATEFROMDAT2 [Ref: MSG-55801]"
    },
    credit_422: {
        interface: "Order_Create_Inbound", source: "Shopify_Storefront", target: "S4HANA",
        status_code: 422, retry_count: 0, processing_time: 1950,
        timestamp: "2026-10-07T14:12:00Z",
        error_message: "Business Rule Violation: Credit limit exceeded for customer ACME_CORP (Limit: $50,000, Current Order: $68,000)"
    },
    period_422: {
        interface: "General_Ledger_Batch_Post", source: "BillingEngine", target: "S4HANA",
        status_code: 422, retry_count: 1, processing_time: 900,
        timestamp: "2026-10-07T23:00:00Z",
        error_message: "Business Rule Violation: SAP Posting period 09/2026 is closed in company code 1000 [Ref: MSG-11120]"
    },
    kunnr_400: {
        interface: "Customer_Master_Sync", source: "Salesforce_CRM", target: "S4HANA",
        status_code: 400, retry_count: 0, processing_time: 180,
        timestamp: "2026-10-07T10:30:00Z",
        error_message: "Bad Request: JSON schema validation error - missing mandatory field KUNNR in customer payload [Ref: MSG-33290]"
    },
    duplicate_409: {
        interface: "Order_Create_Inbound", source: "Shopify_Storefront", target: "S4HANA",
        status_code: 409, retry_count: 1, processing_time: 700,
        timestamp: "2026-10-07T15:00:00Z",
        error_message: "Conflict: Duplicate document error — Purchase Order PO-98231 already exists in SAP S/4HANA [Ref: MSG-28881]"
    },
    xml_400: {
        interface: "Shipment_Confirmation_EDI", source: "B2B_EDI_Partner", target: "SAP_CPI",
        status_code: 400, retry_count: 0, processing_time: 300,
        timestamp: "2026-10-07T16:00:00Z",
        error_message: "XML parse exception — mismatched closing tag </itemRecord> at line 48 in EDI payload [Ref: MSG-44501]"
    },
    unknown_599: {
        interface: "Vendor_Remittance_Advice", source: "S4HANA", target: "Banking_API",
        status_code: 599, retry_count: 0, processing_time: 400,
        timestamp: "2026-10-07T18:00:00Z",
        error_message: "Unrecognized vendor response code 9999 from legacy banking gateway — no protocol mapping found [Ref: MSG-77001]"
    }
};

// ─── Input Mode Toggle ────────────────────────────────────────
function setInputMode(mode) {
    currentInputMode = mode;
    document.getElementById('input-form-panel').style.display = mode === 'form' ? 'block' : 'none';
    document.getElementById('input-json-panel').style.display = mode === 'json' ? 'block' : 'none';
    document.getElementById('btn-mode-form').classList.toggle('active', mode === 'form');
    document.getElementById('btn-mode-json').classList.toggle('active', mode === 'json');

    // When switching to JSON, sync current form values into textarea
    if (mode === 'json') {
        syncFormToJson();
    }
}

function syncFormToJson() {
    const payload = getFormPayload();
    if (payload && payload.interface) {
        document.getElementById('json-input').value = JSON.stringify(payload, null, 2);
    }
}

function syncJsonToForm(data) {
    if (!data) return;
    setField('input-interface', data.interface);
    setField('input-source', data.source);
    setField('input-target', data.target);
    setField('input-status', data.status_code);
    setField('input-message', data.error_message);
    setField('input-retry', data.retry_count ?? 0);
    setField('input-latency', data.processing_time ?? 0);
    setField('input-timestamp', data.timestamp ?? '');
}

function setField(id, val) {
    const el = document.getElementById(id);
    if (el && val !== undefined && val !== null) el.value = val;
}

// ─── Presets ──────────────────────────────────────────────────
function applyPreset(key) {
    const p = PRESETS[key];
    if (!p) return;

    // Always populate form fields
    syncJsonToForm(p);

    // Also update JSON textarea
    document.getElementById('json-input').value = JSON.stringify(p, null, 2);
    clearJsonError();

    // Auto-run analysis
    runAnalysis(p);
}

// ─── Tab Switching ────────────────────────────────────────────
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.getElementById(`tab-${tabId}`).classList.add('active');
    const btn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick')?.includes(tabId));
    if (btn) btn.classList.add('active');

    if (tabId === 'analytics') renderCharts(window.INITIAL_STATS);
}

// ─── Form Helpers ─────────────────────────────────────────────
function getFormPayload() {
    return {
        interface: document.getElementById('input-interface').value.trim(),
        source: document.getElementById('input-source').value.trim() || 'Unknown',
        target: document.getElementById('input-target').value.trim() || 'Unknown',
        status_code: parseInt(document.getElementById('input-status').value) || 0,
        error_message: document.getElementById('input-message').value.trim(),
        retry_count: parseInt(document.getElementById('input-retry').value) || 0,
        processing_time: parseFloat(document.getElementById('input-latency').value) || 0,
        timestamp: document.getElementById('input-timestamp').value.trim() || undefined
    };
}

// ─── Form Submit ──────────────────────────────────────────────
async function submitSingleAnalysis(event) {
    if (event) event.preventDefault();
    const payload = getFormPayload();
    if (!payload.interface) { alert('Interface Name is required.'); return; }
    if (!payload.error_message) { alert('Error Message is required.'); return; }
    await runAnalysis(payload, 'btn-analyze-form');
}

// ─── JSON Submit ──────────────────────────────────────────────
async function submitJsonAnalysis() {
    const raw = document.getElementById('json-input').value.trim();
    if (!raw) { showJsonError('JSON input is empty.'); return; }

    let payload;
    try {
        payload = JSON.parse(raw);
    } catch (e) {
        showJsonError(`Invalid JSON: ${e.message}`);
        return;
    }

    if (!payload.interface) { showJsonError('Missing required field: "interface"'); return; }
    clearJsonError();

    // Also sync parsed values back into form
    syncJsonToForm(payload);

    await runAnalysis(payload, 'btn-analyze-json');
}

// ─── Core Analysis Runner ─────────────────────────────────────
async function runAnalysis(payload, btnId = null) {
    if (btnId) {
        const btn = document.getElementById(btnId);
        if (btn) { btn.disabled = true; btn.innerHTML = '<span>⏳ Analyzing…</span>'; }
    }

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        lastRawResult = data;
        renderAnalysisResult(data);
    } catch (err) {
        alert('Analysis error: ' + err.message);
    } finally {
        if (btnId) {
            const btn = document.getElementById(btnId);
            if (btn) { btn.disabled = false; btn.innerHTML = '<span>⚡ Run Failure Analysis</span>'; }
        }
    }
}

// ─── Render Result ────────────────────────────────────────────
function renderAnalysisResult(data) {
    document.getElementById('result-empty').style.display = 'none';
    document.getElementById('result-content').style.display = 'flex';
    document.getElementById('result-status-badge').innerText = 'Diagnosed ✓';
    document.getElementById('result-status-badge').className = 'badge-pill text-success';

    document.getElementById('res-category').innerText = data.category;

    const sevEl = document.getElementById('res-severity');
    sevEl.innerText = data.severity_badge;
    sevEl.className = `badge-tag severity-${data.severity}`;

    const confVal = data.confidence ? (data.confidence * 100).toFixed(0) + '%' : '-';
    document.getElementById('res-confidence').innerText = confVal;
    document.getElementById('res-recommendation').innerText = data.recommendation;
    document.getElementById('res-reasoning').innerText = data.reasoning;

    const comp = data.details?.comparison || {};
    document.getElementById('comp-rule-cat').innerText = comp.rule_category || '-';
    document.getElementById('comp-rule-reason').innerText = comp.rule_reason || '-';
    document.getElementById('comp-ml-cat').innerText = comp.ml_category || '-';
    document.getElementById('comp-ml-conf').innerText = comp.ml_confidence != null
        ? `Confidence: ${(comp.ml_confidence * 100).toFixed(0)}%` : '-';

    const banner = document.getElementById('comp-agreement-banner');
    if (comp.agreement) {
        banner.style.cssText = 'display:block; background:rgba(34,197,94,.1); color:#4ade80; border:1px solid rgba(34,197,94,.25); margin-top:.75rem; padding:.5rem .75rem; border-radius:6px; font-size:.8rem;';
        banner.innerHTML = '✓ <b>Consensus:</b> Rule-based heuristics and ML Classifier agree on category.';
    } else {
        banner.style.cssText = 'display:block; background:rgba(234,179,8,.1); color:#facc15; border:1px solid rgba(234,179,8,.25); margin-top:.75rem; padding:.5rem .75rem; border-radius:6px; font-size:.8rem;';
        banner.innerHTML = '⚠️ <b>Discrepancy:</b> Rule-based and ML models produced distinct predictions. Reconciled with highest confidence.';
    }

    // Update raw JSON viewer
    document.getElementById('raw-json-output').textContent = JSON.stringify(data, null, 2);
    // Reset toggle
    document.getElementById('raw-json-output').style.display = 'none';
    document.getElementById('raw-json-toggle-icon').textContent = '▼ Show';
}

// ─── Raw JSON Viewer ──────────────────────────────────────────
function toggleRawJson() {
    const pre = document.getElementById('raw-json-output');
    const icon = document.getElementById('raw-json-toggle-icon');
    if (pre.style.display === 'none') {
        pre.style.display = 'block';
        icon.textContent = '▲ Hide';
    } else {
        pre.style.display = 'none';
        icon.textContent = '▼ Show';
    }
}

// ─── JSON Editor Helpers ──────────────────────────────────────
function formatJson() {
    const ta = document.getElementById('json-input');
    try {
        ta.value = JSON.stringify(JSON.parse(ta.value), null, 2);
        clearJsonError();
    } catch (e) {
        showJsonError(`Cannot format: ${e.message}`);
    }
}

function copyJson() {
    const ta = document.getElementById('json-input');
    navigator.clipboard.writeText(ta.value).then(() => {
        const btn = document.querySelector('.btn-icon[onclick="copyJson()"]');
        if (btn) { const orig = btn.textContent; btn.textContent = '✓ Copied!'; setTimeout(() => btn.textContent = orig, 1500); }
    });
}

function clearJson() {
    document.getElementById('json-input').value = '';
    clearJsonError();
}

function showJsonError(msg) {
    const el = document.getElementById('json-error-banner');
    el.textContent = '⚠ ' + msg;
    el.style.display = 'block';
}

function clearJsonError() {
    const el = document.getElementById('json-error-banner');
    if (el) el.style.display = 'none';
}

// ─── Chart Rendering ──────────────────────────────────────────
function renderCharts(stats) {
    if (!stats || !stats.category_distribution) return;

    renderDonut('chart-category', Object.keys(stats.category_distribution), Object.values(stats.category_distribution),
        ['#38bdf8','#818cf8','#f43f5e','#fb923c','#facc15','#a855f7','#64748b']);

    const sevOrder = ['Critical','High','Medium','Low'];
    const sevData = sevOrder.map(k => (stats.severity_distribution?.[k]) || 0);
    renderBar('chart-severity', ['🔴 Critical','🟠 High','🟡 Medium','🟢 Low'], sevData,
        ['#ef4444','#f97316','#eab308','#22c55e'], false);

    if (stats.top_failing_interfaces) {
        renderBar('chart-interfaces', Object.keys(stats.top_failing_interfaces),
            Object.values(stats.top_failing_interfaces), ['#38bdf8'], true);
    }

    if (stats.status_code_distribution) {
        renderBar('chart-status', Object.keys(stats.status_code_distribution).map(k => `Code ${k}`),
            Object.values(stats.status_code_distribution), ['#818cf8'], false);
    }
}

function renderDonut(id, labels, data, colors) {
    const ctx = document.getElementById(id)?.getContext('2d');
    if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 11 } } } }
        }
    });
}

function renderBar(id, labels, data, colors, horizontal) {
    const ctx = document.getElementById(id)?.getContext('2d');
    if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    const multi = Array.isArray(colors) && colors.length > 1;
    charts[id] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Count',
                data,
                backgroundColor: multi ? colors : colors[0],
                borderRadius: 5
            }]
        },
        options: {
            indexAxis: horizontal ? 'y' : 'x',
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: horizontal ? 'rgba(255,255,255,.05)' : 'none' } },
                y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: horizontal ? 'none' : 'rgba(255,255,255,.05)' } }
            }
        }
    });
}

// ─── File Ingestion ───────────────────────────────────────────
function handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    selectedFile = file;
    document.getElementById('selected-file-name').innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    document.getElementById('btn-upload').disabled = false;
}

const dropzone = document.getElementById('dropzone');
if (dropzone) {
    dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.style.borderColor = '#38bdf8'; });
    dropzone.addEventListener('dragleave', e => { e.preventDefault(); dropzone.style.borderColor = 'var(--border-color)'; });
    dropzone.addEventListener('drop', e => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files.length) {
            selectedFile = e.dataTransfer.files[0];
            document.getElementById('selected-file-name').innerText = `Selected: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`;
            document.getElementById('btn-upload').disabled = false;
        }
    });
}

async function uploadAndAnalyzeFile() {
    if (!selectedFile) return;
    const btn = document.getElementById('btn-upload');
    btn.disabled = true; btn.innerHTML = '<span>⚙️ Cleaning and Analyzing…</span>';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/analyze/file', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(err.detail || `Upload failed: HTTP ${response.status}`);
        }
        const data = await response.json();
        renderAuditSummary(data.cleaning_audit);
        renderTableData(data.sample_results);
        updateKpis(data.statistics);
        window.INITIAL_STATS = data.statistics;
        renderCharts(data.statistics);
    } catch (err) {
        alert('File Processing Error: ' + err.message);
    } finally {
        btn.disabled = false; btn.innerHTML = '<span>🚀 Clean &amp; Analyze Dataset</span>';
    }
}

function updateKpis(stats) {
    if (!stats) return;
    document.getElementById('kpi-total').innerText = stats.total_failures || 0;
    document.getElementById('kpi-critical').innerText = (stats.severity_distribution?.Critical) || 0;
    document.getElementById('kpi-high').innerText = (stats.severity_distribution?.High) || 0;
    document.getElementById('kpi-latency').innerText = `${stats.processing_time_stats_ms?.mean || 0} ms`;
    document.getElementById('kpi-retries').innerText = `${stats.retry_stats?.rate_retried_pct || 0}%`;
}

function renderAuditSummary(audit) {
    document.getElementById('audit-summary-container').style.display = 'block';
    document.getElementById('audit-grid').innerHTML = `
        <div class="audit-card"><span class="audit-label">Total Ingested Records</span><span class="audit-val">${audit.total_records}</span></div>
        <div class="audit-card"><span class="audit-label">Cleaned Valid Records</span><span class="audit-val text-success">${audit.cleaned_records}</span></div>
        <div class="audit-card"><span class="audit-label">Duplicates Removed</span><span class="audit-val text-high">${audit.duplicates_removed}</span></div>
        <div class="audit-card"><span class="audit-label">Missing Status Codes</span><span class="audit-val">${audit.missing_status_codes_imputed}</span></div>
        <div class="audit-card"><span class="audit-label">Negative Latency Fixed</span><span class="audit-val">${audit.negative_processing_times_fixed}</span></div>
        <div class="audit-card"><span class="audit-label">Invalid Retries Fixed</span><span class="audit-val">${audit.invalid_retries_fixed}</span></div>
    `;
}

function renderTableData(results) {
    currentTableData = results || [];
    document.getElementById('table-container').style.display = 'block';
    filterTable();
}

function filterTable() {
    const search = (document.getElementById('table-search').value || '').toLowerCase();
    const sevFilter = document.getElementById('severity-filter').value;
    const catFilter = document.getElementById('category-filter').value;
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    const filtered = currentTableData.filter(row => {
        const matchSearch = !search ||
            (row.interface || '').toLowerCase().includes(search) ||
            (row.error_message || '').toLowerCase().includes(search) ||
            (row.recommendation || '').toLowerCase().includes(search);
        const matchSev = !sevFilter || row.severity === sevFilter;
        const matchCat = !catFilter || row.category === catFilter;
        return matchSearch && matchSev && matchCat;
    });

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8;">No matching records found.</td></tr>`;
        return;
    }

    filtered.slice(0, 50).forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="badge-tag severity-${row.severity}">${row.severity_badge || row.severity}</span></td>
            <td><b>${row.interface}</b></td>
            <td style="color:#94a3b8">${row.source} → ${row.target}</td>
            <td><code>${row.status_code || 0}</code></td>
            <td><span class="badge-pill">${row.category}</span></td>
            <td>${row.confidence != null ? (row.confidence * 100).toFixed(0) + '%' : '-'}</td>
            <td style="font-size:.8rem;max-width:380px;">${row.recommendation}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ─── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    applyPreset('auth_401');
});
