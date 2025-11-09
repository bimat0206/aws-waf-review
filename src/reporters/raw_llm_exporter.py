"""
Raw LLM Response Exporter

Exports raw LLM responses from analysis to markdown files for external review and archiving.
"""

import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class RawLLMExporter:
    """
    Exports raw LLM analysis responses to markdown files.
    """

    def export_raw_response(
        self,
        response: str,
        output_dir: str,
        account_identifier: str,
        model_name: str = "llm",
        web_acl_name: str = None
    ) -> str:
        """
        Export raw LLM response to markdown file.

        Args:
            response: Raw LLM response text
            output_dir: Output directory path (e.g., raw-llm-response/{alias}_{account_id})
            account_identifier: Account identifier (alias_accountid)
            model_name: Name of the LLM model used
            web_acl_name: Optional Web ACL name for targeted analysis

        Returns:
            str: Path to the exported file
        """
        if not response:
            logger.warning("No LLM response to export")
            return None

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize model name for filename
        safe_model_name = model_name.replace('/', '_').replace(':', '_').replace('.', '_')

        # Build filename
        if web_acl_name:
            safe_web_acl_name = web_acl_name.replace('/', '_').replace(':', '_').replace(' ', '_')
            filename = f"{account_identifier}_{safe_web_acl_name}_{safe_model_name}_{timestamp}_response.md"
        else:
            filename = f"{account_identifier}_{safe_model_name}_{timestamp}_response.md"

        filepath = output_path / filename

        try:
            # Export to markdown file
            with open(filepath, 'w', encoding='utf-8') as f:
                # Add header with metadata
                f.write("# AWS WAF Security Analysis - LLM Response\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Account:** {account_identifier}\n")
                f.write(f"**Model:** {model_name}\n")
                if web_acl_name:
                    f.write(f"**Web ACL:** {web_acl_name}\n")
                f.write("\n---\n\n")

                # Write the raw response
                f.write(response)

            file_size_kb = filepath.stat().st_size / 1024

            logger.info(f"✅ Exported raw LLM response to: {filepath}")
            logger.info(f"   File format: Markdown (.md)")
            logger.info(f"   File size: {file_size_kb:.2f} KB")

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export raw LLM response: {e}")
            return None

    def export_full_analysis(
        self,
        analysis_result: dict,
        output_dir: str,
        account_identifier: str,
        web_acl_name: str = None
    ) -> str:
        """
        Export full LLM analysis including metadata and parsed results.

        Args:
            analysis_result: Complete analysis result from LLMAnalyzer
            output_dir: Output directory path
            account_identifier: Account identifier (alias_accountid)
            web_acl_name: Optional Web ACL name for targeted analysis

        Returns:
            str: Path to the exported file
        """
        if not analysis_result:
            logger.warning("No analysis result to export")
            return None

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Extract metadata
        metadata = analysis_result.get('metadata', {})
        model_name = metadata.get('model', 'unknown')
        safe_model_name = model_name.replace('/', '_').replace(':', '_').replace('.', '_')

        # Build filename
        if web_acl_name:
            safe_web_acl_name = web_acl_name.replace('/', '_').replace(':', '_').replace(' ', '_')
            filename = f"{account_identifier}_{safe_web_acl_name}_{safe_model_name}_{timestamp}_full_analysis.md"
        else:
            filename = f"{account_identifier}_{safe_model_name}_{timestamp}_full_analysis.md"

        filepath = output_path / filename

        try:
            # Export to markdown file
            with open(filepath, 'w', encoding='utf-8') as f:
                # Add header with metadata
                f.write("# AWS WAF Security Analysis - Complete LLM Analysis\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Account:** {account_identifier}\n")

                if metadata:
                    f.write(f"\n## Analysis Metadata\n\n")
                    f.write(f"- **Provider:** {metadata.get('provider', 'N/A')}\n")
                    f.write(f"- **Model:** {metadata.get('model', 'N/A')}\n")
                    f.write(f"- **Total Tokens:** {metadata.get('tokens_used', {}).get('total', 0):,}\n")
                    f.write(f"- **Input Tokens:** {metadata.get('tokens_used', {}).get('input', 0):,}\n")
                    f.write(f"- **Output Tokens:** {metadata.get('tokens_used', {}).get('output', 0):,}\n")
                    f.write(f"- **Estimated Cost:** ${metadata.get('cost_estimate', 0):.4f}\n")
                    f.write(f"- **Duration:** {metadata.get('duration', 0):.2f}s\n")

                if web_acl_name:
                    f.write(f"- **Web ACL:** {web_acl_name}\n")

                f.write("\n---\n\n")

                # Write the raw response
                response = analysis_result.get('response', '')
                if response:
                    f.write("## LLM Response\n\n")
                    f.write(response)
                else:
                    f.write("*No response available*\n")

            file_size_kb = filepath.stat().st_size / 1024

            logger.info(f"✅ Exported full LLM analysis to: {filepath}")
            logger.info(f"   File format: Markdown (.md)")
            logger.info(f"   File size: {file_size_kb:.2f} KB")

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export full LLM analysis: {e}")
            return None
