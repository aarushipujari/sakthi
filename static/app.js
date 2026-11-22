/**
 * VULCAN // SAKTHI MELT-OS - CLIENT CONTROLLER
 * Zero CDN Dependencies • 100% Offline Self-Contained SCADA Interface
 * High-Contrast Foundry Light Theme & Precision Decision Support Engine
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
  operatorName: "K. Murugan",
  overrideReason: "",
  manualOverrides: {}, // { alloy_id: weight_kg }
  isOverridden: false
};

// 1. OFFLINE EMBEDDED VECTOR ICONS (Zero CDN / No Lucide Dependency)
function getIcon(name, cls = "w-4 h-4") {
  const s = 'style="display:inline-block; vertical-align:middle; width:16px; height:16px; stroke-width:2; stroke:currentColor; fill:none; stroke-linecap:round; stroke-linejoin:round;"';
  const icons = {
    flame: `<svg ${s} viewBox="0 0 24 24"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`,
    upload: `<svg ${s} viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
    download: `<svg ${s} viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
    check: `<svg ${s} viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`,
    activity: `<svg ${s} viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
    printer: `<svg ${s} viewBox="0 0 24 24"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>`,
    play: `<svg ${s} viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
    rotate: `<svg ${s} viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>`,
    info: `<svg ${s} viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    layers: `<svg ${s} viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
    boxes: `<svg ${s} viewBox="0 0 24 24"><path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l6 3.43a2 2 0 0 0 2.06 0l6-3.43a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L11 9.49a2 2 0 0 0-2.06 0l-5.97 3.43z"/><path d="m21.5 6.5-6-3.43a2 2 0 0 0-2.06 0L7.47 6.5"/><path d="M12 22.08V12"/></svg>`,
    history: `<svg ${s} viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>`,
    binary: `<svg ${s} viewBox="0 0 24 24"><rect x="14" y="4" width="4" height="6" rx="2"/><rect x="6" y="4" width="4" height="6" rx="2"/><rect x="6" y="14" width="4" height="6" rx="2"/><rect x="14" y="14" width="4" height="6" rx="2"/></svg>`,
    trending: `<svg ${s} viewBox="0 0 24 24"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
    x: `<svg ${s} viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    chevronDown: `<svg ${s} viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>`,
    chevronRight: `<svg ${s} viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>`,
    alert: `<svg ${s} viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
  };
  return icons[name] || icons.info;
}

function injectStaticIcons() {
  const mapping = {
    "logo-icon": "flame", "icon-flame": "flame", "icon-upload": "upload",
    "icon-dropzone": "upload", "icon-activity": "activity", "icon-rotate": "rotate",
    "icon-play": "play", "icon-boxes-small": "boxes", "icon-dispatch": "flame",
    "icon-corridor": "activity", "icon-check": "check", "icon-pdf": "download",
    "icon-csv": "download", "icon-binary": "binary", "icon-trending": "trending",
    "icon-boxes": "boxes", "icon-layers": "layers", "icon-history": "history",
    "icon-printer": "printer", "icon-alloy-modal": "boxes", "icon-close-alloy": "x",
    "icon-grade-modal": "layers", "icon-close-grade": "x", "icon-history-modal": "history",
    "icon-close-heats": "x", "icon-ticket": "printer", "icon-close-ticket": "x",
    "icon-print-action": "printer", "icon-trace-chevron": "chevronDown", "icon-whatif-chevron": "chevronDown"
  };
  for (const [id, icon] of Object.entries(mapping)) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = getIcon(icon);
  }
}

// 2. CURRENCY FORMATTING
function formatCurrency(amountUSD) {
  if (appState.currency === "INR") {
    const valINR = (amountUSD || 0) * appState.fxRate;
    return `₹${Math.round(valINR).toLocaleString('en-IN')}`;
  }
  return `$${(amountUSD || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// 3. LIFECYCLE INIT
document.addEventListener("DOMContentLoaded", async () => {
  injectStaticIcons();
  await loadCatalogData();
  await fetchNextHeatNumber();
  setupEventListeners();
  selectGrade(appState.selectedGradeId);
});

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

async function loadCatalogData() {
  try {
    const [gradesRes, alloysRes, elementsRes] = await Promise.all([
      fetch("/api/grades").then(r => r.json()),
      fetch("/api/alloys").then(r => r.json()),
      fetch("/api/elements").then(r => r.json()).catch(() => ({ elements: {} }))
    ]);

    appState.grades = {};
    gradesRes.grades.forEach(g => { appState.grades[g.id] = g; });
    appState.alloys = alloysRes.alloys;
    appState.elementsMeta = elementsRes.elements || {};

    renderPresetStrip();
    renderGradeDropdown();
    renderAlloyToggles();
  } catch (e) {
    console.error("Failed to load catalog data:", e);
  }
}

// 4. UI RENDERING & EVENT HANDLERS
function setupEventListeners() {
  // Currency Toggle
  document.getElementById("curr-inr-btn")?.addEventListener("click", () => setCurrency("INR"));
  document.getElementById("curr-usd-btn")?.addEventListener("click", () => setCurrency("USD"));

  // Grade Selector
  document.getElementById("grade-select")?.addEventListener("change", (e) => {
    selectGrade(e.target.value);
  });

  // Melt Weight Input
  document.getElementById("melt-weight-input")?.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value) || 4000.0;
    appState.meltWeight = Math.max(100.0, Math.min(50000.0, val));
    debounceOptimize();
  });

  // Mode Radio
  document.querySelectorAll("input[name='opt-mode']").forEach(radio => {
    radio.addEventListener("change", (e) => {
      appState.mode = e.target.value;
      debounceOptimize();
    });
  });

  // Reset Reading Button
  document.getElementById("reset-reading-btn")?.addEventListener("click", () => {
    const g = appState.grades[appState.selectedGradeId];
    if (g && g.demo_reading) {
      appState.currentChemistry = { ...g.demo_reading };
      renderSpectroInputs();
      debounceOptimize();
    }
  });

  // Recalculate Button
  document.getElementById("solve-btn")?.addEventListener("click", () => triggerOptimize());

  // Drag and Drop Spectrometer File
  setupDropzone();

  // Navigation Modals
  document.getElementById("nav-alloys-btn")?.addEventListener("click", openAlloyModal);
  document.getElementById("nav-grades-btn")?.addEventListener("click", openGradeModal);
  document.getElementById("nav-heats-btn")?.addEventListener("click", openHeatLogModal);
  document.getElementById("quick-slip-btn")?.addEventListener("click", openSlipModal);

  // Verification & Sign-off Actions
  document.getElementById("save-heat-btn")?.addEventListener("click", handleSaveAndApprove);
  document.getElementById("mobile-approve-btn")?.addEventListener("click", handleSaveAndApprove);
  document.getElementById("export-pdf-btn")?.addEventListener("click", exportCurrentPDF);
  document.getElementById("export-csv-btn")?.addEventListener("click", exportCurrentCSV);

  // Approval Status Select
  document.getElementById("approval-status-select")?.addEventListener("change", (e) => {
    appState.approvalStatus = e.target.value;
    updateApprovalStatusUI();
  });

  // Accordion Toggles
  setupAccordions();

  // Reset Catalogs Buttons
  document.getElementById("reset-alloys-btn")?.addEventListener("click", handleResetAlloys);
  document.getElementById("reset-grades-btn")?.addEventListener("click", handleResetGrades);
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

function selectGrade(gradeId) {
  if (!appState.grades[gradeId]) return;
  appState.selectedGradeId = gradeId;
  const grade = appState.grades[gradeId];

  // Update UI Select
  const sel = document.getElementById("grade-select");
  if (sel) sel.value = gradeId;

  // Update App Note
  const partText = document.getElementById("casting-part-text");
  if (partText) partText.textContent = grade.casting_part || grade.category || "";

  // Update Melt Weight
  if (grade.default_weight_kg) {
    appState.meltWeight = grade.default_weight_kg;
    const wtInput = document.getElementById("melt-weight-input");
    if (wtInput) wtInput.value = grade.default_weight_kg;
  }

  // Set Demo Reading
  appState.currentChemistry = { ...(grade.demo_reading || {}) };
  appState.manualOverrides = {};
  appState.isOverridden = false;
  appState.approvalStatus = "CALCULATED";

  updateTelemetryHeader();
  renderPresetStrip();
  renderSpectroInputs();
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

function renderPresetStrip() {
  const container = document.getElementById("preset-strip-container");
  if (!container) return;
  container.innerHTML = "";

  Object.values(appState.grades).forEach(g => {
    const btn = document.createElement("button");
    btn.className = `preset-btn ${g.id === appState.selectedGradeId ? 'active' : ''}`;
    btn.textContent = g.name.split('(')[0].trim();
    btn.onclick = () => selectGrade(g.id);
    container.appendChild(btn);
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

function renderSpectroInputs() {
  const container = document.getElementById("spectro-channels-container");
  if (!container) return;
  container.innerHTML = "";

  const g = appState.grades[appState.selectedGradeId];
  if (!g) return;

  Object.entries(g.elements).forEach(([el, spec]) => {
    const val = appState.currentChemistry[el] ?? spec.target;
    const delta = val - spec.target;
    const deltaClass = Math.abs(delta) < 0.01 ? 'ok' : (delta < 0 ? 'deficit' : 'excess');
    const deltaSign = delta >= 0 ? '+' : '';

    const tile = document.createElement("div");
    tile.className = "channel-tile";
    tile.innerHTML = `
      <div class="channel-header">
        <span class="channel-sym">${el}</span>
        <span class="channel-target">Target: ${spec.target}%</span>
      </div>
      <div class="channel-input-wrap">
        <input type="number" step="${spec.step || 0.01}" value="${val}" class="channel-input" data-el="${el}">
      </div>
      <div class="channel-delta ${deltaClass}" id="delta-${el}">${deltaSign}${delta.toFixed(3)}%</div>
    `;

    const input = tile.querySelector("input");
    input.addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      if (!isNaN(v)) {
        appState.currentChemistry[el] = v;
        const newDelta = v - spec.target;
        const dEl = document.getElementById(`delta-${el}`);
        if (dEl) {
          dEl.className = `channel-delta ${Math.abs(newDelta) < 0.01 ? 'ok' : (newDelta < 0 ? 'deficit' : 'excess')}`;
          dEl.textContent = `${newDelta >= 0 ? '+' : ''}${newDelta.toFixed(3)}%`;
        }
        debounceOptimize();
      }
    });

    container.appendChild(tile);
  });
}

function renderAlloyToggles() {
  const container = document.getElementById("alloys-toggle-container");
  if (!container) return;
  container.innerHTML = "";

  appState.alloys.forEach(a => {
    const wrap = document.createElement("label");
    wrap.style.display = "flex";
    wrap.style.alignItems = "center";
    wrap.style.gap = "6px";
    wrap.style.fontSize = "11.5px";
    wrap.style.cursor = "pointer";

    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.checked = !appState.disabledAlloys.has(a.id);
    chk.onchange = (e) => {
      if (e.target.checked) appState.disabledAlloys.delete(a.id);
      else appState.disabledAlloys.add(a.id);
      debounceOptimize();
    };

    wrap.appendChild(chk);
    const span = document.createElement("span");
    span.textContent = a.short_name || a.name;
    wrap.appendChild(span);
    container.appendChild(wrap);
  });
}

// 5. SPECTROMETER DROPZONE INTEGRATION
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
        // If detected grade differs, prompt or set
        if (data.detected_grade_id && data.detected_grade_id !== appState.selectedGradeId && appState.grades[data.detected_grade_id]) {
          appState.selectedGradeId = data.detected_grade_id;
          selectGrade(data.detected_grade_id);
        }

        // Apply readings
        Object.assign(appState.currentChemistry, data.composition);
        renderSpectroInputs();

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

// 6. SOLVER INTEGRATION & DEBOUNCING
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
    const [optRes, whatIfRes] = await Promise.all([
      fetch("/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(r => r.json()),
      fetch("/api/what-if", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(r => r.json()).catch(() => null)
    ]);

    appState.lastOptimizationResult = optRes;
    appState.lastWhatIfResult = whatIfRes;

    renderVerdictBanner(optRes);
    renderKPIs(optRes);
    renderChargingTable(optRes);
    renderCorridorBars(optRes);
    renderTraceability(optRes);
    if (whatIfRes) renderWhatIf(whatIfRes);

    updateTelemetryHeader();
  } catch (e) {
    console.error("Optimization failed:", e);
  }
}

// 7. DECISION & KPI RENDERING
function renderVerdictBanner(res) {
  const container = document.getElementById("verdict-banner-container");
  if (!container) return;

  if (!res.success) {
    container.innerHTML = `
      <div class="verdict-banner violation">
        ${getIcon("alert")}
        <div>
          <b>Optimization Blocked:</b> ${res.message || "Unable to find feasible addition plan."}
        </div>
      </div>
    `;
    return;
  }

  const hasViolations = res.violations && res.violations.length > 0;
  const hasAlerts = res.over_spec_alerts && res.over_spec_alerts.length > 0;

  if (hasViolations || hasAlerts) {
    let violationList = "";
    if (hasViolations) {
      violationList += res.violations.map(v => `<li>${v.reason}</li>`).join("");
    }
    if (hasAlerts) {
      violationList += res.over_spec_alerts.map(a => `<li>${a.reason}</li>`).join("");
    }
    container.innerHTML = `
      <div class="verdict-banner violation">
        ${getIcon("alert")}
        <div>
          <b>Attention Required — Corridor Constraint Active:</b>
          <ul style="margin-top:4px; padding-left:16px;">${violationList}</ul>
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div class="verdict-banner in-spec">
        ${getIcon("check")}
        <div>
          <b>All Channels In Spec:</b> Optimal alloy charge brings every element strictly into grade corridor window. Ready for ladle dispatch.
        </div>
      </div>
    `;
  }
}

function renderKPIs(res) {
  const costEl = document.getElementById("kpi-total-cost");
  const weightEl = document.getElementById("kpi-total-weight");
  const weightSub = document.getElementById("kpi-weight-sub");
  const mobileCost = document.getElementById("mobile-cost-val");

  const totCost = res.total_cost || 0;
  const totWeight = res.total_added_kg || 0;

  if (costEl) costEl.textContent = formatCurrency(totCost);
  if (mobileCost) mobileCost.textContent = formatCurrency(totCost);
  if (weightEl) weightEl.textContent = `${totWeight.toFixed(2)} kg`;

  const dilutionPct = ((totWeight / (appState.meltWeight || 4000.0)) * 100).toFixed(1);
  if (weightSub) weightSub.textContent = `+${dilutionPct}% Melt Dilution`;

  // Carbon Equivalent & Liquidus (Phase 1, Item 5)
  const ceCard = document.getElementById("kpi-ce-card");
  const tliqCard = document.getElementById("kpi-tliq-card");

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

// 8. CHARGING TABLE & EDITABLE OVERRIDES
function renderChargingTable(res) {
  const tbody = document.getElementById("charging-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const recs = res.recommendations || [];
  if (recs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:18px; color:var(--text-muted);">No alloy additions needed. Base melt chemistry is in specification.</td></tr>`;
    return;
  }

  recs.forEach((r, idx) => {
    const overrideVal = appState.manualOverrides[r.alloy_id] ?? r.quantity_kg;
    const isModified = Math.abs(overrideVal - r.quantity_kg) > 0.01;
    const cost = appState.currency === "INR" ? (r.total_cost_inr || r.total_cost * appState.fxRate) : r.total_cost;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td style="font-family:var(--font-mono); font-weight:700; color:var(--text-muted);">${r.charge_order || idx + 1}</td>
      <td>
        <div style="font-weight:700; color:var(--text-primary);">${r.short_name || r.name}</div>
        <div style="font-size:10.5px; color:var(--text-muted);">${r.alloy_name || ''}</div>
      </td>
      <td style="text-align:right; font-family:var(--font-mono); font-weight:700;">${r.quantity_kg.toFixed(2)} kg</td>
      <td style="text-align:right;">
        <input type="number" step="0.1" value="${overrideVal}" class="charging-input ${isModified ? 'modified' : ''}" data-alloy="${r.alloy_id}">
      </td>
      <td style="font-size:11px; font-family:var(--font-mono);">
        ${r.full_bags > 0 ? `<b>${r.full_bags}</b> sack (${r.bag_size_kg}kg) + <b>${r.loose_kg.toFixed(1)}kg</b> trim` : `<b>${r.loose_kg.toFixed(1)}kg</b> trim`}
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
      // Re-render corridor with simulated results
      renderCorridorBars({
        final_composition: res.predicted_composition,
        violations: res.violations
      });

      // Show banner if violation
      if (res.violations && res.violations.length > 0) {
        const container = document.getElementById("verdict-banner-container");
        if (container) {
          container.innerHTML = `
            <div class="verdict-banner violation">
              ${getIcon("alert")}
              <div>
                <b>Manual Override Out of Spec:</b> Operator modification caused corridor violations:
                <ul style="margin-top:4px; padding-left:16px;">
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

// 9. CHEMISTRY CORRIDOR BARS
function renderCorridorBars(res) {
  const container = document.getElementById("corridor-bars-container");
  if (!container) return;
  container.innerHTML = "";

  const g = appState.grades[appState.selectedGradeId];
  if (!g) return;

  const finalComp = res.final_composition || {};
  const violationsMap = {};
  (res.violations || []).forEach(v => { violationsMap[v.element] = v; });

  Object.entries(g.elements).forEach(([el, spec]) => {
    const c0 = appState.currentChemistry[el] ?? spec.target;
    const cFin = finalComp[el] ?? c0;
    const hasViolation = violationsMap[el] !== undefined;

    // Scale range for display [minDisplay, maxDisplay]
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

    const item = document.createElement("div");
    item.className = "corridor-item";
    item.innerHTML = `
      <div class="corridor-header">
        <div>
          <b>${el}</b> <span style="color:var(--text-muted); font-size:10.5px;">[Min: ${spec.min}% | Max: ${spec.max}%]</span>
        </div>
        <div>
          <span style="color:#0284c7;">${c0.toFixed(3)}%</span> &rarr;
          <b style="color:${hasViolation ? '#dc2626' : '#16a34a'};">${cFin.toFixed(3)}%</b>
        </div>
      </div>
      <div class="corridor-track-wrap">
        <div class="corridor-spec-window" style="left:${leftWindow}%; width:${widthWindow}%;"></div>
        <div class="corridor-target-line" style="left:${targetPos}%;"></div>
        <div class="corridor-marker initial" style="left:${c0Pos}%;" title="Initial: ${c0}%"></div>
        <div class="corridor-marker final ${hasViolation ? 'violation' : ''}" style="left:${cFinPos}%;" title="Final: ${cFin}%"></div>
      </div>
    `;
    container.appendChild(item);
  });
}

// 10. VERIFICATION & HEAT LOGGING WORKFLOW
function updateApprovalStatusUI() {
  const chip = document.getElementById("verify-status-chip");
  const sel = document.getElementById("approval-status-select");
  const reasonBlock = document.getElementById("override-reason-block");
  const overrideBadge = document.getElementById("override-indicator-badge");

  if (sel) sel.value = appState.approvalStatus;

  if (chip) {
    chip.className = `status-pill ${appState.approvalStatus.toLowerCase().replace('_', '-')}`;
    chip.textContent = appState.approvalStatus.replace('_', ' ');
  }

  const isOverridden = appState.approvalStatus === "OVERRIDDEN" || appState.isOverridden;
  if (reasonBlock) reasonBlock.style.display = isOverridden ? "block" : "none";
  if (overrideBadge) overrideBadge.style.display = isOverridden ? "inline-block" : "none";

  updateTelemetryHeader();
}

function updateTelemetryHeader() {
  const heatNum = document.getElementById("telemetry-heat-num");
  const gradeName = document.getElementById("telemetry-grade-name");
  const statusPill = document.getElementById("telemetry-status-pill");
  const heatBadge = document.getElementById("heat-id-badge");

  if (heatNum) heatNum.textContent = appState.activeHeatNumber;
  if (heatBadge) heatBadge.textContent = `HEAT #${appState.activeHeatNumber}`;

  const g = appState.grades[appState.selectedGradeId];
  if (gradeName && g) gradeName.textContent = g.name.split('(')[0].trim();

  if (statusPill) {
    statusPill.className = `status-pill ${appState.approvalStatus.toLowerCase().replace('_', '-')}`;
    statusPill.textContent = appState.approvalStatus.replace('_', ' ');
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
      alert("Override Justification is mandatory when approving an overridden plan.");
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
        feedback.textContent = `✓ Logged ${appState.activeHeatNumber} to digital audit database`;
      }
      alert(`Heat #${appState.activeHeatNumber} verified & recorded in SQLite digital audit trail!`);
      await fetchNextHeatNumber();
    }
  } catch (e) {
    alert("Error logging heat: " + e.message);
  }
}

function exportCurrentPDF() {
  if (!appState.lastSavedHeatId) {
    alert("Please approve/save the heat first to record it in the official audit trail, then export.");
    return;
  }
  window.open(`/api/heats/${appState.lastSavedHeatId}/export?format=pdf`, "_blank");
}

function exportCurrentCSV() {
  if (!appState.lastSavedHeatId) {
    alert("Please approve/save the heat first to record it in the official audit trail, then export.");
    return;
  }
  window.open(`/api/heats/${appState.lastSavedHeatId}/export?format=csv`, "_blank");
}

// 11. TRACEABILITY & EXPLAINABILITY
function renderTraceability(res) {
  const container = document.getElementById("explanations-container");
  const dualsContainer = document.getElementById("binding-constraints-container");
  if (!container || !dualsContainer) return;

  container.innerHTML = "";
  dualsContainer.innerHTML = "";

  (res.explanations || []).forEach(exp => {
    const item = document.createElement("div");
    item.style.padding = "8px 12px";
    item.style.background = "#ffffff";
    item.style.border = "1px solid var(--border-subtle)";
    item.style.borderRadius = "6px";
    item.style.fontSize = "11.5px";
    item.innerHTML = `<b>${exp.alloy_name}:</b> ${exp.rationale}`;
    container.appendChild(item);
  });

  (res.binding_constraints || []).forEach(bc => {
    const shadowPrice = appState.currency === "INR" ? `₹${bc.shadow_price_inr}/kg` : `$${bc.shadow_price_usd}/kg`;
    const box = document.createElement("div");
    box.style.padding = "8px 10px";
    box.style.background = "#ffffff";
    box.style.border = "1px solid var(--border-subtle)";
    box.style.borderRadius = "6px";
    box.innerHTML = `
      <div style="font-weight:700; color:var(--text-primary);">${bc.element} (${bc.type.toUpperCase()})</div>
      <div style="color:#ea580c; font-weight:800; font-family:var(--font-mono); font-size:12px;">${shadowPrice}</div>
      <div style="color:var(--text-muted); font-size:10px; margin-top:2px;">${bc.description}</div>
    `;
    dualsContainer.appendChild(box);
  });
}

// 12. WHAT-IF ECONOMICS & HEURISTIC COMPARISON (Fair comparison, no fake numbers)
function renderWhatIf(whatIfRes) {
  const container = document.getElementById("roi-benchmark-content");
  if (!container) return;

  const comp = whatIfRes.comparison || {};
  const isNaiveValid = comp.naive_is_in_spec !== false;

  let roiHtml = "";
  if (!isNaiveValid) {
    roiHtml = `
      <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:6px; padding:12px; color:#b91c1c; font-size:12px;">
        <b>Traditional Spreadsheet Rule-of-Thumb Failed:</b><br/>
        Manual single-alloy calculation produced an <b>OUT OF SPEC</b> melt.
        ${comp.naive_out_of_spec_reason || "Target chemistry ceiling was violated due to cross-contamination."}
        <br/><span style="color:#15803d; font-weight:700; margin-top:4px; display:inline-block;">VULCAN LP prevents scrap heats and guarantees 100% metallurgical corridor integrity.</span>
      </div>
    `;
  } else {
    const savingsINR = comp.cost_savings_inr || 0;
    const savingsPct = comp.cost_savings_pct || 0;
    const annualLakhs = comp.annual_savings_lakhs ?? 0;

    roiHtml = `
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
        <div style="background:#ffffff; border:1px solid var(--border-subtle); padding:10px; border-radius:6px;">
          <div style="font-size:10.5px; font-family:var(--font-mono); color:var(--text-muted);">PER-HEAT SAVINGS</div>
          <div style="font-size:18px; font-weight:800; color:#15803d; font-family:var(--font-mono);">₹${Math.round(savingsINR).toLocaleString('en-IN')}</div>
          <div style="font-size:10.5px; color:var(--text-muted);">${savingsPct.toFixed(1)}% Cost Reduction</div>
        </div>
        ${annualLakhs > 0 ? `
        <div style="background:#ffffff; border:1px solid var(--border-subtle); padding:10px; border-radius:6px;">
          <div style="font-size:10.5px; font-family:var(--font-mono); color:var(--text-muted);">ANNUAL FOUNDRY VALUE</div>
          <div style="font-size:18px; font-weight:800; color:#ea580c; font-family:var(--font-mono);">₹${annualLakhs.toFixed(1)} Lakhs</div>
          <div style="font-size:10.5px; color:var(--text-muted);">At ${comp.heats_per_day || 12} heats/day × ${comp.working_days_per_year || 300} days</div>
        </div>` : ''}
      </div>
    `;
  }

  container.innerHTML = roiHtml;
}

// 13. ACCORDIONS
function setupAccordions() {
  const traceToggle = document.getElementById("traceability-toggle");
  const traceContent = document.getElementById("traceability-content");
  traceToggle?.addEventListener("click", () => {
    const isHidden = traceContent.style.display === "none";
    traceContent.style.display = isHidden ? "block" : "none";
  });

  const whatifToggle = document.getElementById("whatif-toggle");
  const whatifContent = document.getElementById("whatif-content");
  whatifToggle?.addEventListener("click", () => {
    const isHidden = whatifContent.style.display === "none";
    whatifContent.style.display = isHidden ? "block" : "none";
  });
}

// 14. MODALS & POPUPS
function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.style.display = "none";
}

function openSlipModal() {
  const el = document.getElementById("addition-slip-modal");
  const content = document.getElementById("addition-slip-content");
  if (!el || !content) return;

  const res = appState.lastOptimizationResult;
  if (!res) {
    alert("Please calculate alloy additions first.");
    return;
  }

  const g = appState.grades[appState.selectedGradeId];
  const recs = res.recommendations || [];

  content.innerHTML = `
    <div style="text-align:center; border-bottom:2px solid #000; padding-bottom:8px; margin-bottom:12px;">
      <h2 style="font-size:16px; font-weight:800; margin:0;">SAKTHI FOUNDRIES - MELT DISPATCH TICKET</h2>
      <div style="font-size:11px;">HEAT #${appState.activeHeatNumber} &bull; ${new Date().toLocaleString()}</div>
    </div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-bottom:12px;">
      <div><b>Target Grade:</b> ${g?.name || appState.selectedGradeId}</div>
      <div><b>Base Melt Weight:</b> ${appState.meltWeight} kg</div>
      <div><b>Mode:</b> ${appState.mode === 'target' ? 'Target Midpoint' : 'Lean Spec (Cost Min)'}</div>
      <div><b>Melter / Supervisor:</b> ${appState.operatorName}</div>
    </div>
    <div style="font-weight:700; margin-bottom:4px; text-transform:uppercase;">Alloy Charging Sequence:</div>
    <table style="width:100%; border-collapse:collapse; margin-bottom:12px;">
      <thead>
        <tr style="border-bottom:1px solid #000; font-size:11px; text-align:left;">
          <th>Seq</th><th>Alloy Name</th><th>Weight</th><th>Packaging</th>
        </tr>
      </thead>
      <tbody>
        ${recs.map((r, i) => `
          <tr style="border-bottom:1px solid #ddd; font-size:11.5px;">
            <td>${i+1}</td>
            <td><b>${r.short_name || r.name}</b></td>
            <td>${(appState.manualOverrides[r.alloy_id] ?? r.quantity_kg).toFixed(2)} kg</td>
            <td>${r.full_bags > 0 ? `${r.full_bags} sacks (${r.bag_size_kg}kg) + ${r.loose_kg.toFixed(1)}kg trim` : `${r.loose_kg.toFixed(1)}kg trim`}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:24px; border-top:1px dashed #666; padding-top:12px;">
      <div>Melter Signature: __________________</div>
      <div>Chief Metallurgist: __________________</div>
    </div>
  `;

  el.style.display = "flex";
}

// ALLOY INVENTORY MODAL
async function openAlloyModal() {
  const modal = document.getElementById("alloy-modal");
  const body = document.getElementById("alloy-modal-body");
  if (!modal || !body) return;

  body.innerHTML = "Loading alloy parameters...";
  modal.style.display = "flex";

  try {
    const res = await fetch("/api/alloys").then(r => r.json());
    appState.alloys = res.alloys || [];

    let html = `
      <table class="charging-table" style="font-size:12px;">
        <thead>
          <tr>
            <th>Alloy</th>
            <th>Primary Recoveries</th>
            <th>Cost (₹/kg)</th>
            <th>Cost ($/kg)</th>
            <th>Bag Size</th>
          </tr>
        </thead>
        <tbody>
    `;

    appState.alloys.forEach(a => {
      const recEntries = Object.entries(a.recovery || {}).map(([el, r]) => `${el}: ${(r * 100).toFixed(0)}%`).join(", ");
      html += `
        <tr>
          <td><b>${a.short_name || a.name}</b></td>
          <td><input type="text" class="form-input" style="padding:3px 6px; font-size:11px;" value="${recEntries}" data-alloy-rec="${a.id}"></td>
          <td><input type="number" step="1" class="form-input" style="width:80px; padding:3px 6px; font-size:11px;" value="${a.cost_inr_per_kg || Math.round(a.cost_per_kg * 84)}" data-alloy-inr="${a.id}"></td>
          <td><input type="number" step="0.05" class="form-input" style="width:75px; padding:3px 6px; font-size:11px;" value="${a.cost_per_kg}" data-alloy-usd="${a.id}"></td>
          <td><input type="number" step="5" class="form-input" style="width:65px; padding:3px 6px; font-size:11px;" value="${a.bag_size_kg || 25}" data-alloy-bag="${a.id}"></td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    body.innerHTML = html;
  } catch (e) {
    body.innerHTML = "Error loading alloys: " + e.message;
  }
}

async function handleResetAlloys() {
  if (!confirm("Reset all alloy recoveries, compositions, and prices to factory standard catalog defaults?")) return;
  try {
    await fetch("/api/alloys/reset", { method: "POST" });
    await loadCatalogData();
    openAlloyModal();
    triggerOptimize();
  } catch (e) {
    alert("Error resetting alloys: " + e.message);
  }
}

// GRADE RECIPES MODAL
async function openGradeModal() {
  const modal = document.getElementById("grade-modal");
  const body = document.getElementById("grade-modal-body");
  if (!modal || !body) return;

  body.innerHTML = "Loading grade recipes...";
  modal.style.display = "flex";

  try {
    const res = await fetch("/api/grades").then(r => r.json());
    const grades = res.grades || [];

    let html = `
      <div style="display:flex; flex-direction:column; gap:16px;">
    `;

    grades.forEach(g => {
      const elemCorridors = Object.entries(g.elements || {}).map(([el, spec]) => `
        <span style="font-family:var(--font-mono); font-size:11px; background:#f1f5f9; padding:2px 6px; border-radius:4px;">
          <b>${el}</b>: ${spec.min} - ${spec.target} - ${spec.max}%
        </span>
      `).join(" ");

      html += `
        <div style="border:1px solid var(--border-subtle); border-radius:6px; padding:12px; background:#ffffff;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
            <div>
              <b>${g.name}</b> <span class="status-pill calculated" style="font-size:10px;">${g.category}</span>
            </div>
            <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">
              Default Weight: ${g.default_weight_kg || 4000} kg
            </div>
          </div>
          <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:8px;">${g.description || ''}</div>
          <div style="display:flex; flex-wrap:wrap; gap:6px;">${elemCorridors}</div>
        </div>
      `;
    });

    html += `</div>`;
    body.innerHTML = html;
  } catch (e) {
    body.innerHTML = "Error loading grades: " + e.message;
  }
}

async function handleResetGrades() {
  if (!confirm("Reset all grade recipes to factory standards?")) return;
  try {
    await fetch("/api/grades/reset", { method: "POST" });
    await loadCatalogData();
    openGradeModal();
    selectGrade(appState.selectedGradeId);
  } catch (e) {
    alert("Error resetting grades: " + e.message);
  }
}

// DIGITAL HEAT AUDIT TRAIL MODAL
async function openHeatLogModal() {
  const modal = document.getElementById("heat-log-modal");
  const container = document.getElementById("heat-log-table-container");
  const searchInput = document.getElementById("heat-search-input");
  if (!modal || !container) return;

  container.innerHTML = "Loading heat audit records...";
  modal.style.display = "flex";

  async function fetchAndRenderHeats(query = "") {
    try {
      const url = query ? `/api/heats?search=${encodeURIComponent(query)}` : `/api/heats`;
      const res = await fetch(url).then(r => r.json());
      const heats = res.heats || [];

      if (heats.length === 0) {
        container.innerHTML = `<div style="text-align:center; padding:24px; color:var(--text-muted);">No recorded heats found.</div>`;
        return;
      }

      let html = `
        <table class="charging-table">
          <thead>
            <tr>
              <th>Heat #</th>
              <th>Date & Time</th>
              <th>Grade</th>
              <th>Weight</th>
              <th>Cost (₹)</th>
              <th>Status</th>
              <th>Operator</th>
              <th>Export</th>
            </tr>
          </thead>
          <tbody>
      `;

      heats.forEach(h => {
        const timeStr = (h.created_at || "").substring(0, 16).replace('T', ' ');
        html += `
          <tr>
            <td><b>${h.heat_number}</b></td>
            <td style="font-family:var(--font-mono); font-size:11px;">${timeStr}</td>
            <td>${h.grade_name || h.grade_id}</td>
            <td style="font-family:var(--font-mono);">${h.melt_weight_kg} kg</td>
            <td style="font-family:var(--font-mono); font-weight:700;">₹${Math.round(h.total_cost_inr || 0).toLocaleString('en-IN')}</td>
            <td><span class="status-pill ${(h.status || 'CALCULATED').toLowerCase().replace('_', '-')}">${h.status}</span></td>
            <td>${h.operator_name || 'Unassigned'}</td>
            <td>
              <div style="display:flex; gap:4px;">
                <a href="/api/heats/${h.id}/export?format=pdf" target="_blank" class="btn btn-secondary" style="padding:2px 6px; font-size:10px;">PDF</a>
                <a href="/api/heats/${h.id}/export?format=csv" target="_blank" class="btn btn-secondary" style="padding:2px 6px; font-size:10px;">CSV</a>
              </div>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
    } catch (e) {
      container.innerHTML = "Error loading heat log: " + e.message;
    }
  }

  fetchAndRenderHeats();
  if (searchInput) {
    searchInput.oninput = (e) => {
      fetchAndRenderHeats(e.target.value.trim());
    };
  }
}
