"""
Script Audit Tool — checks all scripts against platform rules.
Generates a landscape PDF report with PASS / REWORK / DELETE verdicts.
Run locally: python3 audit_scripts.py /tmp/viral_audit.db
"""
import re
import sqlite3
import sys
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
)

# ── Rules from services/rewriter.py ──

FORBIDDEN_PHRASES = [
    "literally", "insane", "crazy", "mind-blowing", "mind blowing",
    "game-changer", "game changer", "wake up", "you need to",
    "right now", "before it's too late", "most people don't know",
    "as you can see", "check this", "look at this",
    "comment", "dm me", "link in the description",
    "game changing", "jaw-dropping", "jaw dropping",
    "believe it or not", "you won't believe",
]

HYPE_WORDS = [
    "insane", "crazy", "mind-blowing", "game-changer", "incredible",
    "unbelievable", "amazing", "shocking", "terrifying", "devastating",
]

LISTICLE_PATTERN = re.compile(r'\b(\d+)\s+(things?|steps?|ways?|tips?|reasons?|secrets?|hacks?|tricks?|mistakes?)\b', re.I)
DIGIT_PATTERN = re.compile(r'\$[\d,]+|\b\d{2,}\b')  # $10,000 or numbers 10+
EXCLAMATION_PATTERN = re.compile(r'!')


def audit_script(script_id, text, assigned_to, category):
    """Check a single script against all rules. Returns (verdict, issues)."""
    issues = []

    if not text or not text.strip():
        return "DELETE", ["Empty script (no modified_text)"]

    words = text.split()
    wc = len(words)

    # Word count check
    if wc < 30:
        issues.append(f"Too short: {wc} words (min 30)")
    elif wc > 60:
        issues.append(f"Too long: {wc} words (max ~50)")
    elif wc > 50:
        issues.append(f"Slightly over: {wc} words (target 45-50)")

    # Forbidden phrases
    text_lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            issues.append(f'Forbidden: "{phrase}"')

    # Exclamation marks
    if EXCLAMATION_PATTERN.search(text):
        issues.append("Has exclamation mark(s)")

    # Digits (should be words)
    digits_found = DIGIT_PATTERN.findall(text)
    if digits_found:
        issues.append(f"Digits found: {', '.join(digits_found[:3])}")

    # Listicles
    listicle = LISTICLE_PATTERN.search(text)
    if listicle:
        issues.append(f'Listicle: "{listicle.group()}"')

    # Incomplete sentences (ends mid-thought)
    stripped = text.strip()
    if stripped and stripped[-1] not in '.!?"':
        issues.append("Doesn't end with punctuation")

    # Hook check: first sentence too generic
    first_sent = stripped.split('.')[0] if stripped else ""
    generic_openers = ["so", "hey", "hi", "hello", "today", "in this video", "let me tell you"]
    first_lower = first_sent.lower().strip()
    for opener in generic_openers:
        if first_lower.startswith(opener):
            issues.append(f'Weak hook: starts with "{opener}"')
            break

    # Verdict
    if not text.strip():
        verdict = "DELETE"
    elif len(issues) == 0:
        verdict = "PASS"
    elif any("Too short" in i or "Too long" in i for i in issues):
        if wc < 20 or wc > 80:
            verdict = "DELETE"
        else:
            verdict = "REWORK"
    elif len(issues) >= 3:
        verdict = "REWORK"
    elif len(issues) >= 1 and any("Forbidden" in i for i in issues):
        verdict = "REWORK"
    else:
        verdict = "PASS"

    return verdict, issues


def generate_pdf(results, output_path):
    """Generate landscape PDF audit report."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('AuditTitle', parent=styles['Title'], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle('AuditSub', parent=styles['Normal'], fontSize=10, textColor=colors.grey)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7, leading=9)
    cell_bold = ParagraphStyle('CellBold', parent=cell_style, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13, spaceBefore=12, spaceAfter=6)

    elements = []

    # ── Summary ──
    total = len(results)
    pass_count = sum(1 for r in results if r['verdict'] == 'PASS')
    rework_count = sum(1 for r in results if r['verdict'] == 'REWORK')
    delete_count = sum(1 for r in results if r['verdict'] == 'DELETE')

    elements.append(Paragraph("Viral Scripts — Full Audit Report", title_style))
    elements.append(Paragraph(f"Total: {total} scripts | PASS: {pass_count} | REWORK: {rework_count} | DELETE: {delete_count}", subtitle_style))
    elements.append(Spacer(1, 8*mm))

    # Summary by creator
    by_creator = defaultdict(lambda: {"PASS": 0, "REWORK": 0, "DELETE": 0, "total": 0})
    for r in results:
        c = r['creator'] or 'unassigned'
        by_creator[c][r['verdict']] += 1
        by_creator[c]['total'] += 1

    summary_data = [["Creator", "Total", "PASS", "REWORK", "DELETE"]]
    for c in sorted(by_creator.keys()):
        d = by_creator[c]
        summary_data.append([c.capitalize(), str(d['total']), str(d['PASS']), str(d['REWORK']), str(d['DELETE'])])

    summary_table = Table(summary_data, colWidths=[80, 50, 50, 60, 50])
    summary_table.setStyle(TableStyle([
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
    elements.append(summary_table)
    elements.append(PageBreak())

    # ── Detail tables by verdict ──
    for verdict in ["DELETE", "REWORK", "PASS"]:
        group = [r for r in results if r['verdict'] == verdict]
        if not group:
            continue

        color_map = {"DELETE": "#ef4444", "REWORK": "#f59e0b", "PASS": "#16a34a"}
        elements.append(Paragraph(f"{verdict} — {len(group)} scripts", section_style))

        table_data = [["ID", "Creator", "Cat", "Words", "Score", "Issues", "First 80 chars"]]
        for r in group:
            issues_text = "; ".join(r['issues'][:4]) if r['issues'] else "—"
            preview = (r['text'][:80] + "...") if r['text'] and len(r['text']) > 80 else (r['text'] or "—")
            table_data.append([
                str(r['id']),
                (r['creator'] or '—').capitalize(),
                r['category'] or '—',
                str(r['word_count']),
                str(r['score']),
                Paragraph(issues_text, cell_style),
                Paragraph(preview.replace('&', '&amp;').replace('<', '&lt;'), cell_style),
            ])

        col_widths = [30, 55, 40, 35, 35, 200, 350]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color_map[verdict])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (4, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(PageBreak())

    doc.build(elements)
    print(f"PDF saved to {output_path}")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/viral_audit.db"
    output_path = "/Users/levavdosin/Desktop/viral_scripts_audit.pdf"

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    cursor.execute("""
        SELECT s.id, s.assigned_to, s.modified_text, s.original_text,
               s.viral_score, s.character_type, s.production_status,
               v.title as video_title,
               sr.category
        FROM scripts s
        LEFT JOIN videos v ON s.video_id = v.id
        LEFT JOIN searches sr ON v.search_id = sr.id
        ORDER BY s.assigned_to, s.id
    """)

    results = []
    for row in cursor.fetchall():
        text = row['modified_text'] or row['original_text'] or ""
        verdict, issues = audit_script(row['id'], row['modified_text'], row['assigned_to'], row['category'])
        results.append({
            'id': row['id'],
            'creator': row['assigned_to'] or '',
            'category': row['category'] or '',
            'text': text,
            'word_count': len(text.split()) if text else 0,
            'score': row['viral_score'] or 0,
            'verdict': verdict,
            'issues': issues,
        })

    db.close()

    # Print summary
    pass_c = sum(1 for r in results if r['verdict'] == 'PASS')
    rework_c = sum(1 for r in results if r['verdict'] == 'REWORK')
    delete_c = sum(1 for r in results if r['verdict'] == 'DELETE')
    print(f"\nAudit complete: {len(results)} scripts")
    print(f"  PASS:   {pass_c}")
    print(f"  REWORK: {rework_c}")
    print(f"  DELETE: {delete_c}")

    generate_pdf(results, output_path)


if __name__ == "__main__":
    main()
