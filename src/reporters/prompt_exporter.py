"""
Prompt Exporter

This module exports LLM prompt templates filled with WAF analysis data.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class PromptExporter:
    """
    Exports LLM prompts with WAF data injected into templates.
    """

    def __init__(self, template_dir: str = "config/prompts", export_dir: str = None):
        """
        Initialize the prompt exporter.

        Args:
            template_dir (str): Directory containing prompt templates
            export_dir (str): Directory to export filled prompts
        """
        self.template_dir = Path(template_dir)
        self.export_dir = Path(export_dir) if export_dir else None

        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {template_dir}")

        logger.info(f"Prompt exporter initialized")

    def export_all_prompts(self, metrics: Dict[str, Any], web_acls: List[Dict[str, Any]],
                          resources: List[Dict[str, Any]], rules_by_web_acl: Dict[str, List[Dict[str, Any]]],
                          export_dir: str) -> int:
        """
        Export all prompt templates with injected WAF data.

        Args:
            metrics (Dict[str, Any]): Calculated metrics
            web_acls (List[Dict[str, Any]]): Web ACL configurations
            resources (List[Dict[str, Any]]): Resource associations
            rules_by_web_acl (Dict[str, List[Dict[str, Any]]]): Rules grouped by Web ACL
            export_dir (str): Directory to export prompts

        Returns:
            int: Number of prompts exported
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting prompts to: {export_dir}")

        # Prepare data for injection
        data = self._prepare_data(metrics, web_acls, resources, rules_by_web_acl)

        # Export each template
        exported_count = 0
        templates = list(self.template_dir.glob("*.md"))

        if not templates:
            logger.warning(f"No prompt templates found in {self.template_dir}")
            return 0

        for template_path in templates:
            try:
                self._export_prompt(template_path, data)
                exported_count += 1
            except Exception as e:
                logger.error(f"Failed to export {template_path.name}: {e}")

        logger.info(f"Exported {exported_count} prompts successfully")
        return exported_count

    def _prepare_data(self, metrics: Dict[str, Any], web_acls: List[Dict[str, Any]],
                     resources: List[Dict[str, Any]], rules_by_web_acl: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Prepare WAF data for injection into templates.
        """
        summary = metrics.get('summary', {})
        coverage = metrics.get('web_acl_coverage', {})
        rule_effectiveness = metrics.get('rule_effectiveness', [])
        geo_dist = metrics.get('geographic_distribution', [])
        top_ips = metrics.get('top_blocked_ips', [])

        # Format Web ACLs info
        web_acls_summary = []
        for acl in web_acls:
            acl_id = acl.get('web_acl_id', acl.get('Id', ''))
            acl_name = acl.get('name', acl.get('Name', ''))
            rules = rules_by_web_acl.get(acl_id, [])

            web_acls_summary.append({
                'name': acl_name,
                'scope': acl.get('scope', acl.get('Scope', '')),
                'default_action': acl.get('default_action', ''),
                'capacity': acl.get('capacity', 0),
                'rules_count': len(rules),
                'rules': [{'name': r.get('name', ''), 'type': r.get('rule_type', ''),
                          'priority': r.get('priority', '')} for r in rules]
            })

        # Format resources
        resources_by_acl = {}
        for resource in resources:
            web_acl_name = resource.get('web_acl_name', '')
            if web_acl_name not in resources_by_acl:
                resources_by_acl[web_acl_name] = []
            resources_by_acl[web_acl_name].append({
                'type': resource.get('resource_type', ''),
                'arn': resource.get('resource_arn', '')
            })

        # Prepare formatted data
        data = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'total_requests': f"{summary.get('total_requests', 0):,}",
            'blocked_requests': f"{summary.get('blocked_requests', 0):,}",
            'block_rate': f"{summary.get('block_rate_percent', 0):.2f}%",
            'unique_ips': f"{summary.get('unique_client_ips', 0):,}",
            'unique_countries': f"{summary.get('unique_countries', 0):,}",
            'web_acls_count': len(web_acls),
            'web_acls': web_acls_summary,
            'resources_by_acl': resources_by_acl,
            'total_resources': len(resources),
            'security_score': coverage.get('security_posture_score', 0),
            'logging_coverage': f"{coverage.get('logging_coverage_percent', 0):.1f}%",
            'time_range_start': str(summary.get('time_range', {}).get('start', ''))[:19],
            'time_range_end': str(summary.get('time_range', {}).get('end', ''))[:19],
            'top_rules': [{'name': r.get('rule_name', ''), 'hits': r.get('hit_count', 0),
                          'block_rate': f"{r.get('block_rate_percent', 0):.1f}%"} for r in rule_effectiveness[:10]],
            'top_countries': [{'country': g.get('country', ''), 'requests': g.get('total_requests', 0),
                              'threat_score': f"{g.get('threat_score', 0):.1f}%"} for g in geo_dist[:10]],
            'top_blocked_ips': [{'ip': ip.get('ip', ''), 'country': ip.get('country', ''),
                                'blocks': ip.get('block_count', 0)} for ip in top_ips[:20]]
        }

        return data

    def _export_prompt(self, template_path: Path, data: Dict[str, Any]) -> None:
        """
        Export a single prompt template with injected data.
        """
        logger.info(f"Processing template: {template_path.name}")

        # Read template
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Failed to read template {template_path}: {e}")
            raise

        # Inject data
        filled_prompt = self._inject_data(template, data)

        # Write to export directory
        export_path = self.export_dir / template_path.name
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(filled_prompt)
            logger.info(f"Exported: {export_path}")
        except Exception as e:
            logger.error(f"Failed to write {export_path}: {e}")
            raise

    def _inject_data(self, template: str, data: Dict[str, Any]) -> str:
        """
        Inject WAF data into the template.
        """
        filled = template

        # Replace simple placeholders
        simple_replacements = {
            '{{analysis_date}}': data['analysis_date'],
            '{{total_requests}}': data['total_requests'],
            '{{blocked_requests}}': data['blocked_requests'],
            '{{block_rate}}': data['block_rate'],
            '{{unique_ips}}': data['unique_ips'],
            '{{unique_countries}}': data['unique_countries'],
            '{{web_acls_count}}': str(data['web_acls_count']),
            '{{total_resources}}': str(data['total_resources']),
            '{{security_score}}': str(data['security_score']),
            '{{logging_coverage}}': data['logging_coverage'],
            '{{time_range_start}}': data['time_range_start'],
            '{{time_range_end}}': data['time_range_end']
        }

        for placeholder, value in simple_replacements.items():
            filled = filled.replace(placeholder, value)

        # Replace Web ACLs list
        if '{{web_acls_list}}' in filled:
            web_acls_text = self._format_web_acls(data['web_acls'])
            filled = filled.replace('{{web_acls_list}}', web_acls_text)

        # Replace rules list
        if '{{top_rules}}' in filled:
            rules_text = self._format_top_rules(data['top_rules'])
            filled = filled.replace('{{top_rules}}', rules_text)

        # Replace geographic distribution
        if '{{top_countries}}' in filled:
            countries_text = self._format_top_countries(data['top_countries'])
            filled = filled.replace('{{top_countries}}', countries_text)

        # Replace top blocked IPs
        if '{{top_blocked_ips}}' in filled:
            ips_text = self._format_top_ips(data['top_blocked_ips'])
            filled = filled.replace('{{top_blocked_ips}}', ips_text)

        return filled

    def _format_web_acls(self, web_acls: List[Dict[str, Any]]) -> str:
        """Format Web ACLs list for prompt."""
        lines = []
        for i, acl in enumerate(web_acls, 1):
            lines.append(f"{i}. **{acl['name']}**")
            lines.append(f"   - Scope: {acl['scope']}")
            lines.append(f"   - Default Action: {acl['default_action']}")
            lines.append(f"   - Capacity: {acl['capacity']} WCU")
            lines.append(f"   - Rules: {acl['rules_count']}")

            if acl['rules']:
                lines.append(f"   - Rule Types:")
                for rule in acl['rules'][:5]:  # Show top 5 rules
                    lines.append(f"     * {rule['name']} (Priority: {rule['priority']}, Type: {rule['type']})")
                if len(acl['rules']) > 5:
                    lines.append(f"     * ... and {len(acl['rules']) - 5} more rules")
            lines.append("")

        return "\n".join(lines)

    def _format_top_rules(self, rules: List[Dict[str, Any]]) -> str:
        """Format top rules for prompt."""
        lines = []
        for i, rule in enumerate(rules, 1):
            lines.append(f"{i}. {rule['name']}: {rule['hits']} hits (Block Rate: {rule['block_rate']})")
        return "\n".join(lines) if lines else "No rule data available"

    def _format_top_countries(self, countries: List[Dict[str, Any]]) -> str:
        """Format top countries for prompt."""
        lines = []
        for i, country in enumerate(countries, 1):
            lines.append(f"{i}. {country['country']}: {country['requests']} requests (Threat Score: {country['threat_score']})")
        return "\n".join(lines) if lines else "No geographic data available"

    def _format_top_ips(self, ips: List[Dict[str, Any]]) -> str:
        """Format top blocked IPs for prompt."""
        lines = []
        for i, ip in enumerate(ips, 1):
            lines.append(f"{i}. {ip['ip']} ({ip['country']}): {ip['blocks']} blocks")
        return "\n".join(lines) if lines else "No blocked IP data available"
