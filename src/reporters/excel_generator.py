"""
Excel Report Generator

This module generates comprehensive multi-sheet Excel reports with visualizations
for AWS WAF analysis results.
"""

import logging
from typing import Any, Dict, List, Optional
from openpyxl import Workbook

from .visualization_helpers import VisualizationHelpers
from .sheets import (
    ClientAnalysisSheet,
    ExecutiveSummarySheet,
    GeographicBlockedTrafficSheet,
    InventorySheet,
    LLMRecommendationsSheet,
    RuleActionDistributionSheet,
    RuleEffectivenessSheet,
    TrafficAnalysisSheet,
)

logger = logging.getLogger(__name__)


class ExcelReportGenerator:
    """Generates comprehensive Excel reports for WAF analysis."""

    def __init__(self, output_path: str):
        """Initialize the Excel report generator."""
        self.output_path = output_path
        self.workbook = Workbook()
        if 'Sheet' in self.workbook.sheetnames:
            del self.workbook['Sheet']

        self.viz = VisualizationHelpers()
        logger.info(f"Excel report generator initialized: {output_path}")

    def _init_sheet(self, sheet_cls):
        """Instantiate a sheet helper with shared visualization utilities."""
        sheet = sheet_cls(self.workbook)
        sheet.viz = self.viz
        return sheet

    def generate_report(
        self,
        metrics: Dict[str, Any],
        web_acls: List[Dict[str, Any]],
        resources: List[Dict[str, Any]],
        logging_configs: List[Dict[str, Any]],
        rules_by_web_acl: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        account_info: Optional[Dict[str, Any]] = None,
        llm_analysis: Optional[Dict[str, Any]] = None,
        llm_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate the complete Excel report."""
        logger.info("Generating Excel report...")

        if rules_by_web_acl is None:
            rules_by_web_acl = {}

        self._init_sheet(ExecutiveSummarySheet).build(metrics, web_acls, account_info)
        self._init_sheet(InventorySheet).build(
            web_acls, resources, logging_configs, rules_by_web_acl
        )
        self._init_sheet(TrafficAnalysisSheet).build(metrics)
        self._init_sheet(RuleEffectivenessSheet).build(metrics)
        self._init_sheet(GeographicBlockedTrafficSheet).build(metrics)
        self._init_sheet(RuleActionDistributionSheet).build(metrics)
        self._init_sheet(ClientAnalysisSheet).build(metrics)
        self._init_sheet(LLMRecommendationsSheet).build(llm_analysis, llm_metadata)

        self.save()

    def save(self) -> None:
        """Save the Excel workbook."""
        try:
            self.workbook.save(self.output_path)
            logger.info(f"Excel report saved: {self.output_path}")
        except Exception as exc:
            logger.error(f"Error saving Excel report: {exc}")
            raise
