"""
LLM Response Parser

Parses LLM markdown responses into structured data for Excel sheet population.
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parses LLM responses into structured recommendations."""

    def parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM markdown response into structured data.

        Args:
            response_text: Raw LLM response (markdown format)

        Returns:
            Dict containing parsed sections:
                - executive_summary
                - critical_findings
                - high_priority
                - medium_priority
                - low_priority (if present)
                - rule_analysis
                - false_positives
                - threat_intelligence
                - compliance
                - cost_optimization
                - roadmap
        """
        if not response_text:
            logger.warning("Empty response text")
            return self._empty_response()

        try:
            logger.info(f"Parsing response ({len(response_text):,} characters)...")

            parsed = {
                'raw_response': response_text,
                'executive_summary': self._parse_executive_summary(response_text),
                'critical_findings': self._parse_findings_section(response_text, 'Critical'),
                'high_priority': self._parse_findings_section(response_text, 'High Priority'),  # Mid/Long-Term
                'medium_priority': [],  # No longer used - merged into high_priority
                'low_priority': self._parse_findings_section(response_text, 'Low Priority'),
                'rule_analysis': self._parse_table_section(response_text, 'Rule Effectiveness'),
                'false_positives': self._parse_table_section(response_text, 'False Positive'),
                'threat_intelligence': self._parse_threat_section(response_text),
                'compliance': self._parse_compliance_section(response_text),
                'cost_optimization': self._parse_cost_section(response_text),
                'roadmap': self._parse_roadmap(response_text)
            }

            logger.info("Response parsing completed")
            return parsed

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return self._empty_response()

    def _parse_executive_summary(self, text: str) -> Dict[str, Any]:
        """Parse executive summary section."""
        summary = {
            'security_posture': 'Medium',
            'assessment_breakdown': {},
            'assessment': '',
            'critical_count': 0,
            'mid_long_term_count': 0,
            'low_priority_count': 0
        }

        try:
            # Extract security posture assessment (High/Medium/Low)
            posture_match = re.search(r'\*\*Security Posture Assessment:\*\*\s*(High|Medium|Low)', text, re.IGNORECASE)
            if posture_match:
                summary['security_posture'] = posture_match.group(1).strip()

            # Extract assessment breakdown
            breakdown_section = re.search(
                r'\*\*Assessment Breakdown:\*\*\s*\n(.*?)(?:\n\n|\*\*Overall)',
                text,
                re.DOTALL
            )
            if breakdown_section:
                breakdown_text = breakdown_section.group(1)

                # Parse each breakdown item
                rule_coverage = re.search(r'Rule Coverage:\s*(High|Medium|Low)', breakdown_text, re.IGNORECASE)
                if rule_coverage:
                    summary['assessment_breakdown']['rule_coverage'] = rule_coverage.group(1).strip()

                threat_detection = re.search(r'Threat Detection:\s*(High|Medium|Low)', breakdown_text, re.IGNORECASE)
                if threat_detection:
                    summary['assessment_breakdown']['threat_detection'] = threat_detection.group(1).strip()

                logging_monitoring = re.search(r'Logging & Monitoring:\s*(High|Medium|Low)', breakdown_text, re.IGNORECASE)
                if logging_monitoring:
                    summary['assessment_breakdown']['logging_monitoring'] = logging_monitoring.group(1).strip()

                config_security = re.search(r'Configuration Security:\s*(High|Medium|Low)', breakdown_text, re.IGNORECASE)
                if config_security:
                    summary['assessment_breakdown']['configuration_security'] = config_security.group(1).strip()

                response_readiness = re.search(r'Response Readiness:\s*(High|Medium|Low)', breakdown_text, re.IGNORECASE)
                if response_readiness:
                    summary['assessment_breakdown']['response_readiness'] = response_readiness.group(1).strip()

            # Extract overall assessment
            assessment_match = re.search(
                r'\*\*Overall Assessment:\*\*\s*(.+?)(?:\n\n|\*\*|---)',
                text,
                re.DOTALL
            )
            if assessment_match:
                summary['assessment'] = assessment_match.group(1).strip()

            # Count findings in tables
            critical_table = re.search(r'\*\*Critical Findings.*?\n\|.*?\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)', text, re.DOTALL)
            if critical_table:
                summary['critical_count'] = len(critical_table.group(1).strip().split('\n'))

            midlong_table = re.search(r'\*\*Mid/Long-Term Recommendations.*?\n\|.*?\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)', text, re.DOTALL)
            if midlong_table:
                summary['mid_long_term_count'] = len(midlong_table.group(1).strip().split('\n'))

            low_table = re.search(r'\*\*Low Priority Suggestions.*?\n\|.*?\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)', text, re.DOTALL)
            if low_table:
                summary['low_priority_count'] = len(low_table.group(1).strip().split('\n'))

        except Exception as e:
            logger.warning(f"Error parsing executive summary: {e}")

        return summary

    def _parse_findings_section(
        self,
        text: str,
        priority: str
    ) -> List[Dict[str, str]]:
        """Parse findings section from table format (Critical, Mid/Long-Term, Low Priority)."""
        findings = []

        try:
            # Find section by priority level
            if priority == 'Critical':
                pattern = r'\*\*Critical Findings.*?\n\|.*?\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)'
            elif priority == 'High Priority':
                # This is now "Mid/Long-Term Recommendations"
                pattern = r'\*\*Mid/Long-Term Recommendations.*?\n\|.*?\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)'
            elif priority == 'Medium':
                # Medium priority is now part of Mid/Long-Term, return empty
                return findings
            else:
                # Low Priority
                pattern = r'\*\*Low Priority Suggestions.*?\n\|.*?\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)'

            section_match = re.search(pattern, text, re.DOTALL)
            if not section_match:
                return findings

            # Parse table rows
            rows_text = section_match.group(1)

            for row_text in rows_text.strip().split('\n'):
                # Split by | and filter out empty strings
                cells = [cell.strip() for cell in row_text.split('|') if cell.strip()]

                if len(cells) >= 5:
                    # Table format: No | Finding | Expected Impact | Action Items | Rationale
                    finding = {
                        'number': cells[0],
                        'title': cells[1],
                        'finding': cells[1],  # Alias for compatibility
                        'impact': cells[2],
                        'expected_impact': cells[2],  # Alias for compatibility
                        'actions': self._parse_action_items(cells[3]),  # Parse bullet list
                        'action': cells[3],  # Raw text for compatibility
                        'rationale': cells[4],
                        'reason': cells[4],  # Alias for compatibility
                        'priority': priority
                    }

                    findings.append(finding)

        except Exception as e:
            logger.warning(f"Error parsing {priority} findings: {e}")

        return findings

    def _parse_action_items(self, action_text: str) -> List[str]:
        """Parse action items from bullet list format."""
        actions = []

        try:
            # Handle <br> separated items
            if '<br>' in action_text:
                items = action_text.split('<br>')
            else:
                # Handle newline separated items
                items = action_text.split('\n')

            for item in items:
                # Remove bullet points and trim
                cleaned = item.strip().lstrip('•').lstrip('-').lstrip('*').strip()
                if cleaned:
                    actions.append(cleaned)

        except Exception as e:
            logger.warning(f"Error parsing action items: {e}")

        return actions if actions else [action_text]

    def _parse_table_section(self, text: str, section_name: str) -> List[Dict[str, str]]:
        """Parse markdown tables from sections."""
        tables = []

        try:
            # Find tables in section
            section_pattern = f'{section_name}.*?(?=###|Section \d+:|$)'
            section_match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)

            if not section_match:
                return tables

            section_text = section_match.group(0)

            # Find markdown tables
            table_pattern = r'\|(.+?)\|\n\|[-:|\s]+\|\n((?:\|.+?\|\n)+)'
            table_matches = re.finditer(table_pattern, section_text)

            for table_match in table_matches:
                headers = [h.strip() for h in table_match.group(1).split('|') if h.strip()]
                rows_text = table_match.group(2)

                for row_text in rows_text.strip().split('\n'):
                    values = [v.strip() for v in row_text.split('|') if v.strip()]
                    if values:
                        row_dict = dict(zip(headers, values))
                        tables.append(row_dict)

        except Exception as e:
            logger.warning(f"Error parsing table in {section_name}: {e}")

        return tables

    def _parse_threat_section(self, text: str) -> Dict[str, Any]:
        """Parse threat intelligence section."""
        threats = {
            'attack_vectors': [],
            'persistent_threats': [],
            'bot_assessment': '',
            'recommended_rules': []
        }

        try:
            # This is a simplified parser - can be enhanced based on actual response format
            threat_match = re.search(
                r'Threat Intelligence.*?(?=###|Section \d+:|$)',
                text,
                re.DOTALL | re.IGNORECASE
            )

            if threat_match:
                threat_text = threat_match.group(0)

                # Extract bot assessment
                bot_match = re.search(r'Bot Traffic Assessment:.*?Recommendation:\s*(.+?)(?:\n\n|\*\*)', threat_text, re.DOTALL)
                if bot_match:
                    threats['bot_assessment'] = bot_match.group(1).strip()

                # Extract tables
                threats['attack_vectors'] = self._parse_table_section(threat_text, 'Attack Vectors')
                threats['recommended_rules'] = self._parse_table_section(threat_text, 'Recommended')

        except Exception as e:
            logger.warning(f"Error parsing threat section: {e}")

        return threats

    def _parse_compliance_section(self, text: str) -> Dict[str, Any]:
        """Parse compliance section."""
        compliance = {
            'owasp_coverage': [],
            'pci_dss_status': '',
            'gaps': []
        }

        try:
            compliance_match = re.search(
                r'Compliance.*?(?=###|Section \d+:|$)',
                text,
                re.DOTALL | re.IGNORECASE
            )

            if compliance_match:
                compliance_text = compliance_match.group(0)

                # Extract PCI-DSS status
                pci_match = re.search(r'PCI-DSS.*?Status.*?:\*\*\s*(.+?)(?:\n|\*\*)', compliance_text)
                if pci_match:
                    compliance['pci_dss_status'] = pci_match.group(1).strip()

                # Extract OWASP table
                compliance['owasp_coverage'] = self._parse_table_section(compliance_text, 'OWASP')

        except Exception as e:
            logger.warning(f"Error parsing compliance section: {e}")

        return compliance

    def _parse_cost_section(self, text: str) -> Dict[str, Any]:
        """Parse cost optimization section."""
        cost = {
            'current_cost': '',
            'potential_savings': '',
            'opportunities': []
        }

        try:
            cost_match = re.search(
                r'Cost Optimization.*?(?=###|Section \d+:|$)',
                text,
                re.DOTALL | re.IGNORECASE
            )

            if cost_match:
                cost_text = cost_match.group(0)

                # Extract current cost
                current_match = re.search(r'Current.*?Cost.*?\$([0-9,.]+)', cost_text)
                if current_match:
                    cost['current_cost'] = current_match.group(1)

                # Extract savings
                savings_match = re.search(r'Savings.*?\$([0-9,.]+)', cost_text)
                if savings_match:
                    cost['potential_savings'] = savings_match.group(1)

        except Exception as e:
            logger.warning(f"Error parsing cost section: {e}")

        return cost

    def _parse_roadmap(self, text: str) -> Dict[str, List[str]]:
        """Parse implementation roadmap."""
        roadmap = {
            'week_1': [],
            'month_1': [],
            'quarter_1': [],
            'ongoing': []
        }

        try:
            roadmap_match = re.search(
                r'Implementation Roadmap.*?(?=###|Section \d+:|$)',
                text,
                re.DOTALL | re.IGNORECASE
            )

            if roadmap_match:
                roadmap_text = roadmap_match.group(0)

                # Extract checkbox items for each timeframe
                week_items = re.findall(r'Week 1.*?\n((?:- \[.\].+?\n)+)', roadmap_text, re.DOTALL)
                if week_items:
                    roadmap['week_1'] = [item.strip('- []') for item in week_items[0].strip().split('\n')]

                month_items = re.findall(r'Month 1.*?\n((?:- \[.\].+?\n)+)', roadmap_text, re.DOTALL)
                if month_items:
                    roadmap['month_1'] = [item.strip('- []') for item in month_items[0].strip().split('\n')]

        except Exception as e:
            logger.warning(f"Error parsing roadmap: {e}")

        return roadmap

    def parse_sheet_findings(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse sheet-specific findings from LLM response.

        Expects format:
        FINDING 1:
        Finding: [description]
        Severity: [HIGH/MEDIUM/LOW]
        Recommendation: [recommendation text]

        Args:
            response: LLM response text

        Returns:
            List of finding dictionaries
        """
        findings = []

        try:
            # Split by FINDING markers
            finding_blocks = re.split(r'FINDING \d+:', response)

            for block in finding_blocks[1:]:  # Skip first empty element
                finding_dict = {}

                # Extract Finding
                finding_match = re.search(r'Finding:\s*(.+?)(?=Severity:|$)', block, re.DOTALL)
                if finding_match:
                    finding_dict['finding'] = finding_match.group(1).strip()

                # Extract Severity
                severity_match = re.search(r'Severity:\s*(HIGH|MEDIUM|LOW)', block, re.IGNORECASE)
                if severity_match:
                    finding_dict['severity'] = severity_match.group(1).upper()
                else:
                    finding_dict['severity'] = 'MEDIUM'  # Default

                # Extract Recommendation
                rec_match = re.search(r'Recommendation:\s*(.+?)(?=FINDING \d+:|$)', block, re.DOTALL)
                if rec_match:
                    finding_dict['recommendation'] = rec_match.group(1).strip()

                if finding_dict.get('finding'):
                    findings.append(finding_dict)

        except Exception as e:
            logger.error(f"Error parsing sheet findings: {e}")

        logger.info(f"Parsed {len(findings)} sheet findings")
        return findings

    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response structure."""
        return {
            'raw_response': '',
            'executive_summary': {},
            'critical_findings': [],
            'high_priority': [],
            'medium_priority': [],
            'rule_analysis': [],
            'false_positives': [],
            'threat_intelligence': {},
            'compliance': {},
            'cost_optimization': {},
            'roadmap': {}
        }
