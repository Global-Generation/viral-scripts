"""Generate a review PDF: Russian text + P1 + P2 for each creator's rewritten scripts."""
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register a font that supports Cyrillic
FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
for font_path, name, bold_name in [
    ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 'ArialUni', 'ArialUni'),
    ('/System/Library/Fonts/Supplemental/Arial Bold.ttf', None, 'ArialBold'),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'DejaVu', None),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', None, 'DejaVuBold'),
]:
    try:
        if name:
            pdfmetrics.registerFont(TTFont(name, font_path))
            FONT = name
        if bold_name and bold_name != name:
            pdfmetrics.registerFont(TTFont(bold_name, font_path))
            FONT_BOLD = bold_name
    except:
        pass
if FONT == 'ArialUni':
    FONT_BOLD = 'ArialUni'  # Arial Unicode has no separate bold


def main():
    with open('/tmp/rework_rewrites_ru.json') as f:
        data = json.load(f)

    output_path = "/Users/levavdosin/Desktop/viral_scripts_review_ru.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=18, spaceAfter=4, fontName=FONT_BOLD)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=colors.grey, fontName=FONT)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, spaceBefore=10, spaceAfter=4, fontName=FONT_BOLD)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7.5, leading=10, fontName=FONT)
    cell_bold = ParagraphStyle('CellBold', parent=cell_style, fontName=FONT_BOLD)
    rej_style = ParagraphStyle('Rej', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#dc2626'), fontName=FONT)

    elements = []

    creators = ['boris', 'daniel', 'luna', 'natalie', 'thomas', 'zoe']
    total_ok = sum(1 for d in data if d.get('ru_status') == 'ok')
    total_rej = sum(1 for d in data if d.get('ru_status') == 'rejected' or d['status'] == 'rejected')

    elements.append(Paragraph("Viral Scripts — Review (RU)", title_style))
    elements.append(Paragraph(f"{total_ok} scripts translated | {total_rej} rejected", subtitle_style))
    elements.append(Spacer(1, 6*mm))

    # Summary table
    sum_data = [[Paragraph("Creator", cell_bold), Paragraph("Translated", cell_bold), Paragraph("Rejected", cell_bold), Paragraph("Total", cell_bold)]]
    for cr in creators:
        ok_c = sum(1 for d in data if d['creator'] == cr and d.get('ru_status') == 'ok')
        rej_c = sum(1 for d in data if d['creator'] == cr and (d.get('ru_status') == 'rejected' or d['status'] == 'rejected'))
        sum_data.append([Paragraph(cr.capitalize(), cell_style), str(ok_c), str(rej_c), str(ok_c + rej_c)])

    st = Table(sum_data, colWidths=[80, 70, 70, 80])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(st)
    elements.append(PageBreak())

    # Detail per creator
    for cr in creators:
        ok_items = [d for d in data if d['creator'] == cr and d.get('ru_status') == 'ok']
        rej_items = [d for d in data if d['creator'] == cr and (d.get('ru_status') == 'rejected' or d['status'] == 'rejected')]

        elements.append(Paragraph(f"{cr.upper()} — {len(ok_items)} translated, {len(rej_items)} rejected", section_style))

        if ok_items:
            table_data = [[
                Paragraph("ID", cell_bold),
                Paragraph("Text (RU)", cell_bold),
                Paragraph("P1", cell_bold),
                Paragraph("P2", cell_bold),
            ]]
            for d in ok_items:
                ru_esc = (d.get('ru_text') or '').replace('&', '&amp;').replace('<', '&lt;')
                p1_esc = (d.get('p1') or '').replace('&', '&amp;').replace('<', '&lt;')
                p2_esc = (d.get('p2') or '').replace('&', '&amp;').replace('<', '&lt;')
                table_data.append([
                    str(d['id']),
                    Paragraph(ru_esc, cell_style),
                    Paragraph(p1_esc, cell_style),
                    Paragraph(p2_esc, cell_style),
                ])

            col_widths = [30, 310, 210, 210]
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 0), (2, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)

        if rej_items:
            elements.append(Spacer(1, 4*mm))
            rej_ids = [str(d['id']) for d in rej_items]
            elements.append(Paragraph(f"Rejected (will delete): IDs {', '.join(rej_ids)}", rej_style))

        elements.append(PageBreak())

    doc.build(elements)
    print(f"Review PDF saved to {output_path}")


if __name__ == "__main__":
    main()
