"""
Prompt Template Data Injection

This module populates LLM prompt templates with actual WAF metrics data.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptInjector:
    """Injects WAF metrics into LLM prompt templates."""

    def __init__(self, template_dir: str = "config/prompts"):
        """
        Initialize the prompt injector.

        Args:
            template_dir: Directory containing prompt template files
        """
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        logger.info(f"PromptInjector initialized with template dir: {template_dir}")

    def load_template(self, template_name: str) -> str:
        """
        Load a prompt template file.

        Args:
            template_name: Name of the template file (e.g., 'comprehensive_waf_analysis.md')

        Returns:
            str: Template content

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self.template_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.debug(f"Loaded template: {template_name} ({len(content)} chars)")
        return content

    def create_comprehensive_prompt(
        self,
        metrics: Dict[str, Any],
        web_acls: List[Dict[str, Any]],
        resources: List[Dict[str, Any]],
        account_info: Dict[str, Any]
    ) -> str:
        """
        Create comprehensive analysis prompt with all metrics injected.

        Args:
            metrics: Calculated metrics from MetricsCalculator
            web_acls: List of Web ACL configurations
            resources: List of protected resources
            account_info: AWS account information (account_id, account_alias, region, profile, timezone)

        Returns:
            str: Ready-to-use prompt for LLM with all data injected
        """
        logger.info("Creating comprehensive prompt with data injection...")

        template = self.load_template('comprehensive_waf_analysis.md')

        # Extract time range
        time_range = metrics.get('summary', {}).get('time_range', {})
        start_date = self._format_datetime(time_range.get('start', 'N/A'))
        end_date = self._format_datetime(time_range.get('end', 'N/A'))

        # Format Web ACL overview
        web_acl_overview = self._format_web_acls(web_acls)

        # Format data for injection
        try:
            prompt = template.format(
                # Account context
                account_name=account_info.get('account_alias', account_info.get('account_id', 'N/A')),
                account_id=account_info.get('account_id', 'N/A'),
                region=account_info.get('region', 'N/A'),
                timezone=account_info.get('timezone', 'UTC'),
                time_period=f"{start_date} to {end_date}",
                account_info=self._to_json(account_info),

                # Configuration
                web_acl_overview=self._to_json(web_acl_overview),
                summary_metrics=self._to_json(metrics.get('summary', {})),

                # Rule analysis
                rule_effectiveness=self._to_json(self._limit_list(metrics.get('rule_effectiveness', []), 50)),
                action_distribution=self._to_json(metrics.get('action_distribution', {})),

                # Traffic patterns
                daily_trends=self._format_dataframe(metrics.get('daily_trends')),
                hourly_patterns=self._to_json(self._limit_list(metrics.get('hourly_patterns', []), 24)),
                geographic_distribution=self._to_json(self._limit_list(metrics.get('geographic_distribution', []), 30)),

                # Threat intelligence
                top_blocked_ips=self._to_json(self._limit_list(metrics.get('top_blocked_ips', []), 30)),
                bot_analysis=self._to_json(metrics.get('bot_analysis', {})),
                attack_types=self._to_json(metrics.get('attack_type_distribution', {})),

                # Coverage
                web_acl_coverage=self._to_json(metrics.get('web_acl_coverage', {}))
            )

            prompt_size = len(prompt)
            logger.info(f"Prompt created successfully ({prompt_size:,} characters, ~{prompt_size//4:,} tokens)")
            return prompt

        except KeyError as e:
            logger.error(f"Missing template placeholder: {e}")
            raise ValueError(f"Template formatting error - missing placeholder: {e}")
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            raise

    def save_prompt_to_file(self, prompt: str, output_path: str) -> None:
        """
        Save generated prompt to file for review or manual use.

        Args:
            prompt: Generated prompt text
            output_path: Path to save the prompt file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)

        logger.info(f"Prompt saved to: {output_path} ({len(prompt):,} characters)")

    def _format_web_acls(self, web_acls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Web ACL data for template injection."""
        formatted = []
        for acl in web_acls:
            default_action = acl.get('default_action', acl.get('DefaultAction', {}))
            if isinstance(default_action, dict):
                action_str = 'ALLOW' if 'Allow' in default_action else 'BLOCK'
            else:
                action_str = str(default_action)

            formatted.append({
                'name': acl.get('name', acl.get('Name', 'Unknown')),
                'scope': acl.get('scope', acl.get('Scope', 'Unknown')),
                'capacity': acl.get('capacity', acl.get('Capacity', 0)),
                'default_action': action_str
            })
        return formatted

    def _format_dataframe(self, df) -> str:
        """
        Convert pandas DataFrame to JSON string.

        Args:
            df: Pandas DataFrame or None

        Returns:
            str: JSON array string
        """
        if df is None:
            return "[]"

        try:
            if hasattr(df, 'empty') and df.empty:
                return "[]"
            # Limit to first 30 rows to avoid token bloat
            limited_df = df.head(30)
            return limited_df.to_json(orient='records', date_format='iso', indent=2)
        except Exception as e:
            logger.warning(f"Error formatting DataFrame: {e}")
            return "[]"

    def _to_json(self, data: Any, indent: int = 2) -> str:
        """
        Convert data to formatted JSON string.

        Args:
            data: Any JSON-serializable data
            indent: JSON indentation level

        Returns:
            str: Formatted JSON string
        """
        try:
            return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error converting to JSON: {e}")
            return "{}"

    def _limit_list(self, data: List[Any], limit: int) -> List[Any]:
        """
        Limit list size to avoid excessive token usage.

        Args:
            data: List to limit
            limit: Maximum number of items

        Returns:
            List: Limited list
        """
        if not isinstance(data, list):
            return []
        return data[:limit]

    def _format_datetime(self, dt) -> str:
        """
        Format datetime to string.

        Args:
            dt: Datetime object or string

        Returns:
            str: Formatted datetime string
        """
        if dt is None or dt == 'N/A':
            return 'N/A'

        if isinstance(dt, str):
            # Already a string, truncate to date+time
            return str(dt)[:19] if len(str(dt)) > 19 else str(dt)

        if hasattr(dt, 'strftime'):
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        return str(dt)[:19]
