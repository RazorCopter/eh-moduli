"""
PDF Report Generator for EHModuli
Generates high-quality, professional PDF reports for form submissions and document receipts.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Pagina X di Y'
    along with running header and footer on all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer (on all pages)
        footer_y = 25
        page_text = f"Pagina {self._pageNumber} di {page_count}"
        self.drawRightString(A4[0] - 36, footer_y, page_text)

        footer_left = "Etichub S.r.l. · Spin-off Università di Pavia · Ricevuta di Ricezione Documenti"
        self.drawString(36, footer_y, footer_left)

        # Thin footer rule
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, footer_y + 12, A4[0] - 36, footer_y + 12)

        self.restoreState()


def format_file_size(bytes_val):
    if not bytes_val or bytes_val <= 0:
        return "—"
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1048576:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / 1048576:.2f} MB"


def generate_submission_pdf(output_pdf_path, form_data, customer_data, uploads, form_fields=None, logo_path=None):
    """
    Generates a premium-quality PDF report for a submitted form.

    :param output_pdf_path: Path where PDF will be saved
    :param form_data: dict with form metadata (id, name, project_name, submission_time, ip, etc.)
    :param customer_data: dict with customer info (name, code, email, phone, vat, etc.)
    :param uploads: list of upload records
    :param form_fields: list of submitted form field answers
    :param logo_path: optional path to SVG logo file
    """
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    content_width = A4[0] - 72  # 595.27 - 72 = 523.27 pt

    # Colors
    c_primary = colors.HexColor("#7F1718")      # Etichub Burgundy
    c_primary_light = colors.HexColor("#FDF2F1")
    c_dark = colors.HexColor("#1E293B")         # Main Text
    c_muted = colors.HexColor("#64748B")        # Subtitles/labels
    c_border = colors.HexColor("#E2E8F0")       # Borders
    c_success_bg = colors.HexColor("#ECFDF3")
    c_success_fg = colors.HexColor("#027A48")
    c_warn_bg = colors.HexColor("#FEF0C7")
    c_warn_fg = colors.HexColor("#B54708")

    # Typography & Styles
    base_styles = getSampleStyleSheet()

    s_title = ParagraphStyle(
        'DocTitle',
        parent=base_styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=c_primary,
        spaceAfter=2
    )

    s_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_muted
    )

    s_section_hdr = ParagraphStyle(
        'SectionHdr',
        parent=base_styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=c_primary,
        spaceBefore=8,
        spaceAfter=4
    )

    s_th = ParagraphStyle(
        'TableHead',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    s_tb_bold = ParagraphStyle(
        'TableBodyBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    s_tb = ParagraphStyle(
        'TableBody',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    s_tb_muted = ParagraphStyle(
        'TableBodyMuted',
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=c_muted
    )

    s_tb_mono = ParagraphStyle(
        'TableBodyMono',
        fontName='Courier',
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#334155")
    )

    s_badge_uploaded = ParagraphStyle(
        'BadgeUploaded',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=c_success_fg,
        alignment=1  # Centered
    )

    s_badge_unavail = ParagraphStyle(
        'BadgeUnavail',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=c_warn_fg,
        alignment=1  # Centered
    )

    story = []

    # ==========================================================
    # 1. Header with Logo & Title
    # ==========================================================
    header_table_data = []
    left_logo = None

    if logo_path and os.path.exists(logo_path):
        try:
            drawing = svg2rlg(logo_path)
            if drawing:
                target_h = 36
                scale = target_h / drawing.height
                drawing.width = drawing.width * scale
                drawing.height = target_h
                drawing.scale(scale, scale)
                left_logo = drawing
        except Exception:
            left_logo = None

    if not left_logo:
        left_logo = Paragraph("<b>ETICHUB</b><br><font size=7 color='#64748B'>DOCUMENT SYSTEM</font>", s_title)

    right_meta = [
        Paragraph("<b>RAPPORTO DI RICEZIONE DOCUMENTI</b>", s_title),
        Paragraph(f"<b>Data Ricezione:</b> {form_data.get('submission_datetime', datetime.now().strftime('%d/%m/%Y %H:%M:%S'))}", s_subtitle),
        Paragraph(f"<b>ID Transazione:</b> {form_data.get('form_id', '—')}", s_subtitle)
    ]

    header_table = Table(
        [[left_logo, right_meta]],
        colWidths=[content_width * 0.38, content_width * 0.62]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=4, spaceAfter=10))

    # ==========================================================
    # 2. Metadata Grid (Form & Customer Details)
    # ==========================================================
    cust_display = customer_data.get('name') or "Non assegnato (Generico)"
    cust_code = customer_data.get('code', '—')
    cust_email = customer_data.get('email', '—')
    cust_vat = customer_data.get('vat', customer_data.get('fiscal_code', '—'))
    ip_addr = form_data.get('client_ip', '—')

    meta_grid_data = [
        [
            Paragraph("<b>DETTAGLI MODULO</b>", s_tb_bold),
            Paragraph("<b>ANAGRAFICA CLIENTE</b>", s_tb_bold)
        ],
        [
            Paragraph(f"<b>Modulo:</b> {form_data.get('name', '—')}", s_tb),
            Paragraph(f"<b>Cliente:</b> {cust_display}", s_tb)
        ],
        [
            Paragraph(f"<b>Progetto:</b> {form_data.get('project_name', '—') or 'Standard'}", s_tb),
            Paragraph(f"<b>Codice Cliente:</b> {cust_code}", s_tb)
        ],
        [
            Paragraph(f"<b>IP Sottomissione:</b> {ip_addr}", s_tb),
            Paragraph(f"<b>Email:</b> {cust_email}", s_tb)
        ],
    ]

    if cust_vat and cust_vat != '—':
        meta_grid_data.append([
            Paragraph(f"<b>Stato Modulo:</b> Completato", s_tb),
            Paragraph(f"<b>P.IVA / C.F.:</b> {cust_vat}", s_tb)
        ])

    meta_table = Table(
        meta_grid_data,
        colWidths=[content_width * 0.5, content_width * 0.5]
    )
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary_light),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # ==========================================================
    # 3. Form Input Fields (if any text fields were filled)
    # ==========================================================
    if form_fields and len(form_fields) > 0:
        story.append(Paragraph("DATI COMPILATI NEL MODULO", s_section_hdr))
        fields_table_data = [[
            Paragraph("Campo / Domanda", s_th),
            Paragraph("Valore Inserito", s_th)
        ]]

        for f in form_fields:
            fields_table_data.append([
                Paragraph(f"<b>{f.get('label', 'Campo')}</b>", s_tb),
                Paragraph(str(f.get('value', '—')), s_tb)
            ])

        fields_table = Table(fields_table_data, colWidths=[content_width * 0.4, content_width * 0.6])
        fields_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_primary),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, c_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(fields_table)
        story.append(Spacer(1, 10))

    # ==========================================================
    # 4. Documents Receipt Table
    # ==========================================================
    story.append(Paragraph("RIASSUNTO RICEZIONE DOCUMENTI", s_section_hdr))

    doc_table_data = [[
        Paragraph("Documento", s_th),
        Paragraph("Stato", s_th),
        Paragraph("Dettagli / File Archiviato", s_th),
        Paragraph("Dimensione", s_th),
        Paragraph("Codice SHA-256 (Integrità)", s_th),
    ]]

    col_widths = [
        content_width * 0.28,  # Nome documento
        content_width * 0.16,  # Stato badge
        content_width * 0.24,  # Dettagli / filename
        content_width * 0.10,  # Dimensione
        content_width * 0.22   # Checksum
    ]

    total_uploaded = 0
    total_unavail = 0

    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
    ]

    for idx, doc_item in enumerate(uploads, start=1):
        doc_name = doc_item.get('document_name', f'Documento {idx}')
        is_req = doc_item.get('required', False)
        status = doc_item.get('availability_status', 'uploaded')
        is_unavail = doc_item.get('indisponibile', False) or status == 'not_available'

        req_tag = "<font color='#B42318'>*Obbligatorio</font>" if is_req else "<font color='#64748B'>Facoltativo</font>"
        doc_cell = Paragraph(f"<b>{doc_name}</b><br/>{req_tag}", s_tb)

        if not is_unavail and doc_item.get('stored_filename'):
            total_uploaded += 1
            badge_cell = Paragraph("<b>✓ CARICATO</b>", s_badge_uploaded)
            orig_name = doc_item.get('original_filename', '—')
            stored_name = doc_item.get('stored_filename', '—')
            details_cell = Paragraph(f"<b>Originale:</b> {orig_name}<br/><b>NAS:</b> {stored_name}", s_tb_muted)
            size_cell = Paragraph(format_file_size(doc_item.get('file_size', 0)), s_tb)
            sha = doc_item.get('sha256', '—')
            sha_cell = Paragraph(sha[:32] + "<br/>" + sha[32:] if len(sha) == 64 else sha, s_tb_mono)
            table_styles.append(('BACKGROUND', (1, idx), (1, idx), c_success_bg))
        else:
            total_unavail += 1
            badge_cell = Paragraph("<b>⚠️ NON DISPONIBILE</b>", s_badge_unavail)
            reason = doc_item.get('motivazione_indisponibilita') or "Nessun motivo specificato"
            details_cell = Paragraph(f"<b>Motivo:</b> {reason}", s_tb_muted)
            size_cell = Paragraph("—", s_tb)
            sha_cell = Paragraph("—", s_tb)
            table_styles.append(('BACKGROUND', (1, idx), (1, idx), c_warn_bg))

        doc_table_data.append([doc_cell, badge_cell, details_cell, size_cell, sha_cell])

    doc_table = Table(doc_table_data, colWidths=col_widths)
    doc_table.setStyle(TableStyle(table_styles))
    story.append(doc_table)
    story.append(Spacer(1, 10))

    # ==========================================================
    # 5. Summary & Verification Statement
    # ==========================================================
    summary_html = f"""
    <b>Riepilogo:</b> {total_uploaded} documento/i acquisito/i con successo · {total_unavail} documento/i contrassegnato/i come non disponibile/i.<br/>
    <b>Verifica Integrità:</b> I file contrassegnati come <i>CARICATO</i> sono stati memorizzati nell'archivio protetto sul NAS aziendale Etichub. I digest crittografici SHA-256 sopra riportati garantiscono la non alterabilità dei documenti ricevuti rispetto allo stato originale inviato dal mittente.
    """
    summary_box = Table(
        [[Paragraph(summary_html, s_tb_muted)]],
        colWidths=[content_width]
    )
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_box)

    # Build the document using the NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_pdf_path


def generate_form_receipt_pdf(form_template, assignment, pdf_path):
    """
    Generate PDF receipt for an assignment submission.
    """
    customer = assignment.customer
    customer_data = {
        'name': f"{customer.first_name} {customer.last_name}".strip() if customer else "Cliente",
        'code': customer.code if customer else "—",
        'email': customer.email if customer else "—",
        'phone': customer.phone if customer else "—",
        'vat_number': getattr(customer, 'vat_number', '—'),
        'fiscal_code': getattr(customer, 'fiscal_code', '—'),
    }
    project_name = assignment.form_data.get('project_name', '') if assignment.form_data else ''
    form_data = {
        'id': str(assignment.id),
        'name': form_template.name,
        'project_name': project_name or getattr(form_template, 'project_name', ''),
        'submission_time': (assignment.submission_date or datetime.now()).strftime('%d/%m/%Y %H:%M:%S'),
        'ip': '127.0.0.1',
    }

    uploads_data = []
    # Collect all requirements from template steps
    for step in form_template.formstep_set.all().order_by('order'):
        for req in step.documentrequirement_set.all().order_by('order'):
            up = assignment.documentupload_set.filter(document_requirement=req, status='valid').first()
            if up:
                is_unavail = (up.availability_status == 'not_available')
                uploads_data.append({
                    'document_name': req.name,
                    'required': req.required,
                    'availability_status': up.availability_status,
                    'indisponibile': is_unavail,
                    'motivazione_indisponibilita': up.motivazione_indisponibilita if is_unavail else '',
                    'original_filename': up.original_filename if not is_unavail else '—',
                    'stored_filename': up.stored_filename if not is_unavail else '',
                    'file_size': up.file_size or 0,
                    'sha256': up.sha256_checksum or '—',
                })
            else:
                uploads_data.append({
                    'document_name': req.name,
                    'required': req.required,
                    'availability_status': 'not_available',
                    'indisponibile': True,
                    'motivazione_indisponibilita': 'Non fornito',
                    'original_filename': '—',
                    'stored_filename': '',
                    'file_size': 0,
                    'sha256': '—',
                })

    return generate_submission_pdf(pdf_path, form_data, customer_data, uploads_data)
