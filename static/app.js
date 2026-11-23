/**
 * VULCAN // SAKTHI MELT-OS - CLIENT CONTROLLER
 * Authentic Industrial SCADA / MES Controller for Automotive Foundries
 * High-Legibility Light Mode • Tabbed Workspaces • Zero External CDN Dependencies
 */

// Application State
const appState = {
  grades: {},
  alloys: [],
  elementsMeta: {},
  selectedGradeId: "ductile_iron_500_7",
  meltWeight: 4000.0,
  mode: "target",
  currency: "INR",
  fxRate: 84.0,
  currentChemistry: {},
  disabledAlloys: new Set(),
  lastOptimizationResult: null,
  lastWhatIfResult: null,
  activeHeatNumber: "H-2026-1121-001",
  lastSavedHeatId: null,
  approvalStatus: "CALCULATED",
  operatorName: "K. Murugan (Shift A)",
  overrideReason: "",
  manualOverrides: {}, // { alloy_id: weight_kg }
  isOverridden: false
};

// ==========================================================================
// 1. LIFECYCLE INITIALIZATION
// ==========================================================================
document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  setupEventListeners();
  await loadCatalogData();
  await fetchNextHeatNumber();
  await refreshHeatLogCount();
  selectGrade(appState.selectedGradeId);
});

function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      if (!targetId) return;

      // Update button states
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      // Update pane states
      document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
      });
      const activePane = document.getElementById(targetId);
      if (activePane) activePane.classList.add("active");

      // Contextual refresh on tab switch
      if (targetId === "tab-heats") {
        loadHeatLogRecords();
      } else if (targetId === "tab-settings") {
        renderSettingsTab();
      } else if (targetId === "tab-economics") {
        triggerWhatIfComparison();
      } else if (targetId === "tab-corridors") {
        if (appState.lastOptimizationResult) {
          renderCorridorAnalysis(appState.lastOptimizationResult);
        }
      }
    });
  });
}

async function fetchNextHeatNumber() {
  try {
    const res = await fetch("/api/heats/next-number").then(r => r.json());
    if (res.next_heat_number) {
      appState.activeHeatNumber = res.next_heat_number;
      updateTelemetryHeader();
    }
  } catch (e) {
    console.warn("Could not fetch next heat number:", e);
  }
}

async function refreshHeatLogCount() {
  try {
    const res = await fetch("/api/heats?limit=1").then(r => r.json());
    const countBadge = document.getElementById("tab-heat-count");
    if (countBadge) countBadge.textContent = res.count ?? 0;
  } catch (e) {
    // ignore
  }
}

async function loadCatalogData() {
  try {
    const [gradesRes, alloysRes, elementsRes] = await Promise.all([
      fetch("/api/grades").then(r => r.json()),
      fetch("/api/alloys").then(r => r.json()),
      fetch("/api/elements").then(r => r.json()).catch(() => ({ elements: {} }))
    ]);

    appState.grades = {};
    gradesRes.grades.forEach(g => { appState.grades[g.id] = g; });
    appState.alloys = alloysRes.alloys || [];
    appState.elementsMeta = elementsRes.elements || {};

    renderPresetChips();
    renderGradeDropdown();
    renderAlloyToggles();
  } catch (e) {
    console.error("Failed to load catalog data:", e);
  }
}

// ==========================================================================
// 2. CURRENCY & NUMBER FORMATTING
// ==========================================================================
function formatCurrency(amountUSD) {
  if (appState.currency === "INR") {
    const valINR = (amountUSD || 0) * appState.fxRate;
    return `₹${Math.round(valINR).toLocaleString('en-IN')}`;
  }
  return `$${(amountUSD || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function setCurrency(curr) {
  appState.currency = curr;
  document.getElementById("curr-inr-btn")?.classList.toggle("active", curr === "INR");
  document.getElementById("curr-usd-btn")?.classList.toggle("active", curr === "USD");
  if (appState.lastOptimizationResult) {
    renderKPIs(appState.lastOptimizationResult);
    renderChargingTable(appState.lastOptimizationResult);
  }
}

// ==========================================================================
// 3. EVENT LISTENERS
// ==========================================================================
function setupEventListeners() {
  // Currency Toggle
  document.getElementById("curr-inr-btn")?.addEventListener("click", () => setCurrency("INR"));
  document.getElementById("curr-usd-btn")?.addEventListener("click", () => setCurrency("USD"));

  // Target Grade Selector
  document.getElementById("grade-select")?.addEventListener("change", (e) => {
    selectGrade(e.target.value);
  });

  // Melt Weight Input
  document.getElementById("melt-weight-input")?.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value) || 4000.0;
    appState.meltWeight = Math.max(100.0, Math.min(50000.0, val));
    debounceOptimize();
  });

  // Corridor Strategy Pills
  document.querySelectorAll(".strategy-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".strategy-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      appState.mode = pill.getAttribute("data-mode") || "target";
      debounceOptimize();
    });
  });

  // Reset Reading Button
  document.getElementById("reset-reading-btn")?.addEventListener("click", () => {
    const g = appState.grades[appState.selectedGradeId];
    if (g && g.demo_reading) {
      appState.currentChemistry = { ...g.demo_reading };
      renderSpectroTable();
      debounceOptimize();
    }
  });

  // Solve Button
  document.getElementById("solve-btn")?.addEventListener("click", () => triggerOptimize());

  // Drag and Drop OES File
  setupDropzone();

  // Verification & Sign-off Actions
  document.getElementById("save-heat-btn")?.addEventListener("click", handleSaveAndApprove);
  document.getElementById("export-pdf-btn")?.addEventListener("click", exportCurrentPDF);
  document.getElementById("export-csv-btn")?.addEventListener("click", exportCurrentCSV);
  document.getElementById("quick-print-ticket-btn")?.addEventListener("click", () => window.print());

  // Approval Status Select
  document.getElementById("approval-status-select")?.addEventListener("change", (e) => {
    appState.approvalStatus = e.target.value;
    updateApprovalStatusUI();
  });

  // Reset Master Catalogs
  document.getElementById("reset-alloys-btn")?.addEventListener("click", handleResetAlloys);
  document.getElementById("reset-grades-btn")?.addEventListener("click", handleResetGrades);

  // Search filter for Heat Log
  document.getElementById("heat-search-input")?.addEventListener("input", (e) => {
    loadHeatLogRecords(e.target.value.trim());
  });
}

function selectGrade(gradeId) {
  if (!appState.grades[gradeId]) return;
  appState.selectedGradeId = gradeId;
  const grade = appState.grades[gradeId];

  // Update UI Select
  const sel = document.getElementById("grade-select");
  if (sel) sel.value = gradeId;

  // Update Application Note
  const appPill = document.getElementById("casting-application-pill");
  if (appPill) appPill.textContent = grade.casting_part || grade.category || "Automotive Casting";

  // Update Melt Weight
  if (grade.default_weight_kg) {
    appState.meltWeight = grade.default_weight_kg;
    const wtInput = document.getElementById("melt-weight-input");
    if (wtInput) wtInput.value = grade.default_weight_kg;
  }

  // Set Demo Reading & Reset Overrides
  appState.currentChemistry = { ...(grade.demo_reading || {}) };
  appState.manualOverrides = {};
  appState.isOverridden = false;
  appState.approvalStatus = "CALCULATED";

  updateTelemetryHeader();
  renderPresetChips();
  renderSpectroTable();
  triggerOptimize();
}

function adjustMeltWeight(delta) {
  const cur = parseFloat(document.getElementById("melt-weight-input")?.value) || 4000.0;
  const updated = Math.max(100.0, Math.min(50000.0, cur + delta));
  appState.meltWeight = updated;
  const input = document.getElementById("melt-weight-input");
  if (input) input.value = updated;
  debounceOptimize();
}

function renderPresetChips() {
  const container = document.getElementById("preset-strip-container");
  if (!container) return;
  container.innerHTML = "";

  Object.values(appState.grades).forEach(g => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `preset-chip ${g.id === appState.selectedGradeId ? 'active' : ''}`;
    chip.textContent = g.name.split('(')[0].trim();
    chip.onclick = () => selectGrade(g.id);
    container.appendChild(chip);
  });
}

function renderGradeDropdown() {
  const sel = document.getElementById("grade-select");
  if (!sel) return;
  sel.innerHTML = "";
  Object.values(appState.grades).forEach(g => {
    const opt = document.createElement("option");
    opt.value = g.id;
    opt.textContent = `${g.name} (${g.category})`;
    sel.appendChild(opt);
  });
  sel.value = appState.selectedGradeId;
}

// ==========================================================================
// 4. TAB 1: SPECTROMETER CHEMISTRY TABLE
// ==========================================================================
function renderSpectroTable() {
  const tbody = document.getElementById("spectro-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const g = appState.grades[appState.selectedGradeId];
  if (!g) return;

  Object.entries(g.elements).forEach(([el, spec]) => {
    const currentVal = appState.currentChemistry[el] ?? spec.target;
    const delta = currentVal - spec.target;

    let tagClass = "in-spec";
    let tagLabel = "IN SPEC";
    if (currentVal < spec.min - 1e-4) {
      tagClass = "deficit";
      tagLabel = `DEFICIT -${(spec.min - currentVal).toFixed(3)}%`;
    } else if (currentVal > spec.max + 1e-4) {
      tagClass = "excess";
      tagLabel = `EXCESS +${(currentVal - spec.max).toFixed(3)}%`;
    }

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>
        <strong style="font-size:13px; color:var(--text-main);">${el}</strong>
        <span style="font-size:10px; color:var(--text-faint); margin-left:4px;">${appState.elementsMeta[el]?.name || ''}</span>
      </td>
      <td style="text-align:right; font-family:var(--font-mono); color:var(--text-muted);">${spec.min.toFixed(3)}%</td>
      <td style="text-align:right;">
        <input type="number" step="${spec.step || 0.01}" value="${currentVal}" class="tabular-input" data-el="${el}">
      </td>
      <td style="text-align:right; font-family:var(--font-mono); color:#ea580c; font-weight:700;">${spec.target.toFixed(3)}%</td>
      <td style="text-align:right; font-family:var(--font-mono); color:var(--text-muted);">${spec.max.toFixed(3)}%</td>
      <td style="text-align:center;">
        <span class="channel-tag ${tagClass}" id="tag-${el}">${tagLabel}</span>
      </td>
    `;

    const input = row.querySelector("input");
    input.addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      if (!isNaN(v)) {
        appState.currentChemistry[el] = v;
        updateElementTag(el, v, spec);
        debounceOptimize();
      }
    });

    tbody.appendChild(row);
  });
}

function updateElementTag(el, val, spec) {
  const tag = document.getElementById(`tag-${el}`);
  if (!tag) return;

  if (val < spec.min - 1e-4) {
    tag.className = "channel-tag deficit";
    tag.textContent = `DEFICIT -${(spec.min - val).toFixed(3)}%`;
  } else if (val > spec.max + 1e-4) {
    tag.className = "channel-tag excess";
    tag.textContent = `EXCESS +${(val - spec.max).toFixed(3)}%`;
  } else {
    tag.className = "channel-tag in-spec";
    tag.textContent = "IN SPEC";
  }
}

// Dropzone Parser
function setupDropzone() {
  const dropzone = document.getElementById("spectro-dropzone");
  const fileInput = document.getElementById("spectro-file-input");
  const statusMsg = document.getElementById("import-status-msg");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleSpectroFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleSpectroFile(e.target.files[0]);
    }
  });

  async function handleSpectroFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
      if (statusMsg) {
        statusMsg.style.display = "block";
        statusMsg.style.background = "#eff6ff";
        statusMsg.style.color = "#1d4ed8";
        statusMsg.textContent = `Parsing ${file.name}...`;
      }

      const res = await fetch("/api/spectrometer/import", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to parse spectrometer file.");
      }

      const data = await res.json();
      if (data.composition) {
        if (data.detected_grade_id && data.detected_grade_id !== appState.selectedGradeId && appState.grades[data.detected_grade_id]) {
          selectGrade(data.detected_grade_id);
        }

        Object.assign(appState.currentChemistry, data.composition);
        renderSpectroTable();

        if (statusMsg) {
          statusMsg.style.background = "#f0fdf4";
          statusMsg.style.color = "#15803d";
          statusMsg.textContent = `✓ Successfully imported ${data.channels_read} channels from ${file.name}`;
        }
        triggerOptimize();
      }
    } catch (e) {
      if (statusMsg) {
        statusMsg.style.background = "#fef2f2";
        statusMsg.style.color = "#b91c1c";
        statusMsg.textContent = `Error: ${e.message}`;
      }
    }
  }
}

// ==========================================================================
// 5. SOLVER INTEGRATION & LIVE RECALCULATION
// ==========================================================================
let debounceTimer = null;
function debounceOptimize() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    triggerOptimize();
  }, 300);
}

async function triggerOptimize() {
  const gradeSpec = appState.grades[appState.selectedGradeId];
  if (!gradeSpec) return;

  const payload = {
    grade_id: appState.selectedGradeId,
    melt_weight_kg: appState.meltWeight,
    current_composition: appState.currentChemistry,
    disabled_alloy_ids: Array.from(appState.disabledAlloys),
    mode: appState.mode
  };

  try {
    const optRes = await fetch("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    appState.lastOptimizationResult = optRes;

    renderVerdictBanner(optRes);
    renderKPIs(optRes);
    renderChargingTable(optRes);
    renderCrucibleMetrics(optRes);

    // If corridors tab is active, update corridor view
    renderCorridorAnalysis(optRes);

    updateTelemetryHeader();
  } catch (e) {
    console.error("Optimization failed:", e);
  }
}

function renderCrucibleMetrics(res) {
  const baseWeightEl = document.getElementById("hud-base-weight");
  const finalWeightEl = document.getElementById("hud-final-weight");
  const ceEl = document.getElementById("hud-ce-val");
  const tliqEl = document.getElementById("hud-tliq-val");
  const eutecticEl = document.getElementById("hud-eutectic-status");

  if (baseWeightEl) baseWeightEl.textContent = `${Math.round(appState.meltWeight).toLocaleString()} kg`;
  if (finalWeightEl) finalWeightEl.textContent = `→ Tap: ${Math.round(res.final_melt_weight_kg || appState.meltWeight).toLocaleString()} kg`;

  if (res.ce_final !== null && res.ce_final !== undefined) {
    if (ceEl) ceEl.textContent = res.ce_final.toFixed(2);
    if (tliqEl) tliqEl.textContent = `${res.liquidus_temp_c} °C`;
    if (eutecticEl) {
      if (res.ce_final < 4.25) eutecticEl.textContent = "Hypoeutectic";
      else if (res.ce_final > 4.35) eutecticEl.textContent = "Hypereutectic";
      else eutecticEl.textContent = "Near-Eutectic (4.30)";
    }
  } else {
    if (ceEl) ceEl.textContent = "N/A (Steel)";
    if (tliqEl) tliqEl.textContent = "N/A";
    if (eutecticEl) eutecticEl.textContent = "Non-Eutectic Matrix";
  }
}

// ==========================================================================
// 6. VERDICT BANNER & METALLURGICAL KPIS
// ==========================================================================
function renderVerdictBanner(res) {
  const container = document.getElementById("verdict-banner-container");
  if (!container) return;

  if (!res.success) {
    container.innerHTML = `
      <div class="verdict-box alert">
        <div>
          <strong>Optimization Blocked:</strong> ${res.message || "Unable to solve feasible additions."}
        </div>
      </div>
    `;
    return;
  }

  const hasViolations = res.violations && res.violations.length > 0;
  const hasAlerts = res.over_spec_alerts && res.over_spec_alerts.length > 0;

  if (hasViolations || hasAlerts) {
    let listItems = "";
    if (hasViolations) listItems += res.violations.map(v => `<li>${v.reason}</li>`).join("");
    if (hasAlerts) listItems += res.over_spec_alerts.map(a => `<li>${a.reason}</li>`).join("");

    container.innerHTML = `
      <div class="verdict-box alert">
        <div>
          <strong>Metallurgical Corridor Alert — Hold Ladle:</strong>
          <ul style="margin-top:4px; padding-left:18px;">${listItems}</ul>
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div class="verdict-box pass">
        <div>
          <strong>Ready to Charge — All Channels In Corridor:</strong>
          Optimal ferroalloy charge satisfies all element bounds. Dilution and cross-contaminations accounted for.
        </div>
      </div>
    `;
  }
}

function renderKPIs(res) {
  const costEl = document.getElementById("kpi-total-cost");
  const weightEl = document.getElementById("kpi-total-weight");
  const weightSub = document.getElementById("kpi-weight-sub");
  const ceCard = document.getElementById("kpi-ce-card");
  const tliqCard = document.getElementById("kpi-tliq-card");

  const totCost = res.total_cost || 0;
  const totWeight = res.total_added_kg || 0;

  if (costEl) costEl.textContent = formatCurrency(totCost);
  if (weightEl) weightEl.textContent = `${totWeight.toFixed(2)} kg`;

  const dilutionPct = ((totWeight / (appState.meltWeight || 4000.0)) * 100).toFixed(1);
  if (weightSub) weightSub.textContent = `+${dilutionPct}% Melt Dilution`;

  if (res.ce_final !== null && res.ce_final !== undefined) {
    if (ceCard) ceCard.style.display = "block";
    if (tliqCard) tliqCard.style.display = "block";
    document.getElementById("kpi-ce-val").textContent = res.ce_final.toFixed(2);
    document.getElementById("kpi-ce-sub").textContent = `Initial: ${res.ce_initial ? res.ce_initial.toFixed(2) : '--'}`;
    document.getElementById("kpi-tliq-val").textContent = `${res.liquidus_temp_c} °C`;
  } else {
    if (ceCard) ceCard.style.display = "none";
    if (tliqCard) tliqCard.style.display = "none";
  }
}

// ==========================================================================
// 7. CHARGING DISPATCH TABLE & INTERACTIVE OVERRIDES
// ==========================================================================
function renderChargingTable(res) {
  const tbody = document.getElementById("charging-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const recs = res.recommendations || [];
  if (recs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-faint);">No alloy additions required. Bath composition is within specification.</td></tr>`;
    return;
  }

  recs.forEach((r, idx) => {
    const overrideVal = appState.manualOverrides[r.alloy_id] ?? r.quantity_kg;
    const isModified = Math.abs(overrideVal - r.quantity_kg) > 0.01;
    const cost = appState.currency === "INR" ? (r.total_cost_inr || r.total_cost * appState.fxRate) : r.total_cost;

    const row = document.createElement("tr");
    row.className = `charging-row ${isModified ? 'modified' : ''}`;
    row.innerHTML = `
      <td style="font-family:var(--font-mono); font-weight:700; color:var(--text-faint);">${r.charge_order || idx + 1}</td>
      <td>
        <div style="font-weight:700; color:var(--text-main); font-size:13px;">${r.short_name || r.name}</div>
        <div style="font-size:10.5px; color:var(--text-faint);">${r.alloy_name || ''}</div>
      </td>
      <td style="text-align:right; font-family:var(--font-mono); font-weight:700;">${r.quantity_kg.toFixed(2)} kg</td>
      <td style="text-align:right;">
        <input type="number" step="0.1" value="${overrideVal}" class="override-input ${isModified ? 'is-changed' : ''}" data-alloy="${r.alloy_id}">
      </td>
      <td class="pack-badge">
        ${r.full_bags > 0 ? `<b>${r.full_bags}</b> sack (${r.bag_size_kg}kg) + <b>${r.loose_kg.toFixed(1)}kg</b> trim` : `<b>${r.loose_kg.toFixed(1)}kg</b> trim scale`}
      </td>
      <td style="text-align:right; font-family:var(--font-mono); font-weight:700;">
        ${appState.currency === "INR" ? `₹${Math.round(cost).toLocaleString('en-IN')}` : `$${cost.toFixed(2)}`}
      </td>
    `;

    const input = row.querySelector("input");
    input.addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      if (!isNaN(v) && v >= 0) {
        appState.manualOverrides[r.alloy_id] = v;
        appState.isOverridden = true;
        appState.approvalStatus = "OVERRIDDEN";
        updateApprovalStatusUI();
        debounceSimulateOverrides();
      }
    });

    tbody.appendChild(row);
  });
}

// Debounced Override Simulation
let simulateTimer = null;
function debounceSimulateOverrides() {
  clearTimeout(simulateTimer);
  simulateTimer = setTimeout(() => {
    simulateOverrides();
  }, 300);
}

async function simulateOverrides() {
  const g = appState.grades[appState.selectedGradeId];
  if (!g) return;

  const additions = [];
  const recs = appState.lastOptimizationResult?.recommendations || [];
  recs.forEach(r => {
    const w = appState.manualOverrides[r.alloy_id] ?? r.quantity_kg;
    additions.push({ alloy_id: r.alloy_id, weight_kg: w });
  });

  try {
    const res = await fetch("/api/simulate-additions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grade_id: appState.selectedGradeId,
        melt_weight_kg: appState.meltWeight,
        current_composition: appState.currentChemistry,
        additions: additions
      })
    }).then(r => r.json());

    if (res.success) {
      renderCorridorAnalysis({
        final_composition: res.predicted_composition,
        violations: res.violations,
        recommendations: recs
      });

      if (res.violations && res.violations.length > 0) {
        const container = document.getElementById("verdict-banner-container");
        if (container) {
          container.innerHTML = `
            <div class="verdict-box alert">
              <div>
                <strong>Manual Override Induced Out-of-Spec Chemistry:</strong>
                <ul style="margin-top:4px; padding-left:18px;">
                  ${res.violations.map(v => `<li>${v.reason}</li>`).join("")}
                </ul>
              </div>
            </div>
          `;
        }
      }
    }
  } catch (e) {
    console.warn("Override simulation error:", e);
  }
}

// ==========================================================================
// 8. VERIFICATION, SIGN-OFF & PDF EXPORTS
// ==========================================================================
function updateApprovalStatusUI() {
  const tag = document.getElementById("verify-status-tag");
  const sel = document.getElementById("approval-status-select");
  const reasonBlock = document.getElementById("override-reason-block");
  const overrideBadge = document.getElementById("override-indicator-badge");

  if (sel) sel.value = appState.approvalStatus;

  if (tag) {
    tag.className = `status-tag ${appState.approvalStatus.toLowerCase().replace('_', '-')}`;
    tag.textContent = appState.approvalStatus.replace('_', ' ');
  }

  const isOverridden = appState.approvalStatus === "OVERRIDDEN" || appState.isOverridden;
  if (reasonBlock) reasonBlock.style.display = isOverridden ? "block" : "none";
  if (overrideBadge) overrideBadge.style.display = isOverridden ? "inline-block" : "none";

  updateTelemetryHeader();
}

function updateTelemetryHeader() {
  const heatNum = document.getElementById("telemetry-heat-num");
  const gradeName = document.getElementById("telemetry-grade-name");
  const statusTag = document.getElementById("telemetry-status-tag");

  if (heatNum) heatNum.textContent = appState.activeHeatNumber;

  const g = appState.grades[appState.selectedGradeId];
  if (gradeName && g) gradeName.textContent = g.name.split('(')[0].trim();

  if (statusTag) {
    statusTag.className = `status-tag ${appState.approvalStatus.toLowerCase().replace('_', '-')}`;
    statusTag.textContent = appState.approvalStatus.replace('_', ' ');
  }
}

async function handleSaveAndApprove() {
  const opInput = document.getElementById("operator-name-input");
  const reasonInput = document.getElementById("override-reason-input");
  const feedback = document.getElementById("save-heat-feedback");

  const operator = (opInput?.value || "").trim();
  if (!operator) {
    alert("Please enter the Melting Supervisor / Melter Name before approving.");
    opInput?.focus();
    return;
  }
  appState.operatorName = operator;

  if (appState.approvalStatus === "OVERRIDDEN") {
    const reason = (reasonInput?.value || "").trim();
    if (!reason) {
      alert("Override Justification is mandatory when approving a modified addition plan.");
      reasonInput?.focus();
      return;
    }
    appState.overrideReason = reason;
  }

  const res = appState.lastOptimizationResult;
  if (!res) return;

  const actualAdditions = (res.recommendations || []).map(r => ({
    alloy_id: r.alloy_id,
    short_name: r.short_name,
    weight_kg: appState.manualOverrides[r.alloy_id] ?? r.quantity_kg,
    cost_inr: (r.cost_inr_per_kg || 100) * (appState.manualOverrides[r.alloy_id] ?? r.quantity_kg),
    cost_usd: (r.cost_per_kg || 1) * (appState.manualOverrides[r.alloy_id] ?? r.quantity_kg),
    sacks: r.full_bags,
    bag_size_kg: r.bag_size_kg,
    trim_kg: r.loose_kg
  }));

  const payload = {
    heat_number: appState.activeHeatNumber,
    grade_id: appState.selectedGradeId,
    grade_name: appState.grades[appState.selectedGradeId]?.name || appState.selectedGradeId,
    melt_weight_kg: appState.meltWeight,
    mode: appState.mode,
    input_chemistry: appState.currentChemistry,
    final_chemistry: res.final_composition || {},
    recommendations: res.recommendations || [],
    actual_additions: actualAdditions,
    violations: res.violations || [],
    total_cost_inr: res.total_cost_inr || 0,
    total_cost_usd: res.total_cost || 0,
    status: appState.approvalStatus,
    operator_name: appState.operatorName,
    override_reason: appState.overrideReason
  };

  try {
    const saveRes = await fetch("/api/heats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    if (saveRes.heat && saveRes.heat.id) {
      appState.lastSavedHeatId = saveRes.heat.id;
      if (feedback) {
        feedback.style.color = "#15803d";
        feedback.textContent = `✓ Recorded Heat #${appState.activeHeatNumber} into SQLite Audit Database`;
      }
      alert(`Heat #${appState.activeHeatNumber} approved and logged successfully!`);
      await fetchNextHeatNumber();
      await refreshHeatLogCount();
    }
  } catch (e) {
    alert("Error logging heat: " + e.message);
  }
}

function exportCurrentPDF() {
  if (!appState.lastSavedHeatId) {
    alert("Please approve/record the heat first to log it in the official audit trail, then export.");
    return;
  }
  window.open(`/api/heats/${appState.lastSavedHeatId}/export?format=pdf`, "_blank");
}

function exportCurrentCSV() {
  if (!appState.lastSavedHeatId) {
    alert("Please approve/record the heat first to log it in the official audit trail, then export.");
    return;
  }
  window.open(`/api/heats/${appState.lastSavedHeatId}/export?format=csv`, "_blank");
}

// ==========================================================================
// 9. TAB 2: CORRIDORS & MASS BALANCE LEDGER
// ==========================================================================
function renderCorridorAnalysis(res) {
  const container = document.getElementById("corridor-bars-container");
  const mbTbody = document.getElementById("mass-balance-table-body");
  const dualsContainer = document.getElementById("binding-constraints-container");
  const expContainer = document.getElementById("explanations-container");

  const g = appState.grades[appState.selectedGradeId];
  if (!g) return;

  const finalComp = res.final_composition || {};
  const violationsMap = {};
  (res.violations || []).forEach(v => { violationsMap[v.element] = v; });

  // 1. Corridor Visual Gauges
  if (container) {
    container.innerHTML = "";
    Object.entries(g.elements).forEach(([el, spec]) => {
      const c0 = appState.currentChemistry[el] ?? spec.target;
      const cFin = finalComp[el] ?? c0;
      const hasViolation = violationsMap[el] !== undefined;

      const span = Math.max(spec.max - spec.min, 0.05);
      const minD = Math.max(0, spec.min - span * 0.4);
      const maxD = spec.max + span * 0.4;
      const range = maxD - minD;
      const toPct = (val) => Math.max(0, Math.min(100, ((val - minD) / range) * 100));

      const leftWindow = toPct(spec.min);
      const widthWindow = toPct(spec.max) - leftWindow;
      const targetPos = toPct(spec.target);
      const c0Pos = toPct(c0);
      const cFinPos = toPct(cFin);

      const row = document.createElement("div");
      row.className = "corridor-row";
      row.innerHTML = `
        <div class="corridor-header-row">
          <div>
            <strong>${el}</strong>
            <span style="color:var(--text-faint); font-size:10.5px; margin-left:6px;">[Min: ${spec.min}% | Max: ${spec.max}%]</span>
          </div>
          <div>
            <span style="color:#0284c7;">${c0.toFixed(3)}%</span> &rarr;
            <strong style="color:${hasViolation ? '#dc2626' : '#15803d'};">${cFin.toFixed(3)}%</strong>
          </div>
        </div>
        <div class="corridor-bar-bg">
          <div class="corridor-window-fill" style="left:${leftWindow}%; width:${widthWindow}%;"></div>
          <div class="corridor-target-notch" style="left:${targetPos}%;"></div>
          <div class="corridor-dot init" style="left:${c0Pos}%;" title="Initial: ${c0}%"></div>
          <div class="corridor-dot final ${hasViolation ? 'violation' : ''}" style="left:${cFinPos}%;" title="Final: ${cFin}%"></div>
        </div>
      `;
      container.appendChild(row);
    });
  }

  // 2. Elemental Mass Balance Ledger Table
  if (mbTbody) {
    mbTbody.innerHTML = "";
    const m0 = appState.meltWeight || 4000.0;
    const mFin = res.final_melt_weight_kg || (m0 + (res.total_added_kg || 0));

    Object.entries(g.elements).forEach(([el, spec]) => {
      const c0 = appState.currentChemistry[el] ?? spec.target;
      const cFin = finalComp[el] ?? c0;
      const baseMassKg = (m0 * c0) / 100.0;
      const targetMassKg = (mFin * spec.target) / 100.0;
      const deficitKg = Math.max(0, targetMassKg - baseMassKg);
      const finalMassKg = (mFin * cFin) / 100.0;
      const retainedYieldKg = Math.max(0, finalMassKg - baseMassKg);
      const hasViolation = violationsMap[el] !== undefined;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${el}</strong></td>
        <td style="text-align:right; font-family:var(--font-mono);">${baseMassKg.toFixed(2)} kg</td>
        <td style="text-align:right; font-family:var(--font-mono);">${targetMassKg.toFixed(2)} kg</td>
        <td style="text-align:right; font-family:var(--font-mono); color:#ea580c; font-weight:700;">${deficitKg > 0 ? `${deficitKg.toFixed(2)} kg` : '0.00 kg'}</td>
        <td style="text-align:right; font-family:var(--font-mono); color:#15803d;">+${retainedYieldKg.toFixed(2)} kg</td>
        <td style="text-align:right; font-family:var(--font-mono); font-weight:700;">${cFin.toFixed(3)}%</td>
        <td style="text-align:center;">
          <span class="channel-tag ${hasViolation ? 'deficit' : 'in-spec'}">${hasViolation ? 'OUT OF SPEC' : 'PASS'}</span>
        </td>
      `;
      mbTbody.appendChild(tr);
    });
  }

  // 3. Dual Shadow Prices
  if (dualsContainer) {
    dualsContainer.innerHTML = "";
    const bcs = res.binding_constraints || [];
    if (bcs.length === 0) {
      dualsContainer.innerHTML = `<div style="font-size:11.5px; color:var(--text-faint); padding:6px;">No dual constraints actively binding.</div>`;
    } else {
      bcs.forEach(bc => {
        const shadowPrice = appState.currency === "INR" ? `₹${bc.shadow_price_inr}/kg` : `$${bc.shadow_price_usd}/kg`;
        const div = document.createElement("div");
        div.style.background = "#ffffff";
        div.style.border = "1px solid var(--border-light)";
        div.style.borderRadius = "4px";
        div.style.padding = "8px 10px";
        div.innerHTML = `
          <div style="font-size:11px; font-weight:700; color:var(--text-main); font-family:var(--font-mono);">${bc.element} (${bc.type.toUpperCase()})</div>
          <div style="font-size:14px; font-weight:800; color:#ea580c; font-family:var(--font-mono);">${shadowPrice}</div>
          <div style="font-size:10px; color:var(--text-faint); margin-top:2px;">${bc.description}</div>
        `;
        dualsContainer.appendChild(div);
      });
    }
  }

  // 4. Rationale Narratives
  if (expContainer) {
    expContainer.innerHTML = "";
    (res.explanations || []).forEach(exp => {
      const item = document.createElement("div");
      item.style.fontSize = "11.5px";
      item.style.marginBottom = "6px";
      item.style.lineHeight = "1.4";
      item.innerHTML = `<strong>${exp.alloy_name}:</strong> <span style="color:var(--text-muted);">${exp.rationale}</span>`;
      expContainer.appendChild(item);
    });
  }
}

// ==========================================================================
// 10. TAB 3: ECONOMICS & WHAT-IF COMPARISON
// ==========================================================================
async function triggerWhatIfComparison() {
  const g = appState.grades[appState.selectedGradeId];
  if (!g) return;

  const heatsPerDay = parseFloat(document.getElementById("whatif-heats-per-day")?.value) || 12.0;
  const daysPerYear = parseFloat(document.getElementById("whatif-days-per-year")?.value) || 300.0;

  const payload = {
    grade_id: appState.selectedGradeId,
    melt_weight_kg: appState.meltWeight,
    current_composition: appState.currentChemistry,
    disabled_alloy_ids: Array.from(appState.disabledAlloys),
    mode: appState.mode,
    heats_per_day: heatsPerDay,
    working_days_per_year: daysPerYear
  };

  try {
    const res = await fetch("/api/what-if", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    appState.lastWhatIfResult = res;
    renderWhatIfContent(res);
  } catch (e) {
    console.error("What-If calculation failed:", e);
  }
}

function renderWhatIfContent(whatIfRes) {
  const container = document.getElementById("whatif-comparison-content");
  if (!container) return;

  const comp = whatIfRes.comparison || {};
  const isNaiveValid = comp.naive_is_in_spec !== false;

  const lpCost = comp.lp_cost_inr || (comp.lp_cost_usd * appState.fxRate);
  const naiveCost = comp.naive_cost_inr || (comp.naive_cost_usd * appState.fxRate);
  const savingsINR = comp.cost_savings_inr || 0;
  const annualLakhs = comp.annual_savings_lakhs ?? 0;

  let compHtml = `
    <div class="whatif-comparison-grid">
      
      <!-- LP Multi-Carrier Card -->
      <div class="compare-card lp">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <strong style="color:#15803d; font-size:13px; text-transform:uppercase;">VULCAN Joint LP Optimizer</strong>
          <span class="status-tag approved">100% IN SPEC</span>
        </div>
        <div style="font-size:22px; font-weight:800; font-family:var(--font-mono); color:#15803d;">
          ${appState.currency === 'INR' ? `₹${Math.round(lpCost).toLocaleString('en-IN')}` : `$${comp.lp_cost_usd.toFixed(2)}`}
        </div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
          Simultaneously optimizes primary & secondary carrier elements. Eliminates scrap risks.
        </div>
      </div>

      <!-- Traditional Heuristic Card -->
      <div class="compare-card ${isNaiveValid ? '' : 'manual'}">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <strong style="font-size:13px; text-transform:uppercase; color:${isNaiveValid ? 'var(--text-main)' : 'var(--signal-red)'};">
            Manual Single-Alloy Heuristic
          </strong>
          <span class="status-tag ${isNaiveValid ? 'under-review' : 'rejected'}">
            ${isNaiveValid ? 'IN SPEC' : 'OUT OF SPEC'}
          </span>
        </div>
        <div style="font-size:22px; font-weight:800; font-family:var(--font-mono); color:${isNaiveValid ? 'var(--text-main)' : 'var(--signal-red)'};">
          ${appState.currency === 'INR' ? `₹${Math.round(naiveCost).toLocaleString('en-IN')}` : `$${comp.naive_cost_usd.toFixed(2)}`}
        </div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
          ${isNaiveValid ? 'Single-element proportional additions.' : `<b style="color:var(--signal-red);">${comp.naive_out_of_spec_reason || 'Cross-contamination exceeded ceiling.'}</b>`}
        </div>
      </div>

    </div>
  `;

  if (isNaiveValid && savingsINR > 0) {
    compHtml += `
      <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; margin-top:14px;">
        <div style="background:#f8fafc; border:1px solid var(--border-light); padding:12px; border-radius:4px;">
          <div style="font-size:10.5px; font-family:var(--font-mono); color:var(--text-faint); text-transform:uppercase;">Per-Heat Savings</div>
          <div style="font-size:18px; font-weight:800; color:#15803d; font-family:var(--font-mono); margin-top:2px;">
            ₹${Math.round(savingsINR).toLocaleString('en-IN')} (${comp.cost_savings_pct.toFixed(1)}%)
          </div>
        </div>
        <div style="background:#f8fafc; border:1px solid var(--border-light); padding:12px; border-radius:4px;">
          <div style="font-size:10.5px; font-family:var(--font-mono); color:var(--text-faint); text-transform:uppercase;">Annual Plant Value</div>
          <div style="font-size:18px; font-weight:800; color:#ea580c; font-family:var(--font-mono); margin-top:2px;">
            ₹${annualLakhs.toFixed(1)} Lakhs / Year
          </div>
        </div>
      </div>
    `;
  }

  container.innerHTML = compHtml;
}

function renderAlloyToggles() {
  const container = document.getElementById("alloys-toggle-container");
  if (!container) return;
  container.innerHTML = "";

  appState.alloys.forEach(a => {
    const item = document.createElement("div");
    item.className = "stockout-item";
    item.innerHTML = `
      <div>
        <div style="font-weight:700; color:var(--text-main);">${a.short_name || a.name}</div>
        <div style="font-size:10.5px; color:var(--text-faint); font-family:var(--font-mono);">
          Rate: ₹${Math.round(a.cost_inr_per_kg || a.cost_per_kg * 84)}/kg
        </div>
      </div>
      <label style="cursor:pointer; display:flex; align-items:center; gap:6px; font-family:var(--font-mono); font-size:11px;">
        <input type="checkbox" ${appState.disabledAlloys.has(a.id) ? '' : 'checked'}>
        <span>${appState.disabledAlloys.has(a.id) ? '<b style="color:var(--signal-red);">DEPLETED</b>' : '<b style="color:var(--signal-green);">IN STOCK</b>'}</span>
      </label>
    `;

    const chk = item.querySelector("input");
    chk.onchange = (e) => {
      if (e.target.checked) appState.disabledAlloys.delete(a.id);
      else appState.disabledAlloys.add(a.id);
      renderAlloyToggles();
      triggerOptimize();
      triggerWhatIfComparison();
    };

    container.appendChild(item);
  });
}

// ==========================================================================
// 11. TAB 4: HEAT LOG & AUDIT TRAIL
// ==========================================================================
async function loadHeatLogRecords(searchQuery = "") {
  const container = document.getElementById("heat-log-table-container");
  if (!container) return;

  container.innerHTML = `<div style="padding:16px; color:var(--text-faint); font-size:12px;">Loading heat records from SQLite...</div>`;

  try {
    const url = searchQuery ? `/api/heats?search=${encodeURIComponent(searchQuery)}` : `/api/heats`;
    const res = await fetch(url).then(r => r.json());
    const heats = res.heats || [];

    const countBadge = document.getElementById("tab-heat-count");
    if (countBadge) countBadge.textContent = heats.length;

    if (heats.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:28px; color:var(--text-faint); font-size:13px;">No recorded heats found in audit database.</div>`;
      return;
    }

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Heat Number</th>
            <th>Logged At</th>
            <th>Target Grade</th>
            <th style="text-align:right;">Melt Weight</th>
            <th style="text-align:right;">Charge Cost</th>
            <th>Approval Status</th>
            <th>Melter / Operator</th>
            <th style="text-align:center;">Dispatch Ticket</th>
          </tr>
        </thead>
        <tbody>
    `;

    heats.forEach(h => {
      const timeStr = (h.created_at || "").substring(0, 16).replace('T', ' ');
      const statusClass = (h.status || 'CALCULATED').toLowerCase().replace('_', '-');
      html += `
        <tr>
          <td><strong style="font-family:var(--font-mono); color:#ea580c;">${h.heat_number}</strong></td>
          <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted);">${timeStr}</td>
          <td><b>${h.grade_name || h.grade_id}</b></td>
          <td style="text-align:right; font-family:var(--font-mono);">${h.melt_weight_kg} kg</td>
          <td style="text-align:right; font-family:var(--font-mono); font-weight:700;">₹${Math.round(h.total_cost_inr || 0).toLocaleString('en-IN')}</td>
          <td><span class="status-tag ${statusClass}">${h.status}</span></td>
          <td>${h.operator_name || 'Unassigned'}</td>
          <td style="text-align:center;">
            <div style="display:flex; justify-content:center; gap:6px;">
              <a href="/api/heats/${h.id}/export?format=pdf" target="_blank" class="ind-btn ind-btn-secondary" style="font-size:10px; padding:2px 8px;">PDF</a>
              <a href="/api/heats/${h.id}/export?format=csv" target="_blank" class="ind-btn ind-btn-secondary" style="font-size:10px; padding:2px 8px;">CSV</a>
            </div>
          </td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div style="padding:16px; color:var(--signal-red);">Error loading heat audit trail: ${e.message}</div>`;
  }
}

// ==========================================================================
// 12. TAB 5: MASTER RECIPE SETTINGS
// ==========================================================================
function renderSettingsTab() {
  renderGradeRecipes();
  renderAlloyCatalogTable();
}

function renderGradeRecipes() {
  const container = document.getElementById("grade-recipes-container");
  if (!container) return;
  container.innerHTML = "";

  Object.values(appState.grades).forEach(g => {
    const card = document.createElement("div");
    card.style.background = "#f8fafc";
    card.style.border = "1px solid var(--border-light)";
    card.style.borderRadius = "var(--radius-sm)";
    card.style.padding = "14px";
    card.style.marginBottom = "12px";

    const corridors = Object.entries(g.elements || {}).map(([el, spec]) => `
      <span style="font-family:var(--font-mono); font-size:11px; background:#ffffff; border:1px solid var(--border-medium); padding:2px 6px; border-radius:3px;">
        <b>${el}</b>: ${spec.min} - <b>${spec.target}</b> - ${spec.max}%
      </span>
    `).join(" ");

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <strong style="font-size:13px; color:var(--text-main);">${g.name}</strong>
        <span class="status-tag calculated">${g.category}</span>
      </div>
      <div style="font-size:11.5px; color:var(--text-muted); margin-bottom:8px;">
        ${g.casting_part ? `<b>Part:</b> ${g.casting_part} &bull; ` : ''}Default Weight: ${g.default_weight_kg || 4000} kg
        ${g.ce_formula ? ` &bull; <b>CE Formula:</b> ${g.ce_formula}` : ''}
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:5px;">${corridors}</div>
    `;

    container.appendChild(card);
  });
}

function renderAlloyCatalogTable() {
  const container = document.getElementById("alloys-catalog-container");
  if (!container) return;
  container.innerHTML = "";

  let html = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Alloy Name</th>
          <th>Element Fraction (%)</th>
          <th>Recovery Factors (%)</th>
          <th style="text-align:right;">Cost (₹/kg)</th>
          <th style="text-align:right;">Cost ($/kg)</th>
          <th style="text-align:right;">Sack Size</th>
        </tr>
      </thead>
      <tbody>
  `;

  appState.alloys.forEach(a => {
    const compStr = Object.entries(a.composition || {}).map(([el, f]) => `${el}: ${(f*100).toFixed(1)}%`).join(", ");
    const recStr = Object.entries(a.recovery || {}).map(([el, r]) => `${el}: ${(r*100).toFixed(0)}%`).join(", ");

    html += `
      <tr>
        <td>
          <strong>${a.short_name || a.name}</strong>
          <div style="font-size:10px; color:var(--text-faint);">${a.id}</div>
        </td>
        <td style="font-family:var(--font-mono); font-size:11px;">${compStr}</td>
        <td style="font-family:var(--font-mono); font-size:11px; color:#15803d;">${recStr}</td>
        <td style="text-align:right; font-family:var(--font-mono); font-weight:700;">₹${Math.round(a.cost_inr_per_kg || a.cost_per_kg * 84)}</td>
        <td style="text-align:right; font-family:var(--font-mono);">$${a.cost_per_kg.toFixed(2)}</td>
        <td style="text-align:right; font-family:var(--font-mono);">${a.bag_size_kg || 25} kg</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
}

async function handleResetAlloys() {
  if (!confirm("Reset all alloy recoveries, compositions, and prices to factory standard catalog defaults?")) return;
  try {
    await fetch("/api/alloys/reset", { method: "POST" });
    await loadCatalogData();
    renderAlloyCatalogTable();
    triggerOptimize();
  } catch (e) {
    alert("Error resetting alloys: " + e.message);
  }
}

async function handleResetGrades() {
  if (!confirm("Reset all grade recipes to factory standards?")) return;
  try {
    await fetch("/api/grades/reset", { method: "POST" });
    await loadCatalogData();
    renderGradeRecipes();
    selectGrade(appState.selectedGradeId);
  } catch (e) {
    alert("Error resetting grades: " + e.message);
  }
}
