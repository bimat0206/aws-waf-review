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

        # Styling
        self.header_font = Font(bold=True, size=12, color='FFFFFF')
        self.header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        self.title_font = Font(bold=True, size=14)

        logger.info(f"Excel report generator initialized: {output_path}")

    def generate_report(self, metrics: Dict[str, Any], web_acls: List[Dict[str, Any]],
                       resources: List[Dict[str, Any]], logging_configs: List[Dict[str, Any]]) -> None:
        """
        Generate the complete Excel report.

        Args:
            metrics (Dict[str, Any]): Calculated metrics
            web_acls (List[Dict[str, Any]]): Web ACL configurations
            resources (List[Dict[str, Any]]): Resource associations
            logging_configs (List[Dict[str, Any]]): Logging configurations
        """
        logger.info("Generating Excel report...")

        # Create all sheets
        self.create_inventory_sheet(web_acls, resources, logging_configs)
        self.create_executive_summary_sheet(metrics)
        self.create_traffic_analysis_sheet(metrics)
        self.create_rule_effectiveness_sheet(metrics)
        self.create_client_analysis_sheet(metrics)
        self.create_llm_recommendations_sheet()

        # Save the workbook
        self.save()

        logger.info(f"Excel report generated successfully: {self.output_path}")

    def create_inventory_sheet(self, web_acls: List[Dict[str, Any]],
                               resources: List[Dict[str, Any]],
                               logging_configs: List[Dict[str, Any]]) -> None:
        """
        Create the Inventory sheet.
        """
        logger.info("Creating Inventory sheet...")

        ws = self.workbook.create_sheet("Inventory")

        # Title
        ws['A1'] = 'AWS WAF Inventory'
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:F1')

        # Web ACLs section
        row = 3
        ws[f'A{row}'] = 'Web ACLs'
        ws[f'A{row}'].font = self.title_font
        row += 1

        # Headers
        headers = ['Name', 'ID', 'Scope', 'Default Action', 'Capacity', 'Logging Enabled']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center')

        row += 1

        # Data
        logging_config_ids = {lc.get('web_acl_id') for lc in logging_configs if lc.get('web_acl_id')}

        for acl in web_acls:
            ws[f'A{row}'] = acl.get('Name', '')
            ws[f'B{row}'] = acl.get('Id', '')
            ws[f'C{row}'] = acl.get('Scope', '')

            default_action = acl.get('DefaultAction', {})
            action_str = 'ALLOW' if 'Allow' in default_action else 'BLOCK'
            ws[f'D{row}'] = action_str

            ws[f'E{row}'] = acl.get('Capacity', 0)

            acl_id = acl.get('Id', '')
            logging_enabled = 'Yes' if acl_id in logging_config_ids else 'No'
            ws[f'F{row}'] = logging_enabled

            # Color code logging status
            if logging_enabled == 'No':
                ws[f'F{row}'].fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            else:
                ws[f'F{row}'].fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')

            row += 1

        # Resources section
        row += 2
        ws[f'A{row}'] = 'Protected Resources'
        ws[f'A{row}'].font = self.title_font
        row += 1

        # Headers
        headers = ['Web ACL Name', 'Resource Type', 'Resource ARN']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center')

        row += 1

        # Data
        for resource in resources:
            ws[f'A{row}'] = resource.get('web_acl_name', '')
            ws[f'B{row}'] = resource.get('resource_type', '')
            ws[f'C{row}'] = resource.get('resource_arn', '')
            row += 1

        # Auto-adjust column widths
        for col in ['A', 'B', 'C', 'D', 'E', 'F']:
            ws.column_dimensions[col].width = 20

        ws.column_dimensions['C'].width = 50

    def create_executive_summary_sheet(self, metrics: Dict[str, Any]) -> None:
        """
        Create the Executive Summary sheet.
        """
        logger.info("Creating Executive Summary sheet...")

        ws = self.workbook.create_sheet("Executive Summary", 0)

        # Title
        ws['A1'] = 'AWS WAF Security Analysis - Executive Summary'
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:D1')

        # Summary metrics
        summary = metrics.get('summary', {})
        coverage = metrics.get('web_acl_coverage', {})

        row = 3

        # Key metrics
        ws[f'A{row}'] = 'Key Metrics'
        ws[f'A{row}'].font = self.title_font
        row += 1

        key_metrics = [
            ('Total Requests Analyzed', summary.get('total_requests', 0)),
            ('Blocked Requests', summary.get('blocked_requests', 0)),
            ('Block Rate', f"{summary.get('block_rate_percent', 0)}%"),
            ('Unique Client IPs', summary.get('unique_client_ips', 0)),
            ('Unique Countries', summary.get('unique_countries', 0)),
            ('Web ACLs Configured', coverage.get('total_web_acls', 0)),
            ('Protected Resources', coverage.get('total_protected_resources', 0)),
            ('Logging Coverage', f"{coverage.get('logging_coverage_percent', 0)}%")
        ]

        for metric_name, metric_value in key_metrics:
            ws[f'A{row}'] = metric_name
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = metric_value
            row += 1

        # Time range
        row += 1
        ws[f'A{row}'] = 'Analysis Period'
        ws[f'A{row}'].font = self.title_font
        row += 1

        time_range = summary.get('time_range')
        if time_range:
            ws[f'A{row}'] = 'Start Date'
            ws[f'B{row}'] = str(time_range.get('start', ''))
            row += 1
            ws[f'A{row}'] = 'End Date'
            ws[f'B{row}'] = str(time_range.get('end', ''))
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
        ws.column_dimensions['B'].width = 20

    def create_traffic_analysis_sheet(self, metrics: Dict[str, Any]) -> None:
        """
        Create the Traffic Analysis sheet.
        """
        logger.info("Creating Traffic Analysis sheet...")

        ws = self.workbook.create_sheet("Traffic Analysis")

        # Title
        ws['A1'] = 'Traffic Analysis'
        ws['A1'].font = Font(bold=True, size=16)

        row = 3

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
            ws[f'A{row}'].font = self.title_font
            row += 1

            # Create table
            headers = ['Country', 'Total Requests', 'Blocked', 'Allowed', 'Threat Score']
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.font = self.header_font
                cell.fill = self.header_fill

            row += 1

            for country_data in geo_data[:20]:  # Top 20
                ws[f'A{row}'] = country_data.get('country', '')
                ws[f'B{row}'] = country_data.get('total_requests', 0)
                ws[f'C{row}'] = country_data.get('blocked_requests', 0)
                ws[f'D{row}'] = country_data.get('allowed_requests', 0)
                ws[f'E{row}'] = f"{country_data.get('threat_score', 0)}%"

                # Color code threat score
                threat_score = country_data.get('threat_score', 0)
                if threat_score > 50:
                    ws[f'E{row}'].fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                elif threat_score > 25:
                    ws[f'E{row}'].fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')

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

        # Title
        ws['A1'] = 'Rule Effectiveness Analysis'
        ws['A1'].font = Font(bold=True, size=16)

        row = 3

        # Rule effectiveness table
        rule_data = metrics.get('rule_effectiveness', [])
        if rule_data:
            # Headers
            headers = ['Rule ID', 'Rule Type', 'Hit Count', 'Blocks', 'Allows', 'Hit Rate %', 'Block Rate %']
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.font = self.header_font
                cell.fill = self.header_fill
                cell.alignment = Alignment(horizontal='center')

            row += 1

            # Data
            for rule in rule_data:
                ws[f'A{row}'] = rule.get('rule_id', '')[:50]
                ws[f'B{row}'] = rule.get('rule_type', '')
                ws[f'C{row}'] = rule.get('hit_count', 0)
                ws[f'D{row}'] = rule.get('blocks', 0)
                ws[f'E{row}'] = rule.get('allows', 0)
                ws[f'F{row}'] = rule.get('hit_rate_percent', 0)
                ws[f'G{row}'] = rule.get('block_rate_percent', 0)

                # Color code hit rate
                hit_rate = rule.get('hit_rate_percent', 0)
                if hit_rate == 0:
                    ws[f'F{row}'].fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                elif hit_rate > 10:
                    ws[f'F{row}'].fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')

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
            ws[f'A{row}'].font = self.title_font
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

        # Title
        ws['A1'] = 'Client and Bot Analysis'
        ws['A1'].font = Font(bold=True, size=16)

        row = 3

        # Top blocked IPs
        top_ips = metrics.get('top_blocked_ips', [])
        if top_ips:
            ws[f'A{row}'] = 'Top Blocked IP Addresses'
            ws[f'A{row}'].font = self.title_font
            row += 1

            # Headers
            headers = ['IP Address', 'Country', 'Block Count', 'Unique Rules Hit', 'First Seen', 'Last Seen']
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.font = self.header_font
                cell.fill = self.header_fill

            row += 1

            # Data
            for ip_data in top_ips[:30]:  # Top 30
                ws[f'A{row}'] = ip_data.get('ip', '')
                ws[f'B{row}'] = ip_data.get('country', '')
                ws[f'C{row}'] = ip_data.get('block_count', 0)
                ws[f'D{row}'] = ip_data.get('unique_rules_hit', 0)
                ws[f'E{row}'] = str(ip_data.get('first_seen', ''))
                ws[f'F{row}'] = str(ip_data.get('last_seen', ''))
                row += 1

        # Bot analysis
        row += 2
        bot_analysis = metrics.get('bot_analysis', {})
        if bot_analysis:
            ws[f'A{row}'] = 'Bot Traffic Analysis'
            ws[f'A{row}'].font = self.title_font
            row += 1

            ws[f'A{row}'] = 'Requests with JA3 Fingerprint'
            ws[f'B{row}'] = bot_analysis.get('requests_with_ja3', 0)
            row += 1

            ws[f'A{row}'] = 'Requests with JA4 Fingerprint'
            ws[f'B{row}'] = bot_analysis.get('requests_with_ja4', 0)
            row += 2

            # Top user agents
            top_agents = bot_analysis.get('top_user_agents', [])
            if top_agents:
                ws[f'A{row}'] = 'Top User Agents'
                ws[f'A{row}'].font = Font(bold=True)
                row += 1

                for agent_data in top_agents[:15]:
                    ws[f'A{row}'] = agent_data.get('user_agent', '')[:100]
                    ws[f'B{row}'] = agent_data.get('count', 0)
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

        # Title
        ws['A1'] = 'AI-Generated Security Recommendations'
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:D1')

        row = 3

        # Instructions
        ws[f'A{row}'] = 'Instructions:'
        ws[f'A{row}'].font = Font(bold=True, italic=True)
        row += 1

        instructions = [
            '1. Use the LLM prompt templates in config/prompts/ with the metrics from this report',
            '2. Populate the sections below with AI-generated findings and recommendations',
            '3. Review and validate all AI recommendations before implementation',
            '4. Prioritize actions based on your organization\'s risk tolerance and requirements'
        ]

        for instruction in instructions:
            ws[f'A{row}'] = instruction
            ws[f'A{row}'].font = Font(italic=True)
            row += 1

        # Sections
        sections = [
            ('Critical Findings', 'Immediate action required'),
            ('High Priority Recommendations', 'Implement within 30 days'),
            ('Medium Priority Optimizations', 'Implement within 90 days'),
            ('Low Priority Suggestions', 'Nice to have improvements')
        ]

        for section_title, section_desc in sections:
            row += 2
            ws[f'A{row}'] = section_title
            ws[f'A{row}'].font = self.title_font
            ws[f'A{row}'].fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')
            ws.merge_cells(f'A{row}:D{row}')
            row += 1

            ws[f'A{row}'] = section_desc
            ws[f'A{row}'].font = Font(italic=True, size=10)
            row += 1

            # Template rows
            headers = ['Priority', 'Finding/Recommendation', 'Impact', 'Action Items']
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.font = self.header_font
                cell.fill = self.header_fill

            row += 1

            # Add 3 empty rows for each section
            for _ in range(3):
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
