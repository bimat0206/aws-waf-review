"""Rule effectiveness sheet generator."""

import logging
from datetime import datetime
from typing import Any, Dict
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from .base_sheet import BaseSheet

logger = logging.getLogger(__name__)


class RuleEffectivenessSheet(BaseSheet):
    """Sheet generator for rule effectiveness."""

    def __init__(self, workbook):
        super().__init__()
        self.workbook = workbook

    def build(self, metrics: Dict[str, Any]) -> None:
        """
        Create the Rule Effectiveness sheet.
        """
        logger.info("Creating Rule Effectiveness sheet...")

        ws = self.workbook.create_sheet("Rule Effectiveness")

        # Title with professional styling
        ws['A1'] = 'Rule Effectiveness Analysis'
        ws['A1'].font = Font(bold=True, size=18, color='1F4E78', name='Calibri')
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells('A1:G1')
        ws.row_dimensions[1].height = 30

        # Subtitle
        ws['A2'] = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        ws['A2'].font = Font(size=10, italic=True, color='808080', name='Calibri')
        ws.merge_cells('A2:G2')

        row = 4

        # Rule effectiveness table
        rule_data = metrics.get('rule_effectiveness', [])
        if rule_data:
            # Headers
            headers = ['Rule ID', 'Rule Type', 'Hit Count', 'Blocks', 'Allows', 'Hit Rate %', 'Block Rate %']
            self._format_header_row(ws, row, headers)
            row += 1

            # Data
            for idx, rule in enumerate(rule_data):
                highlight = idx % 2 == 0
                hit_rate = rule.get('hit_rate_percent', 0)

                row_data = [
                    rule.get('rule_id', '')[:50],
                    rule.get('rule_type', ''),
                    rule.get('hit_count', 0),
                    rule.get('blocks', 0),
                    rule.get('allows', 0),
                    f"{hit_rate:.1f}",
                    f"{rule.get('block_rate_percent', 0):.1f}"
                ]

                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row, column=col_idx)
                    self._format_data_cell(cell, value, highlight)

                # Color code hit rate
                hit_rate_cell = ws.cell(row=row, column=6)
                if hit_rate == 0:
                    hit_rate_cell.fill = self.danger_fill
                    hit_rate_cell.font = Font(bold=True, size=10, color='C00000', name='Calibri')
                elif hit_rate > 10:
                    hit_rate_cell.fill = self.success_fill
                    hit_rate_cell.font = Font(bold=True, size=10, color='008000', name='Calibri')

                row += 1

            # Add chart
            row += 2
            try:
                chart_buffer = self.viz.create_rule_effectiveness_chart(rule_data)
                img = XLImage(chart_buffer)
                img.width = 800
                img.height = 500
                ws.add_image(img, f'A{row}')
            except Exception as e:
                logger.warning(f"Could not create rule effectiveness chart: {e}")

        # Attack type distribution
        attack_data = metrics.get('attack_type_distribution', {})
        if attack_data:
            row += 30
            ws[f'A{row}'] = 'Attack Type Distribution'
            ws[f'A{row}'].font = self.subtitle_font
            ws.merge_cells(f'A{row}:G{row}')
            row += 2

            try:
                chart_buffer = self.viz.create_attack_type_chart(attack_data)
                img = XLImage(chart_buffer)
                img.width = 700
                img.height = 500
                ws.add_image(img, f'A{row}')
            except Exception as e:
                logger.warning(f"Could not create attack type chart: {e}")

        # Auto-adjust columns
        ws.column_dimensions['A'].width = 50
        for col in ['B', 'C', 'D', 'E', 'F', 'G']:
            ws.column_dimensions[col].width = 15
