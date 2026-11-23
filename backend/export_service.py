"""
export_service.py - CSV and PDF Export Engine for Vulcan / Sakthi Melt-OS
Generates official foundry melt certificates, charging dispatch tickets, and audit records.
Uses ReportLab for high-fidelity vector PDF generation.
"""

import io
import csv
from typing import Dict, Any
from datetime import datetime

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def export_heat_csv(heat: Dict[str, Any]) -> str:
    """Generates standard CSV representation of a heat record."""
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Heat Header
    writer.writerow(["SAKTHI MELT-OS FOUNDRY AUTOMATION SYSTEM"])
    writer.writerow(["HEAT METALLURGICAL RECORD & CHARGING DISPATCH"])
    writer.writerow([])
    writer.writerow(["Heat Number", heat.get("heat_number")])
    writer.writerow(["Date & Time", heat.get("created_at")])
    writer.writerow(["Target Grade", heat.get("grade_name")])
    writer.writerow(["Base Melt Weight (kg)", heat.get("melt_weight_kg")])
    writer.writerow(["Optimization Mode", heat.get("mode")])
    writer.writerow(["Approval Status", heat.get("status")])
    writer.writerow(["Melter / Operator", heat.get("operator_name") or "Unassigned"])
    if heat.get("override_reason"):
        writer.writerow(["Override Justification", heat.get("override_reason")])
    writer.writerow([])

    # 2. Spectrometer vs Target vs Predicted Chemistry
    writer.writerow(["--- CHEMICAL ANALYSIS & CORRIDOR INTEGRITY ---"])
    writer.writerow(["Element", "Spectrometer Initial (%)", "Predicted Final (%)", "Status"])
    input_chem = heat.get("input_chemistry") or {}
    final_chem = heat.get("final_chemistry") or {}
    all_elements = sorted(list(set(list(input_chem.keys()) + list(final_chem.keys()))))
    for el in all_elements:
        c0 = input_chem.get(el, 0.0)
        c_fin = final_chem.get(el, 0.0)
        writer.writerow([el, f"{c0:.4f}", f"{c_fin:.4f}", "OK"])
    writer.writerow([])

    # 3. Recommended Alloy Additions
    writer.writerow(["--- ALLOY ADDITION DISPATCH INSTRUCTIONS ---"])
    writer.writerow(["Order", "Alloy Name", "Weight (kg)", "Sacks", "Trim (kg)", "Cost (INR)", "Cost (USD)"])
    recs = heat.get("actual_additions") or heat.get("recommendations") or []
    total_kg = 0.0
    total_inr = 0.0
    for idx, r in enumerate(recs, 1):
        kg = r.get("weight_kg", 0.0)
        total_kg += kg
        cost_inr = r.get("cost_inr", 0.0)
        total_inr += cost_inr
        cost_usd = r.get("cost_usd", 0.0)
        sacks = r.get("sacks", 0)
        trim = r.get("trim_kg", 0.0)
        writer.writerow([
            idx,
            r.get("short_name") or r.get("name"),
            f"{kg:.2f}",
            sacks,
            f"{trim:.2f}",
            f"{cost_inr:.2f}",
            f"{cost_usd:.2f}"
        ])
    writer.writerow(["TOTAL", "", f"{total_kg:.2f}", "", "", f"{total_inr:.2f}", f"{heat.get('total_cost_usd', 0.0):.2f}"])

    # 4. Append-Only Audit Trail & Verification Events
    writer.writerow([])
    writer.writerow(["--- APPEND-ONLY AUDIT TRAIL & LIFECYCLE EVENTS ---"])
    writer.writerow(["Timestamp", "Actor", "Old Status", "New Status", "Reason / Notes", "Snapshot Hash"])
    events = heat.get("events")
    if events is None and heat.get("id"):
        try:
            from backend.storage import get_heat_events
            events = get_heat_events(heat["id"])
        except Exception:
            events = []
    for ev in (events or []):
        writer.writerow([
            ev.get("timestamp", ""),
            ev.get("actor", ""),
            ev.get("old_status", "—") or "—",
            ev.get("new_status", ""),
            ev.get("reason", "") or "—",
            ev.get("snapshot_hash", "") or "—"
        ])

    return output.getvalue()


def export_heat_pdf(heat: Dict[str, Any]) -> bytes:
    """Generates official foundry melt ticket PDF with ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom industrial styles
    primary_color = colors.HexColor("#0f172a") # Dark Slate Navy
    accent_color = colors.HexColor("#ea580c")  # Foundry Orange
    border_color = colors.HexColor("#cbd5e1")  # Slate Border
    header_bg = colors.HexColor("#f8fafc")     # Light Slate Background

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b")
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceAfter=4
    )
    cell_style = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=primary_color
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=primary_color
    )
    cell_right = ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=primary_color
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=primary_color
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>VULCAN // SAKTHI MELT-OS</b>", title_style),
            Paragraph(f"<b>OFFICIAL MELT SHEET</b><br/><font color='#ea580c'>HEAT #{heat.get('heat_number')}</font>", ParagraphStyle("RightH", parent=title_style, alignment=2, fontSize=14, leading=17))
        ],
        [
            Paragraph("Industrial Foundry Decision Support & Automated Spectrometer Correction", subtitle_style),
            Paragraph(f"Logged: {heat.get('created_at')[:19].replace('T', ' ')}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[3.8 * inch, 3.4 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=8))

    # 2. Heat Operational Metadata
    status_label = heat.get("status", "CALCULATED")
    meta_data = [
        [
            Paragraph("<b>Target Grade:</b>", cell_bold),
            Paragraph(str(heat.get("grade_name")), cell_style),
            Paragraph("<b>Heat Number:</b>", cell_bold),
            Paragraph(str(heat.get("heat_number")), cell_style),
        ],
        [
            Paragraph("<b>Furnace Melt Weight:</b>", cell_bold),
            Paragraph(f"{float(heat.get('melt_weight_kg', 0)):,.0f} kg", cell_style),
            Paragraph("<b>Status:</b>", cell_bold),
            Paragraph(f"<b>{status_label}</b>", cell_style),
        ],
        [
            Paragraph("<b>Optimization Mode:</b>", cell_bold),
            Paragraph("Target Midpoint" if heat.get("mode") == "target" else "Lean Cost (Lower Bound)", cell_style),
            Paragraph("<b>Melter / Operator:</b>", cell_bold),
            Paragraph(str(heat.get("operator_name") or "Unassigned"), cell_style),
        ],
    ]
    if heat.get("override_reason"):
        meta_data.append([
            Paragraph("<b>Override Reason:</b>", cell_bold),
            Paragraph(str(heat.get("override_reason")), ParagraphStyle("Reason", parent=cell_style, textColor=colors.HexColor("#b91c1c"))),
            Paragraph("", cell_style),
            Paragraph("", cell_style)
        ])

    meta_table = Table(meta_data, colWidths=[1.6 * inch, 2.0 * inch, 1.6 * inch, 2.0 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), header_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Chemical Analysis Corridor Table
    story.append(Paragraph("SPECTROMETER COMPOSITION & CORRIDOR INTEGRITY", section_style))
    chem_headers = ["Element", "Base Reading (%)", "Predicted Final (%)", "Net Change (%)", "Status"]
    chem_rows = [[Paragraph(f"<b>{h}</b>", cell_bold if i < 3 else cell_right_bold) for i, h in enumerate(chem_headers)]]

    input_chem = heat.get("input_chemistry") or {}
    final_chem = heat.get("final_chemistry") or {}
    elements = sorted(list(set(list(input_chem.keys()) + list(final_chem.keys()))))

    for el in elements:
        c0 = input_chem.get(el, 0.0)
        c_fin = final_chem.get(el, 0.0)
        delta = c_fin - c0
        status_text = "<font color='#16a34a'><b>IN SPEC</b></font>"
        # Check violations
        violations = heat.get("violations") or []
        for v in violations:
            if v and v.get("element") == el:
                status_text = f"<font color='#dc2626'><b>{v.get('side', '').upper()}</b></font>"

        delta_sign = "+" if delta >= 0 else ""
        chem_rows.append([
            Paragraph(f"<b>{el}</b>", cell_bold),
            Paragraph(f"{c0:.4f}%", cell_style),
            Paragraph(f"{c_fin:.4f}%", cell_style),
            Paragraph(f"{delta_sign}{delta:.4f}%", cell_right),
            Paragraph(status_text, cell_right)
        ])

    chem_table = Table(chem_rows, colWidths=[1.2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    chem_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(chem_table)
    story.append(Spacer(1, 12))

    # 4. Corrective Ferroalloy Charging Table
    story.append(Paragraph("RECOMMENDED FERROALLOY CHARGING INSTRUCTIONS", section_style))
    alloy_headers = ["Seq", "Alloy Specification", "Addition (kg)", "Packaging Dispatch", "Cost (INR)", "Cost (USD)"]
    alloy_rows = [[Paragraph(f"<b>{h}</b>", cell_bold if i < 2 else cell_right_bold) for i, h in enumerate(alloy_headers)]]

    recs = heat.get("actual_additions") or heat.get("recommendations") or []
    tot_kg = 0.0
    tot_inr = 0.0
    tot_usd = 0.0

    for idx, r in enumerate(recs, 1):
        kg = float(r.get("weight_kg", 0.0))
        tot_kg += kg
        inr = float(r.get("cost_inr", 0.0))
        tot_inr += inr
        usd = float(r.get("cost_usd", 0.0))
        tot_usd += usd

        sacks = r.get("sacks", 0)
        bag_size = r.get("bag_size_kg", 25.0)
        trim = r.get("trim_kg", 0.0)
        pack_text = f"{sacks} sacks ({bag_size}kg) + {trim:.2f}kg trim" if sacks > 0 else f"{trim:.2f}kg trim"

        alloy_rows.append([
            Paragraph(str(idx), cell_style),
            Paragraph(f"<b>{r.get('short_name') or r.get('name')}</b>", cell_style),
            Paragraph(f"{kg:.2f} kg", cell_right_bold),
            Paragraph(pack_text, cell_style),
            Paragraph(f"₹{inr:,.2f}", cell_right),
            Paragraph(f"${usd:,.2f}", cell_right),
        ])

    # Totals row
    alloy_rows.append([
        Paragraph("", cell_bold),
        Paragraph("<b>NET CHARGE TOTAL</b>", cell_bold),
        Paragraph(f"<b>{tot_kg:.2f} kg</b>", cell_right_bold),
        Paragraph("", cell_style),
        Paragraph(f"<b>₹{tot_inr:,.2f}</b>", cell_right_bold),
        Paragraph(f"<b>${tot_usd:,.2f}</b>", cell_right_bold),
    ])

    alloy_table = Table(alloy_rows, colWidths=[0.5 * inch, 2.3 * inch, 1.1 * inch, 1.7 * inch, 0.9 * inch, 0.7 * inch])
    alloy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(alloy_table)
    story.append(Spacer(1, 16))

    # 5. Sign-Off & Verification Block
    story.append(Paragraph("FOUNDRY QUALITY ASSURANCE & VERIFICATION SIGN-OFF", section_style))
    sign_data = [
        [
            Paragraph("<b>Melting Supervisor / Furnace Operator:</b>", cell_bold),
            Paragraph("<b>Chief Metallurgist / QA Manager:</b>", cell_bold),
        ],
        [
            Paragraph("<br/><br/>Signature: __________________________<br/>Name: " + str(heat.get("operator_name") or "") + "<br/>Date: " + datetime.now().strftime("%Y-%m-%d"), cell_style),
            Paragraph("<br/><br/>Signature: __________________________<br/>Name: __________________________<br/>Date: " + datetime.now().strftime("%Y-%m-%d"), cell_style)
        ]
    ]
    sign_table = Table(sign_data, colWidths=[3.6 * inch, 3.6 * inch])
    sign_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), header_bg)
    ]))
    story.append(KeepTogether([sign_table]))

    # 6. Append-Only Audit Trail Table
    events = heat.get("events")
    if events is None and heat.get("id"):
        try:
            from backend.storage import get_heat_events
            events = get_heat_events(heat["id"])
        except Exception:
            events = []
    if events:
        story.append(Spacer(1, 14))
        story.append(Paragraph("DIGITAL AUDIT TRAIL & LIFECYCLE EVENT HISTORY", section_style))
        event_headers = ["Timestamp", "Actor", "Transition", "Justification / Notes", "Hash"]
        event_rows = [[Paragraph(f"<b>{h}</b>", cell_bold) for h in event_headers]]
        for ev in events:
            old_s = ev.get("old_status") or "START"
            new_s = ev.get("new_status") or ""
            trans = f"{old_s} &rarr; {new_s}"
            event_rows.append([
                Paragraph(str(ev.get("timestamp", ""))[:19].replace("T", " "), cell_style),
                Paragraph(str(ev.get("actor", "System")), cell_style),
                Paragraph(trans, cell_style),
                Paragraph(str(ev.get("reason") or "—"), cell_style),
                Paragraph(str(ev.get("snapshot_hash") or "—"), cell_style),
            ])
        ev_table = Table(event_rows, colWidths=[1.3 * inch, 1.2 * inch, 1.6 * inch, 2.2 * inch, 0.9 * inch])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 1, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(KeepTogether([ev_table]))

    doc.build(story)
    return buffer.getvalue()
