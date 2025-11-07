"""
Excel Report Generator

This module generates comprehensive multi-sheet Excel reports with visualizations
for AWS WAF analysis results.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
from openpyxl.drawing.image import Image as XLImage
import pandas as pd

from .visualization_helpers import VisualizationHelpers

logger = logging.getLogger(__name__)


class ExcelReportGenerator:
    """
    Generates comprehensive Excel reports for WAF analysis.
    """

    def __init__(self, output_path: str):
        """
        Initialize the Excel report generator.

        Args:
            output_path (str): Path to save the Excel file
        """
        self.output_path = output_path
        self.workbook = Workbook()
        # Remove default sheet
        if 'Sheet' in self.workbook.sheetnames:
            del self.workbook['Sheet']

        self.viz = VisualizationHelpers()

        # Professional Styling Theme
        self.header_font = Font(bold=True, size=11, color='FFFFFF', name='Calibri')
        self.header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')  # Professional blue
        self.title_font = Font(bold=True, size=14, color='1F4E78', name='Calibri')
        self.subtitle_font = Font(bold=True, size=12, color='2C3E50', name='Calibri')
        self.data_font = Font(size=10, name='Calibri')
        self.highlight_fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')  # Light gray
        self.success_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # Light green
        self.warning_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')  # Light yellow
        self.danger_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')  # Light red

        # Border styles
        self.thin_border = Border(
            left=Side(style='thin', color='D0D0D0'),
            right=Side(style='thin', color='D0D0D0'),
            top=Side(style='thin', color='D0D0D0'),
            bottom=Side(style='thin', color='D0D0D0')
        )
        self.thick_border = Border(
            left=Side(style='medium', color='1F4E78'),
            right=Side(style='medium', color='1F4E78'),
            top=Side(style='medium', color='1F4E78'),
            bottom=Side(style='medium', color='1F4E78')
        )

        logger.info(f"Excel report generator initialized: {output_path}")

    def _apply_cell_style(self, cell, font=None, fill=None, border=None, alignment=None):
        """Apply consistent styling to a cell."""
        if font:
            cell.font = font
        if fill:
            cell.fill = fill
        if border:
            cell.border = border
        if alignment:
            cell.alignment = alignment

    def _format_header_row(self, ws, row, columns, start_col=1):
        """Format a header row with professional styling."""
        for col_idx, header in enumerate(columns, start=start_col):
            cell = ws.cell(row=row, column=col_idx)
            cell.value = header
            self._apply_cell_style(
                cell,
                font=self.header_font,
                fill=self.header_fill,
                border=self.thin_border,
                alignment=Alignment(horizontal='center', vertical='center', wrap_text=True)
            )
        ws.row_dimensions[row].height = 25

    def _format_data_cell(self, cell, value, highlight=False):
        """Format a data cell with professional styling."""
        cell.value = value
        self._apply_cell_style(
            cell,
            font=self.data_font,
            fill=self.highlight_fill if highlight else None,
            border=self.thin_border,
            alignment=Alignment(vertical='center', wrap_text=False)
        )

    def generate_report(self, metrics: Dict[str, Any], web_acls: List[Dict[str, Any]],
                       resources: List[Dict[str, Any]], logging_configs: List[Dict[str, Any]],
                       rules_by_web_acl: Dict[str, List[Dict[str, Any]]] = None) -> None:
        """
        Generate the complete Excel report.

        Args:
            metrics (Dict[str, Any]): Calculated metrics
            web_acls (List[Dict[str, Any]]): Web ACL configurations
            resources (List[Dict[str, Any]]): Resource associations
            logging_configs (List[Dict[str, Any]]): Logging configurations
            rules_by_web_acl (Dict[str, List[Dict[str, Any]]]): Rules grouped by Web ACL ID
        """
        logger.info("Generating Excel report...")

        if rules_by_web_acl is None:
            rules_by_web_acl = {}

        # Create all sheets
        self.create_executive_summary_sheet(metrics, web_acls)
        self.create_inventory_sheet(web_acls, resources, logging_configs, rules_by_web_acl)
        self.create_traffic_analysis_sheet(metrics)
        self.create_rule_effectiveness_sheet(metrics)
        self.create_client_analysis_sheet(metrics)
        self.create_llm_recommendations_sheet()

        # Save the workbook
        self.save()

        logger.info(f"Excel report generated successfully: {self.output_path}")

    def create_inventory_sheet(self, web_acls: List[Dict[str, Any]],
                               resources: List[Dict[str, Any]],
                               logging_configs: List[Dict[str, Any]],
                               rules_by_web_acl: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Create the Inventory sheet with Web ACLs, resources, and rules.
        """
        logger.info("Creating Inventory sheet...")

        ws = self.workbook.create_sheet("Inventory")

        # Title with professional styling
        ws['A1'] = 'AWS WAF Inventory'
        ws['A1'].font = Font(bold=True, size=18, color='1F4E78', name='Calibri')
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells('A1:H1')
        ws.row_dimensions[1].height = 30

        # Add a subtitle
        ws['A2'] = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        ws['A2'].font = Font(size=10, italic=True, color='808080', name='Calibri')
        ws.merge_cells('A2:H2')

        # Web ACLs section
        row = 4
        ws[f'A{row}'] = 'Web ACLs Configuration'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:H{row}')
        row += 1

        # Headers with professional formatting
        headers = ['Name', 'ID', 'Scope', 'Default Action', 'Capacity', 'Rules Count', 'Resources Count', 'Logging']
        self._format_header_row(ws, row, headers)
        row += 1

        # Data
        logging_config_ids = {lc.get('web_acl_id') for lc in logging_configs if lc.get('web_acl_id')}
        resources_count = {}
        for resource in resources:
            web_acl_id = resource.get('web_acl_id')
            if web_acl_id:
                resources_count[web_acl_id] = resources_count.get(web_acl_id, 0) + 1

        for idx, acl in enumerate(web_acls):
            acl_id = acl.get('web_acl_id', acl.get('Id', ''))
            acl_name = acl.get('name', acl.get('Name', ''))

            # Apply alternating row colors
            highlight = idx % 2 == 0

            default_action = acl.get('default_action', acl.get('DefaultAction', {}))
            if isinstance(default_action, str):
                action_str = default_action
            else:
                action_str = 'ALLOW' if 'Allow' in default_action else 'BLOCK'

            rules_count = len(rules_by_web_acl.get(acl_id, []))
            logging_enabled = 'Yes' if acl_id in logging_config_ids else 'No'

            # Apply professional styling to all cells in the row
            row_data = [
                acl_name,
                acl_id,
                acl.get('scope', acl.get('Scope', '')),
                action_str,
                acl.get('capacity', acl.get('Capacity', 0)),
                rules_count,
                resources_count.get(acl_id, 0),
                logging_enabled
            ]

            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row, column=col_idx)
                self._format_data_cell(cell, value, highlight)

            # Special color coding for logging status
            logging_cell = ws.cell(row=row, column=8)
            if logging_enabled == 'No':
                logging_cell.fill = self.danger_fill
            else:
                logging_cell.fill = self.success_fill

            row += 1

        # Rules section (detailed view)
        row += 2
        ws[f'A{row}'] = 'Rules and Rule Groups'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:E{row}')
        row += 1

        # Headers
        headers = ['Web ACL', 'Rule Name', 'Priority', 'Type', 'Action']
        self._format_header_row(ws, row, headers)
        row += 1

        # Get Web ACL names mapping
        web_acl_names = {acl.get('web_acl_id', acl.get('Id', '')): acl.get('name', acl.get('Name', '')) for acl in web_acls}

        # Data - rules sorted by Web ACL and priority
        all_rules = []
        for web_acl_id, rules in rules_by_web_acl.items():
            for rule in rules:
                all_rules.append({
                    'web_acl_name': web_acl_names.get(web_acl_id, web_acl_id),
                    'rule': rule
                })

        # Sort by Web ACL name and priority
        all_rules.sort(key=lambda x: (x['web_acl_name'], x['rule'].get('priority', 0)))

        import json
        for idx, item in enumerate(all_rules):
            rule = item['rule']

            # Parse action from JSON string if needed
            action = rule.get('action', '')
            if isinstance(action, str):
                try:
                    action_dict = json.loads(action) if action else {}
                    if 'Allow' in action_dict:
                        action = 'ALLOW'
                    elif 'Block' in action_dict:
                        action = 'BLOCK'
                    elif 'Count' in action_dict:
                        action = 'COUNT'
                    elif 'Captcha' in action_dict:
                        action = 'CAPTCHA'
                    elif 'Challenge' in action_dict:
                        action = 'CHALLENGE'
                except:
                    pass

            # Apply alternating row colors
            highlight = idx % 2 == 0

            row_data = [
                item['web_acl_name'],
                rule.get('name', ''),
                rule.get('priority', ''),
                rule.get('rule_type', ''),
                action
            ]

            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row, column=col_idx)
                self._format_data_cell(cell, value, highlight)

            row += 1

        # Resources section
        row += 2
        ws[f'A{row}'] = 'Protected Resources'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:C{row}')
        row += 1

        # Headers
        headers = ['Web ACL Name', 'Resource Type', 'Resource ARN']
        self._format_header_row(ws, row, headers)
        row += 1

        # Data
        if resources:
            for idx, resource in enumerate(resources):
                highlight = idx % 2 == 0

                row_data = [
                    resource.get('web_acl_name', ''),
                    resource.get('resource_type', ''),
                    resource.get('resource_arn', '')
                ]

                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row, column=col_idx)
                    self._format_data_cell(cell, value, highlight)

                row += 1
        else:
            ws[f'A{row}'] = 'No resources associated with Web ACLs'
            ws[f'A{row}'].font = Font(italic=True, color='808080', name='Calibri')
            ws[f'A{row}'].alignment = Alignment(vertical='center')
            ws.merge_cells(f'A{row}:C{row}')
            row += 1

        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 12

    def create_executive_summary_sheet(self, metrics: Dict[str, Any], web_acls: List[Dict[str, Any]]) -> None:
        """
        Create the Executive Summary sheet with Web ACL information.
        """
        logger.info("Creating Executive Summary sheet...")

        ws = self.workbook.create_sheet("Executive Summary", 0)

        # Title with professional styling
        ws['A1'] = 'AWS WAF Security Analysis - Executive Summary'
        ws['A1'].font = Font(bold=True, size=18, color='1F4E78', name='Calibri')
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells('A1:D1')
        ws.row_dimensions[1].height = 30

        # Subtitle
        ws['A2'] = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        ws['A2'].font = Font(size=10, italic=True, color='808080', name='Calibri')
        ws.merge_cells('A2:D2')

        row = 4

        # Web ACLs Summary Section
        ws[f'A{row}'] = 'Web ACLs Overview'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:D{row}')
        row += 1

        # Web ACL details
        for acl in web_acls:
            acl_name = acl.get('name', acl.get('Name', ''))
            acl_scope = acl.get('scope', acl.get('Scope', ''))
            acl_capacity = acl.get('capacity', acl.get('Capacity', 0))
            default_action = acl.get('default_action', acl.get('DefaultAction', {}))

            if isinstance(default_action, str):
                action_str = default_action
            else:
                action_str = 'ALLOW' if 'Allow' in default_action else 'BLOCK'

            ws[f'A{row}'] = f"• {acl_name}"
            ws[f'A{row}'].font = Font(bold=True, size=11, name='Calibri')
            ws.merge_cells(f'A{row}:D{row}')
            row += 1

            # Format ACL details with borders and consistent styling
            acl_details = [
                ("  Scope:", acl_scope),
                ("  Default Action:", action_str),
                ("  Capacity Used:", f"{acl_capacity} WCU")
            ]

            for label, value in acl_details:
                ws[f'A{row}'] = label
                ws[f'A{row}'].font = self.data_font
                ws[f'A{row}'].border = self.thin_border
                ws[f'B{row}'] = value
                ws[f'B{row}'].font = Font(bold=True, size=10, name='Calibri')
                ws[f'B{row}'].border = self.thin_border
                row += 1

            row += 1  # Extra space between ACLs

        # Summary metrics
        summary = metrics.get('summary', {})
        coverage = metrics.get('web_acl_coverage', {})

        row += 1
        ws[f'A{row}'] = 'Key Security Metrics'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:D{row}')
        row += 1

        key_metrics = [
            ('Total Requests Analyzed', f"{summary.get('total_requests', 0):,}"),
            ('Blocked Requests', f"{summary.get('blocked_requests', 0):,}"),
            ('Block Rate', f"{summary.get('block_rate_percent', 0):.2f}%"),
            ('Unique Client IPs', f"{summary.get('unique_client_ips', 0):,}"),
            ('Unique Countries', f"{summary.get('unique_countries', 0):,}"),
            ('Web ACLs Configured', coverage.get('total_web_acls', 0)),
            ('Protected Resources', coverage.get('total_protected_resources', 0)),
            ('Logging Coverage', f"{coverage.get('logging_coverage_percent', 0):.1f}%")
        ]

        for idx, (metric_name, metric_value) in enumerate(key_metrics):
            highlight = idx % 2 == 0

            ws[f'A{row}'] = metric_name
            ws[f'A{row}'].font = Font(bold=True, size=10, name='Calibri')
            ws[f'A{row}'].border = self.thin_border
            ws[f'A{row}'].fill = self.highlight_fill if highlight else None

            ws[f'B{row}'] = metric_value
            ws[f'B{row}'].font = Font(bold=True, size=11, color='1F4E78', name='Calibri')
            ws[f'B{row}'].border = self.thin_border
            ws[f'B{row}'].fill = self.highlight_fill if highlight else None
            ws[f'B{row}'].alignment = Alignment(horizontal='right', vertical='center')

            row += 1

        # Time range
        row += 1
        ws[f'A{row}'] = 'Analysis Period'
        ws[f'A{row}'].font = self.subtitle_font
        ws.merge_cells(f'A{row}:D{row}')
        row += 1

        time_range = summary.get('time_range')
        if time_range:
            time_data = [
                ('Start Date', str(time_range.get('start', ''))[:19]),
                ('End Date', str(time_range.get('end', ''))[:19])
            ]

            for label, value in time_data:
                ws[f'A{row}'] = label
                ws[f'A{row}'].font = Font(bold=True, size=10, name='Calibri')
                ws[f'A{row}'].border = self.thin_border
                ws[f'B{row}'] = value
                ws[f'B{row}'].font = self.data_font
                ws[f'B{row}'].border = self.thin_border
                row += 1

        # Security Posture Score
        security_score = coverage.get('security_posture_score', 0)
        if security_score:
            row += 1
            ws[f'A{row}'] = 'Security Posture Score'
            ws[f'A{row}'].font = self.subtitle_font
            ws.merge_cells(f'A{row}:D{row}')
            row += 1

            ws[f'A{row}'] = 'Overall Score'
            ws[f'A{row}'].font = Font(bold=True, size=10, name='Calibri')
            ws[f'A{row}'].border = self.thin_border

            ws[f'B{row}'] = f"{security_score}/100"
            ws[f'B{row}'].border = self.thin_border
            ws[f'B{row}'].alignment = Alignment(horizontal='right', vertical='center')

            # Color code the score with appropriate fill
            if security_score >= 80:
                ws[f'B{row}'].font = Font(bold=True, size=14, color='008000', name='Calibri')  # Green
                ws[f'B{row}'].fill = self.success_fill
            elif security_score >= 60:
                ws[f'B{row}'].font = Font(bold=True, size=14, color='FF8C00', name='Calibri')  # Orange
                ws[f'B{row}'].fill = self.warning_fill
            else:
                ws[f'B{row}'].font = Font(bold=True, size=14, color='FF0000', name='Calibri')  # Red
                ws[f'B{row}'].fill = self.danger_fill
            row += 1

        # Action distribution chart
        row += 2
        action_dist = metrics.get('action_distribution', {})
        if action_dist:
            try:
                chart_buffer = self.viz.create_action_distribution_chart(action_dist)
                img = XLImage(chart_buffer)
                img.width = 600
                img.height = 400
                ws.add_image(img, f'A{row}')
            except Exception as e:
                logger.warning(f"Could not create action distribution chart: {e}")

        # Auto-adjust columns
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 25

    def create_traffic_analysis_sheet(self, metrics: Dict[str, Any]) -> None:
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

    def create_rule_effectiveness_sheet(self, metrics: Dict[str, Any]) -> None:
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

    def create_client_analysis_sheet(self, metrics: Dict[str, Any]) -> None:
        """
        Create the Client Analysis sheet.
        """
        logger.info("Creating Client Analysis sheet...")

        ws = self.workbook.create_sheet("Client Analysis")

        # Title with professional styling
        ws['A1'] = 'Client and Bot Analysis'
        ws['A1'].font = Font(bold=True, size=18, color='1F4E78', name='Calibri')
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells('A1:F1')
        ws.row_dimensions[1].height = 30

        # Subtitle
        ws['A2'] = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        ws['A2'].font = Font(size=10, italic=True, color='808080', name='Calibri')
        ws.merge_cells('A2:F2')

        row = 4

        # Top blocked IPs
        top_ips = metrics.get('top_blocked_ips', [])
        if top_ips:
            ws[f'A{row}'] = 'Top Blocked IP Addresses'
            ws[f'A{row}'].font = self.subtitle_font
            ws.merge_cells(f'A{row}:F{row}')
            row += 1

            # Headers
            headers = ['IP Address', 'Country', 'Block Count', 'Unique Rules Hit', 'First Seen', 'Last Seen']
            self._format_header_row(ws, row, headers)
            row += 1

            # Data
            for idx, ip_data in enumerate(top_ips[:30]):  # Top 30
                highlight = idx % 2 == 0

                row_data = [
                    ip_data.get('ip', ''),
                    ip_data.get('country', ''),
                    ip_data.get('block_count', 0),
                    ip_data.get('unique_rules_hit', 0),
                    str(ip_data.get('first_seen', ''))[:19],
                    str(ip_data.get('last_seen', ''))[:19]
                ]

                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row, column=col_idx)
                    self._format_data_cell(cell, value, highlight)

                row += 1

        # Bot analysis
        row += 2
        bot_analysis = metrics.get('bot_analysis', {})
        if bot_analysis:
            ws[f'A{row}'] = 'Bot Traffic Analysis'
            ws[f'A{row}'].font = self.subtitle_font
            ws.merge_cells(f'A{row}:F{row}')
            row += 1

            # Bot metrics with professional styling
            bot_metrics = [
                ('Requests with JA3 Fingerprint', bot_analysis.get('requests_with_ja3', 0)),
                ('Requests with JA4 Fingerprint', bot_analysis.get('requests_with_ja4', 0))
            ]

            for idx, (label, value) in enumerate(bot_metrics):
                highlight = idx % 2 == 0
                ws[f'A{row}'] = label
                ws[f'A{row}'].font = Font(bold=True, size=10, name='Calibri')
                ws[f'A{row}'].border = self.thin_border
                ws[f'A{row}'].fill = self.highlight_fill if highlight else None

                ws[f'B{row}'] = value
                ws[f'B{row}'].font = self.data_font
                ws[f'B{row}'].border = self.thin_border
                ws[f'B{row}'].fill = self.highlight_fill if highlight else None
                row += 1

            row += 1

            # Top user agents
            top_agents = bot_analysis.get('top_user_agents', [])
            if top_agents:
                ws[f'A{row}'] = 'Top User Agents'
                ws[f'A{row}'].font = Font(bold=True, size=11, name='Calibri')
                ws.merge_cells(f'A{row}:B{row}')
                row += 1

                # Headers
                headers = ['User Agent', 'Request Count']
                self._format_header_row(ws, row, headers, start_col=1)
                row += 1

                for idx, agent_data in enumerate(top_agents[:15]):
                    highlight = idx % 2 == 0
                    row_data = [
                        agent_data.get('user_agent', '')[:100],
                        agent_data.get('count', 0)
                    ]

                    for col_idx, value in enumerate(row_data, start=1):
                        cell = ws.cell(row=row, column=col_idx)
                        self._format_data_cell(cell, value, highlight)

                    row += 1

        # Hourly patterns
        hourly_data = metrics.get('hourly_patterns', [])
        if hourly_data:
            row += 2
            try:
                chart_buffer = self.viz.create_hourly_pattern_chart(hourly_data)
                img = XLImage(chart_buffer)
                img.width = 800
                img.height = 400
                ws.add_image(img, f'A{row}')
            except Exception as e:
                logger.warning(f"Could not create hourly pattern chart: {e}")

        # Auto-adjust columns
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 20
        for col in ['C', 'D', 'E', 'F']:
            ws.column_dimensions[col].width = 18

    def create_llm_recommendations_sheet(self) -> None:
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

    def save(self) -> None:
        """
        Save the Excel workbook.
        """
        try:
            self.workbook.save(self.output_path)
            logger.info(f"Excel report saved: {self.output_path}")
        except Exception as e:
            logger.error(f"Error saving Excel report: {e}")
            raise
