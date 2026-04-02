"""Generate review PDF for NOT DONE scripts: EN + RU + P1 + P2, grouped by creator."""
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
try:
    pdfmetrics.registerFont(TTFont('ArialUni', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    FONT = 'ArialUni'
    FONT_BOLD = 'ArialUni'
except:
    pass


def main():
    with open('/tmp/not_done_clickbait.json') as f:
        data = json.load(f)

    output_path = "/Users/levavdosin/Desktop/viral_not_done_review.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=10*mm, bottomMargin=10*mm,
    )

    cell = ParagraphStyle('Cell', fontName=FONT, fontSize=7, leading=9)
    cell_bold = ParagraphStyle('CellB', fontName=FONT_BOLD, fontSize=7.5, leading=10)
    title = ParagraphStyle('T', fontName=FONT_BOLD, fontSize=16, spaceAfter=4)
    sub = ParagraphStyle('S', fontName=FONT, fontSize=9, textColor=colors.grey)
    section = ParagraphStyle('Sec', fontName=FONT_BOLD, fontSize=13, spaceBefore=8, spaceAfter=4)

    elements = []

    total = sum(len(v) for v in data.values())
    elements.append(Paragraph("Viral Scripts — Not Done (Review)", title))
    elements.append(Paragraph(f"{total} scripts across 6 creators | EN + RU + P1 + P2", sub))
    elements.append(Spacer(1, 4*mm))

    # Summary
    sum_data = [[
        Paragraph("Creator", cell_bold),
        Paragraph("Not Done", cell_bold),
        Paragraph("Need P1", cell_bold),
        Paragraph("Need P2", cell_bold),
        Paragraph("Ready", cell_bold),
        Paragraph("NEW", cell_bold),
    ]]
    for speaker in ['boris', 'daniel', 'luna', 'natalie', 'thomas', 'zoe']:
        scripts = data.get(speaker, [])
        np1 = sum(1 for s in scripts if 'P1' in s.get('hf_status', ''))
        np2 = sum(1 for s in scripts if 'P2' in s.get('hf_status', ''))
        ready = sum(1 for s in scripts if s.get('hf_status', '').startswith('Ready'))
        new = sum(1 for s in scripts if s.get('hf_status', '') == 'NEW')
        pending = sum(1 for s in scripts if s.get('hf_status', '') == 'Pending')
        sum_data.append([
            Paragraph(speaker.capitalize(), cell),
            str(len(scripts)),
            str(np1), str(np2), str(ready + pending), str(new),
        ])

    st = Table(sum_data, colWidths=[70, 55, 55, 55, 55, 40])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(st)
    elements.append(PageBreak())

    # Per-creator detail
    status_colors = {
        'Need P1': '#ef4444',
        'Need P2': '#f59e0b',
        'Ready P1': '#3b82f6',
        'Ready P2': '#3b82f6',
        'Ready': '#3b82f6',
        'Pending': '#6b7280',
        'NEW': '#8b5cf6',
    }

    for speaker in ['boris', 'daniel', 'luna', 'natalie', 'thomas', 'zoe']:
        scripts = data.get(speaker, [])
        if not scripts:
            continue

        elements.append(Paragraph(f"{speaker.upper()} — {len(scripts)} scripts not done", section))

        header = [
            Paragraph("ID", cell_bold),
            Paragraph("Status", cell_bold),
            Paragraph("EN", cell_bold),
            Paragraph("RU", cell_bold),
            Paragraph("P1", cell_bold),
            Paragraph("P2", cell_bold),
        ]
        rows = [header]

        for s in scripts:
            en = (s.get('text_en') or '').replace('&', '&amp;').replace('<', '&lt;')
            ru = (s.get('text_ru') or '').replace('&', '&amp;').replace('<', '&lt;')
            p1 = (s.get('p1') or '').replace('&', '&amp;').replace('<', '&lt;')
            p2 = (s.get('p2') or '').replace('&', '&amp;').replace('<', '&lt;')
            hf = s.get('hf_status', '')

            rows.append([
                str(s['id']),
                Paragraph(hf, cell),
                Paragraph(en, cell),
                Paragraph(ru, cell),
                Paragraph(p1, cell),
                Paragraph(p2, cell),
            ])

        col_widths = [25, 50, 195, 195, 145, 145]
        t = Table(rows, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]
        t.setStyle(TableStyle(style_cmds))
        elements.append(t)
        elements.append(PageBreak())

    doc.build(elements)
    print(f"PDF saved to {output_path}")


if __name__ == "__main__":
    main()
