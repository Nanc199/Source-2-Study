"""
Source2Study - Export Service
Generates PDF, DOCX, and TXT exports with dedicated high-fidelity generators
for Unique Question Banks and Repeated Question Multi-Year Analysis Reports.
Includes dynamic two-pass page numbering (Page X of Y) and running headers/footers.
"""

import io
import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that dynamically calculates the total page count
    and renders consistent academic running headers and footers (Page X of Y).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.report_title = "Source2Study Academic Report"
        self.report_subtitle = "Zero-Duplicate Question Bank"

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

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 808, self.report_title)
            self.drawRightString(555, 808, self.report_subtitle)
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.6)
            self.line(40, 800, 555, 800)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.6)
        self.line(40, 42, 555, 42)
        self.drawString(40, 30, "Source2Study — Intelligent Previous-Year Question Consolidation")
        self.drawRightString(555, 30, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class ExportService:
    """Export content to PDF, DOCX, and TXT formats with academic styling."""

    def _escape_xml(self, text: str) -> str:
        """Escape XML/HTML special characters for ReportLab Paragraphs."""
        text = str(text or "")
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _parse_question_content(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Parses a formatted question into its statement and multiple-choice options.
        Returns (statement_text, [(letter, option_text), ...]).
        """
        text = text.strip()

        # 1. Strip leading **Question X** or Question X: or Q.X: from statement
        cleaned_text = re.sub(r'^\s*\*\*(?:Question|Q\.?|Problem)\s*\d*\*\*\s*', '', text, flags=re.IGNORECASE).strip()
        cleaned_text = re.sub(r'^(?:(?:Question|Q|Problem)\s*\.?\s*\d+\s*[\.:\)\-]\s*)', '', cleaned_text, flags=re.IGNORECASE).strip()

        # 2. Check if **Options:** or Options: section exists
        options_header_match = re.search(r'\n+\s*(?:\*\*)?Options\s*:(?:\*\*)?\s*\n*', cleaned_text, flags=re.IGNORECASE)
        if options_header_match:
            stmt = cleaned_text[:options_header_match.start()].strip()
            opts_part = cleaned_text[options_header_match.end():].strip()
        else:
            opt_match = re.search(r'(?:(?:\n|\s{2,})(?:[A-Da-d][\.\)]|\([A-Da-d]\)|\[[A-Da-d]\])\s+)|(?:\([A-Da-d]\)\s+)', cleaned_text)
            if not opt_match:
                return cleaned_text, []
            stmt = cleaned_text[:opt_match.start()].strip()
            opts_part = cleaned_text[opt_match.start():].strip()

        options = []
        raw_options = re.split(r'(?=(?:^|\n|\s{2,}|\t)(?:\([A-Da-d]\)|\[[A-Da-d]\]|[A-Da-d][\.\)]))\s*', opts_part)
        for ro in raw_options:
            ro = ro.strip()
            if not ro:
                continue
            m = re.match(r'^(?:\(([A-Da-d])\)|\[([A-Da-d])\]|([A-Da-d])[\.\)])\s*(.+)', ro, re.DOTALL)
            if m:
                letter = (m.group(1) or m.group(2) or m.group(3)).upper()
                opt_body = m.group(4).strip()
                opt_body = re.sub(r'\[\s*\d+\s*(?:marks?|mark|m)\s*\]', '', opt_body, flags=re.IGNORECASE).strip()
                options.append((letter, opt_body))

        return stmt, options

    # ------------------------------------------------------------------
    # PDF 1: Unique Questions PDF
    # ------------------------------------------------------------------

    def export_unique_questions_pdf(
        self,
        questions: List[Dict],
        title: str = "Source2Study - Consolidated Unique Questions",
        stats: Optional[Dict] = None,
    ) -> bytes:
        """
        Generate a clean, professional PDF containing exclusively unique questions.
        Features KPI summary table, structured MCQ option layout, source attribution, and Page X of Y.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=40, rightMargin=40,
            topMargin=52, bottomMargin=52
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Title'], fontSize=18, leading=22, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#1E1B4B'), alignment=0, spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle', parent=styles['Normal'], fontSize=9.5, leading=13,
            textColor=colors.HexColor('#64748B'), spaceAfter=12
        )
        section_style = ParagraphStyle(
            'SectionHead', parent=styles['Heading2'], fontSize=12, leading=15, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#1E293B'), spaceBefore=10, spaceAfter=8
        )
        q_num_badge = ParagraphStyle(
            'QNumBadge', parent=styles['Normal'], fontSize=9, leading=12, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#4338CA')
        )
        topic_badge = ParagraphStyle(
            'TopicBadge', parent=styles['Normal'], fontSize=8, leading=11, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#475569'), alignment=2
        )
        q_text_style = ParagraphStyle(
            'QText', parent=styles['Normal'], fontSize=10, leading=14.5,
            textColor=colors.HexColor('#0F172A'), spaceAfter=4
        )
        opt_letter_style = ParagraphStyle(
            'OptLetter', parent=styles['Normal'], fontSize=9.5, leading=13, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#4F46E5')
        )
        opt_text_style = ParagraphStyle(
            'OptText', parent=styles['Normal'], fontSize=9.5, leading=13,
            textColor=colors.HexColor('#334155')
        )
        meta_style = ParagraphStyle(
            'QMeta', parent=styles['Normal'], fontSize=8.5, leading=12,
            textColor=colors.HexColor('#64748B')
        )
        stat_label_style = ParagraphStyle(
            'StatLabel', parent=styles['Normal'], fontSize=7.5, leading=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#64748B'), alignment=1
        )
        stat_val_style = ParagraphStyle(
            'StatVal', parent=styles['Normal'], fontSize=13, leading=16, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#1E1B4B'), alignment=1
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph(self._escape_xml(title), title_style))
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')} &bull; Zero-Duplicate Academic Question Bank &bull; Consolidated for Study & Revision",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#6366F1'), spaceAfter=12))

        # 2. Metrics Summary Table
        if stats:
            total_docs = stats.get('total_documents', 1)
            total_q = stats.get('total_questions', len(questions))
            unique_q = stats.get('unique_questions', len(questions))
            dup_pct = stats.get('duplicate_percentage', 0.0)

            summary_data = [
                [
                    Paragraph("TOTAL PAPERS ANALYZED", stat_label_style),
                    Paragraph("RAW QUESTIONS EXTRACTED", stat_label_style),
                    Paragraph("UNIQUE QUESTIONS RETAINED", stat_label_style),
                    Paragraph("REDUNDANCY OVERLAP", stat_label_style),
                ],
                [
                    Paragraph(str(total_docs), stat_val_style),
                    Paragraph(str(total_q), stat_val_style),
                    Paragraph(str(unique_q), stat_val_style),
                    Paragraph(f"{dup_pct}%", stat_val_style),
                ]
            ]
            t = Table(summary_data, colWidths=[128, 128, 128, 131])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 14))

        elements.append(Paragraph(f"Consolidated Question Bank &mdash; {len(questions)} Unique Questions", section_style))
        elements.append(Spacer(1, 6))

        if not questions:
            elements.append(Paragraph("No questions found across the analyzed resources.", q_text_style))
        else:
            for i, q in enumerate(questions, 1):
                raw_text = q.get("question_text") or q.get("question") or q.get("canonical_question") or ""
                statement, options = self._parse_question_content(raw_text)
                topic = q.get("topic") or "General"
                q_type = (q.get("question_type") or "MCQ").upper()
                q_num_orig = q.get("question_number") or f"Q.{i}"

                # Sources formatting
                all_srcs = q.get("all_sources") or []
                if all_srcs:
                    src_chips = []
                    for s in all_srcs:
                        fn = s.get("source_filename") or "Exam Paper"
                        yr = f" ({s['year']})" if s.get("year") else ""
                        pg = f" [p. {s['page_number']}]" if s.get("page_number") else ""
                        qn = f" {s['question_number']}" if s.get("question_number") else ""
                        src_chips.append(f"{self._escape_xml(fn)}{yr}{qn}{pg}")
                    sources_str = " &bull; ".join(src_chips)
                else:
                    fn = q.get("source_filename") or "Exam Paper"
                    yr = f" ({q['year']})" if q.get("year") else ""
                    pg = f" [p. {q['page_number']}]" if q.get("page_number") else ""
                    sources_str = f"{self._escape_xml(fn)}{yr}{pg}"

                card_elements = []

                # Card Top Strip
                top_strip = [
                    [
                        Paragraph(f"<b>#{i}</b> &nbsp;&bull;&nbsp; <font color='#4338CA'><b>{self._escape_xml(q_num_orig)}</b></font> &nbsp;[{self._escape_xml(q_type)}]", q_num_badge),
                        Paragraph(f"<b>Topic:</b> {self._escape_xml(topic)}", topic_badge),
                    ]
                ]
                strip_table = Table(top_strip, colWidths=[260, 255])
                strip_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                card_elements.append(strip_table)
                card_elements.append(Spacer(1, 3))

                # Question Statement
                card_elements.append(Paragraph(self._escape_xml(statement), q_text_style))

                # Formatted Options Table (if MCQ)
                if options:
                    card_elements.append(Spacer(1, 3))
                    opt_rows = []
                    for l, o_txt in options:
                        opt_rows.append([
                            Paragraph(f"<b>({l})</b>", opt_letter_style),
                            Paragraph(self._escape_xml(o_txt), opt_text_style),
                        ])
                    opts_table = Table(opt_rows, colWidths=[28, 487])
                    opts_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#F1F5F9')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    card_elements.append(opts_table)

                # Source Attribution Footer
                card_elements.append(Spacer(1, 3))
                card_elements.append(Paragraph(f"<b>Appeared In:</b> {sources_str}", meta_style))
                card_elements.append(Spacer(1, 4))
                card_elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0'), spaceAfter=8))

                elements.append(KeepTogether(card_elements) if len(options) <= 4 else card_elements)

        def make_canvas(*args, **kwargs):
            c = NumberedCanvas(*args, **kwargs)
            c.report_title = "Source2Study — Consolidated Unique Questions Bank"
            c.report_subtitle = "Zero-Duplicate Revision Bank"
            return c

        doc.build(elements, canvasmaker=make_canvas)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # PDF 2: Repeated Questions PDF
    # ------------------------------------------------------------------

    def export_repeated_questions_pdf(
        self,
        repeated_groups: List[Dict],
        title: str = "Source2Study - Repeated Questions Analysis",
        stats: Optional[Dict] = None,
    ) -> bytes:
        """
        Generate a dedicated, professional PDF containing ONLY repeated questions.
        Highlights multi-year recurrence, paper citations, question numbers, page numbers,
        similarity degrees (Exact Match / High Similarity / Conceptual Duplicate), and Page X of Y.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=40, rightMargin=40,
            topMargin=52, bottomMargin=52
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Title'], fontSize=18, leading=22, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#991B1B'), alignment=0, spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle', parent=styles['Normal'], fontSize=9.5, leading=13,
            textColor=colors.HexColor('#64748B'), spaceAfter=12
        )
        section_style = ParagraphStyle(
            'SectionHead', parent=styles['Heading2'], fontSize=12, leading=15, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#1E293B'), spaceBefore=10, spaceAfter=8
        )
        group_badge_style = ParagraphStyle(
            'GroupBadge', parent=styles['Normal'], fontSize=9.5, leading=13, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#DC2626')
        )
        group_topic_style = ParagraphStyle(
            'GroupTopic', parent=styles['Normal'], fontSize=8.5, leading=11, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#475569'), alignment=2
        )
        q_text_style = ParagraphStyle(
            'QText', parent=styles['Normal'], fontSize=10, leading=14.5,
            textColor=colors.HexColor('#0F172A'), spaceAfter=4
        )
        opt_letter_style = ParagraphStyle(
            'OptLetter', parent=styles['Normal'], fontSize=9, leading=12, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#DC2626')
        )
        opt_text_style = ParagraphStyle(
            'OptText', parent=styles['Normal'], fontSize=9, leading=12,
            textColor=colors.HexColor('#334155')
        )
        table_head_style = ParagraphStyle(
            'TH', parent=styles['Normal'], fontSize=8, leading=10, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#FFFFFF'), alignment=1
        )
        table_cell_style = ParagraphStyle(
            'TD', parent=styles['Normal'], fontSize=8, leading=11,
            textColor=colors.HexColor('#1E293B')
        )
        table_cell_center = ParagraphStyle(
            'TDC', parent=styles['Normal'], fontSize=8, leading=11,
            textColor=colors.HexColor('#1E293B'), alignment=1
        )
        table_badge_exact = ParagraphStyle(
            'TDBE', parent=styles['Normal'], fontSize=7.5, leading=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#059669'), alignment=1
        )
        table_badge_high = ParagraphStyle(
            'TDBH', parent=styles['Normal'], fontSize=7.5, leading=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#D97706'), alignment=1
        )
        table_badge_concept = ParagraphStyle(
            'TDBC', parent=styles['Normal'], fontSize=7.5, leading=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#4F46E5'), alignment=1
        )
        stat_label_style = ParagraphStyle(
            'StatLabel', parent=styles['Normal'], fontSize=7.5, leading=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#64748B'), alignment=1
        )
        stat_val_style = ParagraphStyle(
            'StatVal', parent=styles['Normal'], fontSize=13, leading=16, fontName="Helvetica-Bold",
            textColor=colors.HexColor('#991B1B'), alignment=1
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph(self._escape_xml(title), title_style))
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')} &bull; Multi-Year Recurrence Analysis &bull; Focus on High-Yield Repeat Questions",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#EF4444'), spaceAfter=12))

        # 2. Metrics Summary Table
        if stats:
            total_docs = stats.get('total_documents', 1)
            total_q = stats.get('total_questions', 0)
            rep_groups_count = len(repeated_groups)
            total_repeats = stats.get('total_duplicate_occurrences', 0) or stats.get('duplicate_questions', 0)

            summary_data = [
                [
                    Paragraph("TOTAL PAPERS ANALYZED", stat_label_style),
                    Paragraph("TOTAL QUESTIONS", stat_label_style),
                    Paragraph("REPEATED QUESTION GROUPS", stat_label_style),
                    Paragraph("REDUNDANT OCCURRENCES", stat_label_style),
                ],
                [
                    Paragraph(str(total_docs), stat_val_style),
                    Paragraph(str(total_q), stat_val_style),
                    Paragraph(str(rep_groups_count), stat_val_style),
                    Paragraph(str(total_repeats), stat_val_style),
                ]
            ]
            t = Table(summary_data, colWidths=[128, 128, 128, 131])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF2F2')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#FECACA')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 14))

        # 3. High-Yield Question Topics Highlight Box
        if repeated_groups:
            top_repeated = sorted(repeated_groups, key=lambda g: g.get("frequency", 0), reverse=True)[:5]
            hl_rows = [
                [
                    Paragraph("<b>HIGH-YIELD REVISION TOPICS (MOST FREQUENTLY REPEATED)</b>", ParagraphStyle(
                        'HLT', parent=styles['Normal'], fontSize=8.5, leading=11, fontName="Helvetica-Bold",
                        textColor=colors.HexColor('#991B1B')
                    ))
                ]
            ]
            for tr_idx, tr in enumerate(top_repeated, 1):
                tr_q = tr.get("canonical_question") or ""
                stmt_short, _ = self._parse_question_content(tr_q)
                if len(stmt_short) > 130:
                    stmt_short = stmt_short[:127] + "..."
                freq = tr.get("frequency") or len(tr.get("members", []))
                yrs = ", ".join(tr.get("years", [])) or "Multiple Years"
                topic = tr.get("topic") or "General"
                hl_rows.append([
                    Paragraph(
                        f"&bull; <b>{self._escape_xml(topic)}</b> &mdash; <i>Appeared {freq} times ({self._escape_xml(yrs)})</i>: {self._escape_xml(stmt_short)}",
                        ParagraphStyle('HLItem', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#374151'))
                    )
                ])

            hl_table = Table(hl_rows, colWidths=[515])
            hl_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF7ED')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#FED7AA')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(hl_table)
            elements.append(Spacer(1, 14))

        elements.append(Paragraph(f"Identified Repeated Questions &mdash; {len(repeated_groups)} Question Groups", section_style))
        elements.append(Spacer(1, 6))

        if not repeated_groups:
            elements.append(Paragraph(
                "No repeated questions were found across the analyzed papers (all extracted questions are distinct).",
                q_text_style
            ))
        else:
            for i, group in enumerate(repeated_groups, 1):
                canonical = group.get("canonical_question") or group.get("question") or ""
                statement, options = self._parse_question_content(canonical)
                freq = group.get("frequency") or len(group.get("members", []))
                topic = group.get("topic") or "General"
                members = group.get("members", [])

                card_elements = []

                # Group Header
                strip_data = [
                    [
                        Paragraph(f"<b>Repeated Question #{i}</b> &nbsp;&bull;&nbsp; <font color='#DC2626'><b>Appeared in {freq} Question Papers</b></font>", group_badge_style),
                        Paragraph(f"<b>Topic:</b> {self._escape_xml(topic)}", group_topic_style),
                    ]
                ]
                strip_table = Table(strip_data, colWidths=[280, 235])
                strip_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                card_elements.append(strip_table)
                card_elements.append(Spacer(1, 3))

                # Canonical Question Statement
                card_elements.append(Paragraph(f"<b>Standard Question Formulation:</b>", ParagraphStyle(
                    'SH', parent=styles['Normal'], fontSize=8.5, leading=11, fontName="Helvetica-Bold", textColor=colors.HexColor('#475569')
                )))
                card_elements.append(Paragraph(self._escape_xml(statement), q_text_style))

                # Formatted Options Table (if MCQ)
                if options:
                    card_elements.append(Spacer(1, 2))
                    opt_rows = []
                    for l, o_txt in options:
                        opt_rows.append([
                            Paragraph(f"<b>({l})</b>", opt_letter_style),
                            Paragraph(self._escape_xml(o_txt), opt_text_style),
                        ])
                    opts_table = Table(opt_rows, colWidths=[28, 487])
                    opts_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF2F2')),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
                        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#FEE2E2')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    card_elements.append(opts_table)

                # Recurrence Breakdown Table
                card_elements.append(Spacer(1, 5))
                card_elements.append(Paragraph("<b>Recurrence Breakdown across Exam Papers:</b>", ParagraphStyle(
                    'SH2', parent=styles['Normal'], fontSize=8.5, leading=11, fontName="Helvetica-Bold", textColor=colors.HexColor('#475569')
                )))
                card_elements.append(Spacer(1, 2))

                occ_table_rows = [
                    [
                        Paragraph("Exam Paper / Source", table_head_style),
                        Paragraph("Year", table_head_style),
                        Paragraph("Question #", table_head_style),
                        Paragraph("Page", table_head_style),
                        Paragraph("Match Type", table_head_style),
                    ]
                ]

                for m in members:
                    source_name = m.get("source_filename") or m.get("source") or "Exam Paper"
                    year_str = str(m.get("year") or "-")
                    q_num_str = str(m.get("question_number") or "-")
                    page_str = f"Page {m['page_number']}" if m.get("page_number") else "Body"
                    match_type = m.get("match_type") or "Exact Match"

                    if match_type == "Exact Match":
                        badge_p = Paragraph("Exact Match", table_badge_exact)
                    elif match_type == "High Similarity":
                        badge_p = Paragraph("High Similarity", table_badge_high)
                    else:
                        badge_p = Paragraph("Conceptual", table_badge_concept)

                    occ_table_rows.append([
                        Paragraph(self._escape_xml(source_name), table_cell_style),
                        Paragraph(self._escape_xml(year_str), table_cell_center),
                        Paragraph(self._escape_xml(q_num_str), table_cell_center),
                        Paragraph(self._escape_xml(page_str), table_cell_center),
                        badge_p,
                    ])

                occ_table = Table(occ_table_rows, colWidths=[205, 55, 75, 70, 110])
                occ_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ]))
                card_elements.append(occ_table)
                card_elements.append(Spacer(1, 5))
                card_elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#E2E8F0'), spaceAfter=8))

                elements.append(KeepTogether(card_elements) if len(members) <= 3 else card_elements)

        def make_canvas(*args, **kwargs):
            c = NumberedCanvas(*args, **kwargs)
            c.report_title = "Source2Study — Repeated Questions Recurrence Report"
            c.report_subtitle = "Multi-Year Previous-Year Analysis"
            return c

        doc.build(elements, canvasmaker=make_canvas)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Generic Helpers (Preserved for compatibility)
    # ------------------------------------------------------------------

    def export_pdf(self, content: Any, title: str = "Source2Study Export") -> bytes:
        """Generate a generic PDF document."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'], fontSize=20, spaceAfter=20,
            textColor=colors.HexColor('#1E293B')
        )
        heading_style = ParagraphStyle(
            'CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=10,
            textColor=colors.HexColor('#7C3AED'), spaceBefore=15
        )
        body_style = ParagraphStyle(
            'CustomBody', parent=styles['Normal'], fontSize=11, leading=16,
            spaceAfter=8
        )
        badge_style = ParagraphStyle(
            'Badge', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6366F1')
        )

        elements = []
        elements.append(Paragraph(self._escape_xml(title), title_style))
        elements.append(Paragraph("Generated by Source2Study", badge_style))
        elements.append(Spacer(1, 20))

        if isinstance(content, dict):
            if "topics" in content:
                stats = content.get("stats", {})
                elements.append(Paragraph(
                    f"Total Questions: {stats.get('total_questions', 0)} | "
                    f"Unique: {stats.get('unique_questions', 0)} | "
                    f"Duplicates: {stats.get('duplicate_questions', 0)}",
                    body_style
                ))
                elements.append(Spacer(1, 15))
                for topic in content.get("topics", []):
                    elements.append(Paragraph(self._escape_xml(topic["name"]), heading_style))
                    for q in topic.get("questions", []):
                        freq_text = f" [{q.get('frequency_label', '')} - appeared {q.get('frequency', 1)} times]"
                        elements.append(Paragraph(
                            f"Q{q['number']}. {self._escape_xml(q['question'])}{freq_text}",
                            body_style
                        ))
                        if q.get("years"):
                            elements.append(Paragraph(f"Years: {', '.join(q['years'])}", badge_style))
                        elements.append(Spacer(1, 5))
            elif "content" in content:
                for line in content["content"].split("\n"):
                    if line.strip():
                        elements.append(Paragraph(self._escape_xml(line), body_style))
        elif isinstance(content, str):
            for para in content.split('\n'):
                if para.strip():
                    elements.append(Paragraph(self._escape_xml(para), body_style))

        if not elements or len(elements) <= 3:
            elements.append(Paragraph("No content to export.", body_style))

        doc.build(elements)
        return buffer.getvalue()

    def export_docx(self, content: Any, title: str = "Source2Study Export") -> bytes:
        """Generate a DOCX document."""
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
        except ImportError:
            raise ImportError("python-docx is required for DOCX export.")

        doc = Document()
        doc.add_heading(title, level=0)
        subtitle = doc.add_paragraph("Generated by Source2Study")
        if subtitle.runs:
            subtitle.runs[0].font.color.rgb = RGBColor(99, 102, 241)

        if isinstance(content, dict) and "content" in content:
            doc.add_paragraph(content["content"])
        elif isinstance(content, str):
            doc.add_paragraph(content)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    def export_txt(self, content: Any, title: str = "Source2Study Export") -> bytes:
        """Generate a TXT document."""
        lines = [title, "=" * len(title), "Generated by Source2Study", "", ""]
        if isinstance(content, dict) and "content" in content:
            lines.append(content["content"])
        elif isinstance(content, str):
            lines.append(content)
        return "\n".join(lines).encode("utf-8")
