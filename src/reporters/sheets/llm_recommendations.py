"""LLM recommendations sheet template."""

import logging
from datetime import datetime
from openpyxl.styles import Alignment, Font, PatternFill
from .base_sheet import BaseSheet

logger = logging.getLogger(__name__)


class LLMRecommendationsSheet(BaseSheet):
    """Sheet generator for llm."""

    def __init__(self, workbook):
        super().__init__()
        self.workbook = workbook

    def build(self) -> None:
        """
        Create the LLM Recommendations sheet (template for manual population).
        """
        logger.info("Creating LLM Recommendations sheet...")

        ws = self.workbook.create_sheet("LLM Recommendations")

        # Title with professional styling
        ws['A1'] = 'AI-Generated Security Recommendations'
        ws['A1'].font = Font(bold=True, size=18, color='1F4E78', name='Calibri')
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells('A1:D1')
        ws.row_dimensions[1].height = 30

        # Subtitle
        ws['A2'] = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        ws['A2'].font = Font(size=10, italic=True, color='808080', name='Calibri')
        ws.merge_cells('A2:D2')

        row = 4

        # Instructions box with highlighted background
        ws[f'A{row}'] = 'Instructions:'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:D{row}')
        row += 1

        instructions = [
            '1. Use the LLM prompt templates in config/prompts/ with the metrics from this report',
            '2. Populate the sections below with AI-generated findings and recommendations',
            '3. Review and validate all AI recommendations before implementation',
            '4. Prioritize actions based on your organization\'s risk tolerance and requirements'
        ]

        for instruction in instructions:
            ws[f'A{row}'] = instruction
            ws[f'A{row}'].font = Font(italic=True, size=10, name='Calibri')
            ws[f'A{row}'].fill = PatternFill(start_color='FFF4E6', end_color='FFF4E6', fill_type='solid')
            ws.merge_cells(f'A{row}:D{row}')
            row += 1

        # Sections with professional styling
        sections = [
            ('Critical Findings', 'Immediate action required', 'FF6B6B'),
            ('High Priority Recommendations', 'Implement within 30 days', 'FFA500'),
            ('Medium Priority Optimizations', 'Implement within 90 days', 'FFD93D'),
            ('Low Priority Suggestions', 'Nice to have improvements', '6BCF7F')
        ]

        for section_title, section_desc, color in sections:
            row += 2
            ws[f'A{row}'] = section_title
            ws[f'A{row}'].font = Font(bold=True, size=12, color='FFFFFF', name='Calibri')
            ws[f'A{row}'].fill = PatternFill(start_color=color, end_color=color, fill_type='solid')
            ws[f'A{row}'].alignment = Alignment(horizontal='left', vertical='center')
            ws[f'A{row}'].border = self.thin_border
            ws.merge_cells(f'A{row}:D{row}')
            ws.row_dimensions[row].height = 25
            row += 1

            ws[f'A{row}'] = section_desc
            ws[f'A{row}'].font = Font(italic=True, size=10, name='Calibri')
            ws[f'A{row}'].fill = self.highlight_fill
            ws.merge_cells(f'A{row}:D{row}')
            row += 1

            # Template rows
            headers = ['Priority', 'Finding/Recommendation', 'Impact', 'Action Items']
            self._format_header_row(ws, row, headers)
            row += 1

            # Add 3 empty rows with borders for each section
            for i in range(3):
                for col_idx in range(1, 5):
                    cell = ws.cell(row=row, column=col_idx)
                    cell.border = self.thin_border
                    if i % 2 == 0:
                        cell.fill = self.highlight_fill
                row += 1

        # Auto-adjust columns
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 50
