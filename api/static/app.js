/**
 * Enterprise Integration Failure Analyzer Frontend Logic.
 * Handles single failure inference, chart rendering, file ingestion, and presets.
 */

// Global State
let selectedFile = null;
let currentTableData = [];
let charts = {};

const PRESETS = {
    auth_401: {
        interface: "Customer_Master_Sync",
        source: "Salesforce_CRM",
        target: "S4HANA",
        status_code: 401,
        error_message: "Unauthorized client: Bearer token expired or invalid JWT signature during OAuth handshake [Ref: MSG-10492]",
        retry_count: 3,
        processing_time: 320
    },
    timeout_504: {
        interface: "Order_Create_Inbound",
        source: "Shopify_Storefront",
        target: "S4HANA",
        status_code: 504,
        error_message: "Gateway Timeout: Upstream SAP S/4HANA took longer than 60000ms to respond to BAPI call [Ref: MSG-84912]",
        retry_count: 4,
        processing_time: 62400
    },
    lock_500: {
        interface: "Order_Create_Inbound",
        source: "Shopify_Storefront",
        target: "S4HANA",
        status_code: 500,
        error_message: "Internal Server Error: SAP enqueue server lock table overflow (transaction SM12) [Ref: MSG-49102]",
        retry_count: 2,
        processing_time: 1420
    },
    kunnr_400: {
        interface: "Customer_Master_Sync",
        source: "Salesforce_CRM",
        target: "S4HANA",
        status_code: 400,
        error_message: "Bad Request: JSON schema validation error - missing mandatory field 'KUNNR' in customer payload [Ref: MSG-33290]",
        retry_count: 0,
        processing_time: 180
    },
    credit_422: {
        interface: "Order_Create_Inbound",
        source: "Shopify_Storefront",
        target: "S4HANA",
        status_code: 422,
        error_message: "Business Rule Violation: Credit limit exceeded for customer 'ACME_CORP' (Limit: $50,000, Current Order: $68,000)",
        retry_count: 0,
        processing_time: 1950
    },
    tunnel_502: {
        interface: "Invoice_Post_Out",
        source: "S4HANA",
        target: "SAP_CPI",
        status_code: 502,
        error_message: "Bad Gateway: SAP Cloud Connector subaccount tunnel 'hana-prd-s4' is offline [Ref: MSG-99120]",
        retry_count: 3,
        processing_time: 850
    }
};

// Preset Application
function applyPreset(key) {
    const p = PRESETS[key];
    if (!p) return;
    document.getElementById("input-interface").value = p.interface;
    document.getElementById("input-source").value = p.source;
    document.getElementById("input-target").value = p.target;
    document.getElementById("input-status").value = p.status_code;
    document.getElementById("input-message").value = p.error_message;
    document.getElementById("input-retry").value = p.retry_count;
    document.getElementById("input-latency").value = p.processing_time;

    // Trigger analysis immediately on preset selection
    submitSingleAnalysis(new Event("submit"));
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

    const targetContent = document.getElementById(`tab-${tabId}`);
    if (targetContent) targetContent.classList.add("active");

    // Activate matching button
    const activeBtn = Array.from(document.querySelectorAll(".tab-btn")).find(b =>
        b.getAttribute("onclick")?.includes(tabId)
    );
    if (activeBtn) activeBtn.classList.add("active");

    if (tabId === "analytics") {
        renderCharts(window.INITIAL_STATS);
    }
}

// Single Analysis Submit
async function submitSingleAnalysis(event) {
    if (event) event.preventDefault();

    const payload = {
        interface: document.getElementById("input-interface").value.trim(),
        source: document.getElementById("input-source").value.trim(),
        target: document.getElementById("input-target").value.trim(),
        status_code: parseInt(document.getElementById("input-status").value) || 0,
        error_message: document.getElementById("input-message").value.trim(),
        retry_count: parseInt(document.getElementById("input-retry").value) || 0,
        processing_time: parseFloat(document.getElementById("input-latency").value) || 0.0
    };

    const btn = document.getElementById("btn-analyze");
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ Analyzing...</span>";

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const data = await response.json();
        renderAnalysisResult(data);
    } catch (err) {
        alert("Analysis error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = "<span>⚡ Run Failure Analysis</span>";
    }
}

function renderAnalysisResult(data) {
    document.getElementById("result-empty").style.display = "none";
    document.getElementById("result-content").style.display = "flex";
    document.getElementById("result-status-badge").innerText = "Diagnosed";
    document.getElementById("result-status-badge").className = "badge-pill text-success";

    // Category
    const catEl = document.getElementById("res-category");
    catEl.innerText = data.category;

    // Severity
    const sevEl = document.getElementById("res-severity");
    sevEl.innerText = data.severity_badge;
    sevEl.className = `badge-tag severity-${data.severity}`;

    // Confidence
    const confEl = document.getElementById("res-confidence");
    confEl.innerText = `${(data.confidence * 100).toFixed(0)}%`;

    // Recommendation & Reasoning
    document.getElementById("res-recommendation").innerText = data.recommendation;
    document.getElementById("res-reasoning").innerText = data.reasoning;

    // Engine comparison details
    const comp = data.details?.comparison || {};
    document.getElementById("comp-rule-cat").innerText = comp.rule_category || "-";
    document.getElementById("comp-rule-reason").innerText = comp.rule_reason || "-";
    document.getElementById("comp-ml-cat").innerText = comp.ml_category || "-";
    document.getElementById("comp-ml-conf").innerText = comp.ml_confidence ? `Confidence: ${(comp.ml_confidence * 100).toFixed(0)}%` : "-";

    const banner = document.getElementById("comp-agreement-banner");
    if (comp.agreement) {
        banner.style.display = "block";
        banner.style.background = "rgba(34, 197, 94, 0.1)";
        banner.style.color = "#4ade80";
        banner.style.borderColor = "rgba(34, 197, 94, 0.25)";
        banner.innerHTML = "✓ <b>Consensus:</b> Rule-based heuristics and ML Classifier agree on category.";
    } else {
        banner.style.display = "block";
        banner.style.background = "rgba(234, 179, 8, 0.1)";
        banner.style.color = "#facc15";
        banner.style.borderColor = "rgba(234, 179, 8, 0.25)";
        banner.innerHTML = "⚠️ <b>Discrepancy:</b> Rule-based and ML models produced distinct predictions; reconciled with highest confidence.";
    }
}

// Chart.js Rendering
function renderCharts(stats) {
    if (!stats || !stats.category_distribution) return;

    // 1. Categories Breakdown (Doughnut)
    const catCtx = document.getElementById("chart-category")?.getContext("2d");
    if (catCtx) {
        if (charts.category) charts.category.destroy();
        const catLabels = Object.keys(stats.category_distribution);
        const catData = Object.values(stats.category_distribution);
        charts.category = new Chart(catCtx, {
            type: "doughnut",
            data: {
                labels: catLabels,
                datasets: [{
                    data: catData,
                    backgroundColor: [
                        "#38bdf8", "#818cf8", "#f43f5e", "#fb923c", "#facc15", "#a855f7", "#64748b"
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { color: "#94a3b8", font: { size: 11 } } }
                }
            }
        });
    }

    // 2. Severity Distribution (Bar)
    const sevCtx = document.getElementById("chart-severity")?.getContext("2d");
    if (sevCtx) {
        if (charts.severity) charts.severity.destroy();
        const sevOrder = ["Critical", "High", "Medium", "Low"];
        const sevData = sevOrder.map(k => (stats.severity_distribution && stats.severity_distribution[k]) || 0);
        charts.severity = new Chart(sevCtx, {
            type: "bar",
            data: {
                labels: ["🔴 Critical", "🟠 High", "🟡 Medium", "🟢 Low"],
                datasets: [{
                    label: "Count",
                    data: sevData,
                    backgroundColor: ["#ef4444", "#f97316", "#eab308", "#22c55e"],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
                    y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } }
                }
            }
        });
    }

    // 3. Top Failing Interfaces (Horizontal Bar)
    const ifaceCtx = document.getElementById("chart-interfaces")?.getContext("2d");
    if (ifaceCtx && stats.top_failing_interfaces) {
        if (charts.interfaces) charts.interfaces.destroy();
        const ifaceLabels = Object.keys(stats.top_failing_interfaces);
        const ifaceData = Object.values(stats.top_failing_interfaces);
        charts.interfaces = new Chart(ifaceCtx, {
            type: "bar",
            data: {
                labels: ifaceLabels,
                datasets: [{
                    label: "Failures",
                    data: ifaceData,
                    backgroundColor: "#38bdf8",
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } },
                    y: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { display: false } }
                }
            }
        });
    }

    // 4. HTTP Status Codes (Bar)
    const statusCtx = document.getElementById("chart-status")?.getContext("2d");
    if (statusCtx && stats.status_code_distribution) {
        if (charts.status) charts.status.destroy();
        const statusLabels = Object.keys(stats.status_code_distribution).map(k => `Code ${k}`);
        const statusData = Object.values(stats.status_code_distribution);
        charts.status = new Chart(statusCtx, {
            type: "bar",
            data: {
                labels: statusLabels,
                datasets: [{
                    label: "Occurrences",
                    data: statusData,
                    backgroundColor: "#818cf8",
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
                    y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } }
                }
            }
        });
    }
}

// File Selection & Upload
function handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    selectedFile = file;
    document.getElementById("selected-file-name").innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    document.getElementById("btn-upload").disabled = false;
}

// Drag & drop support
const dropzone = document.getElementById("dropzone");
if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "#38bdf8";
    });
    dropzone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--border-color)";
    });
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--border-color)";
        if (e.dataTransfer.files.length) {
            selectedFile = e.dataTransfer.files[0];
            document.getElementById("selected-file-name").innerText = `Selected: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`;
            document.getElementById("btn-upload").disabled = false;
        }
    });
}

async function uploadAndAnalyzeFile() {
    if (!selectedFile) return;

    const btn = document.getElementById("btn-upload");
    btn.disabled = true;
    btn.innerHTML = "<span>⚙️ Cleaning and Analyzing...</span>";

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const response = await fetch("/analyze/file", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || `Upload failed with status ${response.status}`);
        }

        const data = await response.json();
        renderAuditSummary(data.cleaning_audit);
        renderTableData(data.sample_results);

        // Update KPI ribbon with new dataset statistics
        updateKpis(data.statistics);
        window.INITIAL_STATS = data.statistics;
        renderCharts(data.statistics);

    } catch (err) {
        alert("File Processing Error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = "<span>🚀 Clean & Analyze Dataset</span>";
    }
}

function updateKpis(stats) {
    if (!stats) return;
    document.getElementById("kpi-total").innerText = stats.total_failures || 0;
    document.getElementById("kpi-critical").innerText = (stats.severity_distribution && stats.severity_distribution.Critical) || 0;
    document.getElementById("kpi-high").innerText = (stats.severity_distribution && stats.severity_distribution.High) || 0;
    document.getElementById("kpi-latency").innerText = `${stats.processing_time_stats_ms?.mean || 0} ms`;
    document.getElementById("kpi-retries").innerText = `${stats.retry_stats?.rate_retried_pct || 0}%`;
}

function renderAuditSummary(audit) {
    const container = document.getElementById("audit-summary-container");
    const grid = document.getElementById("audit-grid");
    container.style.display = "block";

    grid.innerHTML = `
        <div class="audit-card">
            <span class="audit-label">Total Ingested Records</span>
            <span class="audit-val">${audit.total_records}</span>
        </div>
        <div class="audit-card">
            <span class="audit-label">Cleaned Valid Records</span>
            <span class="audit-val text-success">${audit.cleaned_records}</span>
        </div>
        <div class="audit-card">
            <span class="audit-label">Duplicate Records Purged</span>
            <span class="audit-val text-high">${audit.duplicates_removed}</span>
        </div>
        <div class="audit-card">
            <span class="audit-label">Missing Status Codes Imputed</span>
            <span class="audit-val">${audit.missing_status_codes_imputed}</span>
        </div>
        <div class="audit-card">
            <span class="audit-label">Negative Latency Fixed</span>
            <span class="audit-val">${audit.negative_processing_times_fixed}</span>
        </div>
        <div class="audit-card">
            <span class="audit-label">Invalid Retries Defaulted</span>
            <span class="audit-val">${audit.invalid_retries_fixed}</span>
        </div>
    `;
}

function renderTableData(results) {
    currentTableData = results || [];
    document.getElementById("table-container").style.display = "block";
    filterTable();
}

function filterTable() {
    const search = (document.getElementById("table-search").value || "").toLowerCase();
    const severityFilter = document.getElementById("severity-filter").value;
    const tbody = document.getElementById("table-body");
    tbody.innerHTML = "";

    const filtered = currentTableData.filter(row => {
        const matchesSearch = !search ||
            (row.interface && row.interface.toLowerCase().includes(search)) ||
            (row.error_message && row.error_message.toLowerCase().includes(search)) ||
            (row.recommendation && row.recommendation.toLowerCase().includes(search));

        const matchesSeverity = !severityFilter || row.severity === severityFilter;
        return matchesSearch && matchesSeverity;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #94a3b8;">No matching records found.</td></tr>`;
        return;
    }

    filtered.slice(0, 50).forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><span class="badge-tag severity-${row.severity}">${row.severity_badge || row.severity}</span></td>
            <td><b>${row.interface}</b></td>
            <td><span style="color: #94a3b8">${row.source} → ${row.target}</span></td>
            <td><code>${row.status_code || 0}</code></td>
            <td><span class="badge-pill">${row.category}</span></td>
            <td>${row.confidence ? (row.confidence * 100).toFixed(0) + '%' : '-'}</td>
            <td style="font-size: 0.8rem; max-width: 380px;">${row.recommendation}</td>
        `;
        tbody.appendChild(tr);
    });
}

// On Page Load
document.addEventListener("DOMContentLoaded", () => {
    // Populate with default preset on first load
    applyPreset("auth_401");
});
