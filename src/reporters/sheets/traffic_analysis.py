"""Traffic analysis sheet generator."""

import logging
from datetime import datetime
from typing import Any, Dict
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from .base_sheet import BaseSheet

logger = logging.getLogger(__name__)


class TrafficAnalysisSheet(BaseSheet):
    """Sheet generator for traffic analysis."""

    def __init__(self, workbook):
        super().__init__()
        self.workbook = workbook

    def build(self, metrics: Dict[str, Any]) -> None:
        """
        Create the Traffic Analysis sheet.
        """
        logger.info("Creating Traffic Analysis sheet...")

        ws = self.workbook.create_sheet("Traffic Analysis")

        # Title with professional styling
        ws['A1'] = 'Traffic Analysis'
        ws['A1'].font = Font(bold=True, size=18, color='1F4E78', name='Calibri')
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells('A1:E1')
        ws.row_dimensions[1].height = 30

        # Subtitle
        ws['A2'] = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        ws['A2'].font = Font(size=10, italic=True, color='808080', name='Calibri')
        ws.merge_cells('A2:E2')

        row = 4

        # Daily trends chart
        daily_data = metrics.get('daily_trends')
        if daily_data is not None and not daily_data.empty:
            try:
                chart_buffer = self.viz.create_daily_traffic_chart(daily_data)
                img = XLImage(chart_buffer)
                img.width = 800
                img.height = 400
                ws.add_image(img, f'A{row}')
                row += 25
            except Exception as e:
                logger.warning(f"Could not create daily traffic chart: {e}")

        # Geographic distribution
        geo_data = metrics.get('geographic_distribution', [])
        if geo_data:
            ws[f'A{row}'] = 'Geographic Distribution'
            ws[f'A{row}'].font = self.subtitle_font
            ws.merge_cells(f'A{row}:E{row}')
            row += 1

            # Create table
            headers = ['Country', 'Total Requests', 'Blocked', 'Allowed', 'Threat Score']
            self._format_header_row(ws, row, headers)
            row += 1

            for idx, country_data in enumerate(geo_data[:20]):  # Top 20
                highlight = idx % 2 == 0
                threat_score = country_data.get('threat_score', 0)

                row_data = [
                    country_data.get('country', ''),
                    country_data.get('total_requests', 0),
                    country_data.get('blocked_requests', 0),
                    country_data.get('allowed_requests', 0),
                    f"{threat_score:.1f}%"
                ]

                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row, column=col_idx)
                    self._format_data_cell(cell, value, highlight)

                # Color code threat score
                threat_cell = ws.cell(row=row, column=5)
                if threat_score > 50:
                    threat_cell.fill = self.danger_fill
                    threat_cell.font = Font(bold=True, size=10, color='C00000', name='Calibri')
                elif threat_score > 25:
                    threat_cell.fill = self.warning_fill
                    threat_cell.font = Font(bold=True, size=10, color='FF8C00', name='Calibri')

                row += 1

            # Add geographic chart
            row += 2
            try:
                chart_buffer = self.viz.create_geographic_threat_chart(geo_data)
                img = XLImage(chart_buffer)
                img.width = 800
                img.height = 500
                ws.add_image(img, f'A{row}')
            except Exception as e:
                logger.warning(f"Could not create geographic chart: {e}")

        # Auto-adjust columns
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws.column_dimensions[col].width = 18
