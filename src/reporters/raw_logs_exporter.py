"""
Raw Logs Exporter

Exports raw AWS WAF logs from CloudWatch to JSON Lines format for external processing.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RawLogsExporter:
    """
    Exports raw CloudWatch logs to JSON Lines format.
    """

    def export_raw_logs(self, log_events: List[Dict[str, Any]],
                       output_dir: str,
                       log_source_name: str = "cloudwatch") -> str:
        """
        Export raw log events to JSON Lines file.

        Args:
            log_events: List of log events from CloudWatch
            output_dir: Output directory path
            log_source_name: Name of the log source (e.g., log group name or "cloudwatch")

        Returns:
            str: Path to the exported file
        """
        if not log_events:
            logger.warning("No log events to export")
            return None

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize log source name for filename
        safe_source_name = log_source_name.replace('/', '_').replace(':', '_')

        filename = f"raw_waf_logs_{safe_source_name}_{timestamp}.jsonl"
        filepath = output_path / filename

        try:
            # Export to JSON Lines format (one JSON object per line)
            with open(filepath, 'w', encoding='utf-8') as f:
                for event in log_events:
                    # Write the raw log message
                    json.dump(event, f, ensure_ascii=False, default=str)
                    f.write('\n')

            logger.info(f"✅ Exported {len(log_events):,} raw log events to: {filepath}")
            logger.info(f"   File format: JSON Lines (.jsonl)")
            logger.info(f"   File size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export raw logs: {e}")
            return None

    def export_raw_logs_by_web_acl(self, log_events: List[Dict[str, Any]],
                                   output_dir: str,
                                   log_source_name: str = "cloudwatch") -> Dict[str, str]:
        """
        Export raw log events grouped by Web ACL to separate files.

        Args:
            log_events: List of log events from CloudWatch
            output_dir: Output directory path
            log_source_name: Name of the log source

        Returns:
            Dict[str, str]: Mapping of Web ACL ID/name to exported file path
        """
        if not log_events:
            logger.warning("No log events to export")
            return {}

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Group logs by Web ACL
        logs_by_web_acl = {}

        for event in log_events:
            # Parse the log message to extract Web ACL info
            try:
                # The message field contains the actual WAF log JSON
                message = event.get('message', '{}')
                if isinstance(message, str):
                    log_data = json.loads(message)
                else:
                    log_data = message

                # Extract Web ACL ID or ARN
                web_acl_id = log_data.get('webaclId', 'unknown')

                # Use a short version of the ARN for the filename
                if '/' in web_acl_id:
                    web_acl_name = web_acl_id.split('/')[-1]
                else:
                    web_acl_name = web_acl_id

                if web_acl_name not in logs_by_web_acl:
                    logs_by_web_acl[web_acl_name] = []

                logs_by_web_acl[web_acl_name].append(event)

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse log event for grouping: {e}")
                # Add to 'unknown' group
                if 'unknown' not in logs_by_web_acl:
                    logs_by_web_acl['unknown'] = []
                logs_by_web_acl['unknown'].append(event)

        # Export each Web ACL's logs to a separate file
        exported_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for web_acl_name, events in logs_by_web_acl.items():
            safe_source_name = log_source_name.replace('/', '_').replace(':', '_')
            safe_web_acl_name = web_acl_name.replace('/', '_').replace(':', '_')

            filename = f"raw_waf_logs_{safe_web_acl_name}_{safe_source_name}_{timestamp}.jsonl"
            filepath = output_path / filename

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for event in events:
                        json.dump(event, f, ensure_ascii=False, default=str)
                        f.write('\n')

                logger.info(f"✅ Exported {len(events):,} raw log events for Web ACL '{web_acl_name}' to: {filepath}")
                exported_files[web_acl_name] = str(filepath)

            except Exception as e:
                logger.error(f"Failed to export logs for Web ACL '{web_acl_name}': {e}")

        if exported_files:
            logger.info(f"📁 Exported logs for {len(exported_files)} Web ACL(s)")
            total_size = sum(Path(f).stat().st_size for f in exported_files.values())
            logger.info(f"   Total size: {total_size / 1024 / 1024:.2f} MB")

        return exported_files
