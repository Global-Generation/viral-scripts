"""Generate review PDF for top 30 viral scripts: EN + RU + P1 + P2."""
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Cyrillic font
FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
try:
    pdfmetrics.registerFont(TTFont('ArialUni', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    FONT = 'ArialUni'
    FONT_BOLD = 'ArialUni'
except:
    pass


def main():
    with open('/tmp/top30_review.json') as f:
        data = json.load(f)

    output_path = "/Users/levavdosin/Desktop/viral_top30_review.pdf"

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

    elements = []
    elements.append(Paragraph("Top 30 Viral Scripts — Review", title))
    elements.append(Paragraph(f"Best unassigned scripts (score 42-72, 0 issues) | EN + RU + P1 + P2", sub))
    elements.append(Spacer(1, 6*mm))

    # Table
    header = [
        Paragraph("#", cell_bold),
        Paragraph("ID", cell_bold),
        Paragraph("Score", cell_bold),
        Paragraph("Cat", cell_bold),
        Paragraph("EN", cell_bold),
        Paragraph("RU", cell_bold),
        Paragraph("P1", cell_bold),
        Paragraph("P2", cell_bold),
    ]
    rows = [header]

    for i, d in enumerate(data):
        en_esc = (d['text'] or '').replace('&', '&amp;').replace('<', '&lt;')
        ru_esc = (d.get('ru_text') or '').replace('&', '&amp;').replace('<', '&lt;')
        p1_esc = (d.get('p1') or '').replace('&', '&amp;').replace('<', '&lt;')
        p2_esc = (d.get('p2') or '').replace('&', '&amp;').replace('<', '&lt;')

        rows.append([
            str(i + 1),
            str(d['id']),
            str(d['score']),
            d['category'][:6],
            Paragraph(en_esc, cell),
            Paragraph(ru_esc, cell),
            Paragraph(p1_esc, cell),
            Paragraph(p2_esc, cell),
        ])

    col_widths = [15, 25, 25, 30, 210, 210, 125, 125]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    doc.build(elements)
    print(f"PDF saved to {output_path}")


if __name__ == "__main__":
    main()
