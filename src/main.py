#!/usr/bin/env python3
"""
AWS WAF Security Analysis Tool

Main orchestration script for analyzing AWS WAF configurations and logs.
This tool fetches WAF data, stores it in DuckDB, and generates comprehensive
Excel reports with visualizations.
"""

import sys
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
try:
    import coloredlogs
except ImportError:  # pragma: no cover - optional dependency
    coloredlogs = None

from storage.duckdb_manager import DuckDBManager
from fetchers.cloudwatch_fetcher import CloudWatchFetcher
from fetchers.s3_fetcher import S3Fetcher
from processors.config_processor import WAFConfigProcessor
from processors.log_parser import WAFLogParser
from processors.metrics_calculator import MetricsCalculator
from reporters.excel_generator import ExcelReportGenerator
from reporters.prompt_exporter import PromptExporter
from reporters.raw_logs_exporter import RawLogsExporter
from utils.aws_helpers import (
    verify_aws_credentials,
    get_session_info,
    get_current_region
)
from utils.time_helpers import (
    get_time_window,
    format_datetime,
    get_time_window_description,
    get_today_window,
    get_yesterday_window,
    get_past_week_window,
    get_custom_window
)

# Setup logging
logger = logging.getLogger(__name__)
if coloredlogs:
    coloredlogs.install(
        level='INFO',
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.warning("coloredlogs not installed; falling back to basic logging formatting")


def get_account_identifier(account_id: Optional[str], account_alias: Optional[str] = None) -> str:
    """
    Generate account identifier for directory and file naming.

    Args:
        account_id (Optional[str]): AWS Account ID
        account_alias (Optional[str]): AWS Account alias/name

    Returns:
        str: Account identifier in format "{alias}_{account_id}", "{account_id}",
             or "default" when account metadata is unavailable
    """
    if account_alias and account_id:
        return f"{account_alias}_{account_id}"
    if account_alias:
        return account_alias
    if account_id:
        return account_id
    return 'default'


def setup_directories(account_id: str = None, account_alias: str = None):
    """
    Create necessary directories for the application.

    If account_id is provided, creates account-specific subdirectories.

    Args:
        account_id (str, optional): AWS Account ID for organizing data by account
        account_alias (str, optional): AWS Account alias/name for friendly naming

    Creates:
        - data/ or data/{account_identifier}/ : For DuckDB database files
        - output/ or output/{account_identifier}/ : For Excel reports and exports
        - logs/ or logs/{account_identifier}/ : For application logs
        - exported-prompt/ or exported-prompt/{account_identifier}/ : For exported LLM prompts with WAF data

    Note:
        - config/prompts/ contains prompt templates (version controlled)
        - exported-prompt/ contains filled prompts with account data (gitignored)
        - account_identifier format: "{alias}_{account_id}" if alias exists, otherwise "{account_id}"

    Returns:
        dict: Dictionary containing created directory paths
    """
    if account_id:
        # Generate account identifier with alias if available
        account_identifier = get_account_identifier(account_id, account_alias)

        # Create account-specific subdirectories
        base_dirs = {
            'data': f'data/{account_identifier}',
            'output': f'output/{account_identifier}',
            'logs': f'logs/{account_identifier}',
            'exported_prompts': f'exported-prompt/{account_identifier}',
            'raw_logs': f'raw-logs/{account_identifier}'
        }
        logger.info(f"Setting up account-specific directories for AWS Account: {account_identifier}")
    else:
        # Create root directories only
        base_dirs = {
            'data': 'data',
            'output': 'output',
            'logs': 'logs',
            'exported_prompts': 'exported-prompt',
            'raw_logs': 'raw-logs'
        }

    created_paths = {}
    for key, directory in base_dirs.items():
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}/")
        else:
            logger.debug(f"Directory already exists: {directory}/")
        created_paths[key] = str(dir_path)

    return created_paths


def export_raw_logs(raw_events: List[dict], raw_logs_dir: Optional[str], source: str,
                    identifier: str, start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> Optional[Path]:
    """Persist raw log events for offline inspection."""
    if not raw_logs_dir or not raw_events:
        return None

    try:
        safe_identifier = identifier.strip('/').replace('/', '_')
        safe_identifier = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '_' for ch in safe_identifier)
        if not safe_identifier:
            safe_identifier = 'default'
        dest_dir = Path(raw_logs_dir) / source / safe_identifier
        dest_dir.mkdir(parents=True, exist_ok=True)

        window_parts = []
        if start_time:
            window_parts.append(start_time.strftime('%Y%m%d%H%M%S'))
        if end_time:
            window_parts.append(end_time.strftime('%Y%m%d%H%M%S'))
        window = '_to_'.join(window_parts) if window_parts else datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_path = dest_dir / f"{source}_logs_{window}.jsonl"

        with open(file_path, 'w', encoding='utf-8') as fh:
            for event in raw_events:
                json.dump(event, fh, default=str)
                fh.write('\n')

        logger.info(f"Exported raw {source} logs to {file_path}")
        return file_path
    except Exception as exc:
        logger.warning(f"Failed to export raw {source} logs: {exc}")
        return None


def print_banner():
    """Print application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          AWS WAF Security Analysis Tool                  ║
    ║                                                           ║
    ║  Analyze WAF configurations and logs to identify         ║
    ║  security gaps, optimize rules, and improve protection   ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def verify_environment():
    """Verify AWS credentials and environment setup."""
    logger.info("Verifying AWS environment...")

    if not verify_aws_credentials():
        logger.error("AWS credentials are not configured or invalid")
        logger.error("Please configure AWS CLI with: aws configure --profile <profile-name>")
        return False

    # Get session info
    session_info = get_session_info()
    logger.info(f"AWS Profile: {session_info.get('profile', 'default')}")
    logger.info(f"AWS Region: {session_info.get('region')}")
    logger.info(f"AWS Account ID: {session_info.get('account_id')}")
    if session_info.get('account_alias'):
        logger.info(f"AWS Account Alias: {session_info.get('account_alias')}")
    logger.info(f"IAM Identity: {session_info.get('arn')}")

    return True


def display_web_acl_summary(db_manager: DuckDBManager):
    """
    Display summary of fetched Web ACLs and resources.

    Args:
        db_manager (DuckDBManager): Database manager instance
    """
    conn = db_manager.get_connection()

    # Get Web ACLs
    web_acls = conn.execute("""
        SELECT web_acl_id, name, scope, default_action, capacity
        FROM web_acls
        ORDER BY scope, name
    """).fetchall()

    if not web_acls:
        print("\n⚠️  No Web ACLs found in database")
        return

    print("\n" + "="*80)
    print("📋 Web ACL Inventory")
    print("="*80)

    for idx, (acl_id, name, scope, default_action, capacity) in enumerate(web_acls, 1):
        print(f"\n{idx}. {name}")
        print(f"   Scope: {scope}")
        print(f"   Default Action: {default_action}")
        print(f"   Capacity: {capacity} WCU")

        # Get rule count
        rule_count = conn.execute("""
            SELECT COUNT(*) FROM rules WHERE web_acl_id = ?
        """, [acl_id]).fetchone()[0]
        print(f"   Rules: {rule_count}")

        # Get protected resources
        resources = conn.execute("""
            SELECT resource_arn, resource_type FROM resource_associations
            WHERE web_acl_id = ?
        """, [acl_id]).fetchall()

        if resources:
            print(f"   Protected Resources: {len(resources)}")
            for resource_arn, resource_type in resources[:3]:  # Show first 3
                # Extract resource name from ARN
                resource_name = resource_arn.split('/')[-1] if '/' in resource_arn else resource_arn.split(':')[-1]
                print(f"     - {resource_type}: {resource_name}")
            if len(resources) > 3:
                print(f"     ... and {len(resources) - 3} more")
        else:
            print(f"   Protected Resources: None")

        # Check logging status
        logging_config = conn.execute("""
            SELECT destination_type FROM logging_configurations
            WHERE web_acl_id = ?
        """, [acl_id]).fetchone()

        if logging_config:
            print(f"   Logging: ✓ Enabled ({logging_config[0]})")
        else:
            print(f"   Logging: ✗ Not configured")

    print("\n" + "="*80)


def select_web_acls(db_manager: DuckDBManager):
    """
    Let user select which Web ACLs to analyze.

    Args:
        db_manager (DuckDBManager): Database manager instance

    Returns:
        list: List of selected Web ACL IDs, or None for all
    """
    conn = db_manager.get_connection()

    web_acls = conn.execute("""
        SELECT web_acl_id, name, scope FROM web_acls
        ORDER BY scope, name
    """).fetchall()

    if not web_acls:
        return None

    print("\n📊 Select Web ACLs to analyze:")
    print("0. Analyze ALL Web ACLs")
    for idx, (acl_id, name, scope) in enumerate(web_acls, 1):
        print(f"{idx}. {name} ({scope})")

    while True:
        selection = input("\nEnter selection (0 for all, or comma-separated numbers): ").strip()

        if selection == '0':
            return None  # Analyze all

        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_ids = [web_acls[i][0] for i in indices if 0 <= i < len(web_acls)]
            if selected_ids:
                return selected_ids
            else:
                print("❌ Invalid selection. Please try again.")
        except (ValueError, IndexError):
            print("❌ Invalid input. Please enter numbers separated by commas.")


def fetch_waf_configurations(db_manager: DuckDBManager, scope: str = 'REGIONAL', interactive: bool = True):
    """
    Fetch WAF configurations and store in database.

    Args:
        db_manager (DuckDBManager): Database manager instance
        scope (str): WAF scope - 'REGIONAL' or 'CLOUDFRONT'
        interactive (bool): Whether to show interactive prompts
    """
    logger.info(f"Fetching WAF configurations for {scope} scope...")

    processor = WAFConfigProcessor(scope=scope)

    # Get all Web ACLs
    web_acl_configs = processor.get_all_web_acl_configs()

    if not web_acl_configs:
        logger.warning(f"No Web ACLs found in {scope} scope")
        return 0

    logger.info(f"Found {len(web_acl_configs)} Web ACLs")

    # Store each Web ACL with its resources and logging config
    for web_acl_config in web_acl_configs:
        # Store Web ACL
        db_manager.insert_web_acl(web_acl_config)

        web_acl_id = web_acl_config.get('Id')
        web_acl_arn = web_acl_config.get('ARN')

        # Extract and store rules
        rules = processor.extract_rules_from_web_acl(web_acl_config)
        if rules:
            db_manager.insert_rules(web_acl_id, rules)

        # Get and store resource associations
        resources = processor.get_resources_for_web_acl(web_acl_arn)
        for resource_arn in resources:
            from utils.aws_helpers import determine_resource_type
            resource_type = determine_resource_type(resource_arn)
            db_manager.insert_resource_association(web_acl_id, resource_arn, resource_type)

        # Get and store logging configuration
        logging_config = processor.get_logging_configuration(web_acl_arn)
        if logging_config:
            db_manager.insert_logging_configuration(web_acl_id, logging_config)

    logger.info("WAF configurations stored successfully")

    # Display summary if interactive
    if interactive:
        display_web_acl_summary(db_manager)

    return len(web_acl_configs)


def fetch_logs_from_cloudwatch(db_manager: DuckDBManager, log_group_name: str,
                               start_time: datetime, end_time: datetime,
                               raw_logs_dir: Optional[str] = None,
                               region: Optional[str] = None):
    """
    Fetch logs from CloudWatch and store in database.
    Also exports raw logs to JSON Lines format.

    Args:
        db_manager (DuckDBManager): Database manager instance
        log_group_name (str): CloudWatch log group name
        start_time (datetime): Start of time range
        end_time (datetime): End of time range
        raw_logs_dir (Optional[str]): Directory for raw logs export
        region (Optional[str]): AWS region for CloudWatch (uses current region if not specified)
    """
    logger.info(f"Fetching logs from CloudWatch: {log_group_name}")
    logger.info(f"Time range: {get_time_window_description(start_time, end_time)}")
    if region:
        logger.info(f"Using region: {region}")

    fetcher = CloudWatchFetcher(region=region)
    parser = WAFLogParser()

    # Fetch logs
    log_events = fetcher.get_log_events(log_group_name, start_time, end_time)

    if not log_events:
        logger.warning("No log events found in CloudWatch")
        return

    logger.info(f"Fetched {len(log_events)} log events")

    # Export raw logs immediately after fetching
    try:
        session_info = get_session_info()
        account_id = session_info.get('account_id')
        account_alias = session_info.get('account_alias')
        account_identifier = get_account_identifier(account_id, account_alias)

        # Export to raw-logs directory (use provided path or default)
        if raw_logs_dir:
            output_dir = raw_logs_dir
        else:
            output_dir = f"raw-logs"

        logger.info("📦 Exporting raw CloudWatch logs...")
        exporter = RawLogsExporter()
        exported_file = exporter.export_raw_logs_by_web_acl(
            log_events,
            output_dir,
            log_source_name=log_group_name
        )

        if exported_file:
            logger.info(f"✅ Raw logs exported successfully")
    except Exception as e:
        logger.warning(f"Failed to export raw logs (continuing with processing): {e}")

    # Parse logs
    parsed_logs = parser.parse_batch(log_events, source='cloudwatch')

    if not parsed_logs:
        logger.warning("No logs were successfully parsed")
        return

    # Store in database
    db_manager.insert_log_entries(parsed_logs)

    logger.info(f"Successfully stored {len(parsed_logs)} log entries")


def fetch_logs_from_s3(db_manager: DuckDBManager, bucket: str, prefix: str,
                      start_time: datetime, end_time: datetime,
                      raw_logs_dir: Optional[str] = None):
    """
    Fetch logs from S3 and store in database.

    Args:
        db_manager (DuckDBManager): Database manager instance
        bucket (str): S3 bucket name
        prefix (str): S3 key prefix
        start_time (datetime): Start of time range
        end_time (datetime): End of time range
    """
    logger.info(f"Fetching logs from S3: s3://{bucket}/{prefix}")
    logger.info(f"Time range: {get_time_window_description(start_time, end_time)}")

    fetcher = S3Fetcher()
    parser = WAFLogParser()

    # Estimate volume first
    estimation = fetcher.estimate_log_volume(bucket, prefix, start_time, end_time)
    logger.info(f"Estimated {estimation['estimated_events']:,} log entries in {estimation['total_objects']} files")

    # Fetch logs
    log_entries = fetcher.fetch_logs(bucket, prefix, start_time, end_time)

    if not log_entries:
        logger.warning("No log entries found in S3")
        return

    logger.info(f"Fetched {len(log_entries)} log entries")

    export_raw_logs(
        log_entries,
        raw_logs_dir,
        source='s3',
        identifier=f"{bucket}/{prefix}",
        start_time=start_time,
        end_time=end_time
    )

    # Parse logs
    parsed_logs = parser.parse_batch(log_entries, source='s3')

    if not parsed_logs:
        logger.warning("No logs were successfully parsed")
        return

    # Store in database (in chunks for large datasets)
    chunk_size = 10000
    for i in range(0, len(parsed_logs), chunk_size):
        chunk = parsed_logs[i:i+chunk_size]
        db_manager.insert_log_entries(chunk)
        logger.info(f"Stored chunk {i//chunk_size + 1}: {len(chunk)} entries")

    logger.info(f"Successfully stored {len(parsed_logs)} log entries")


def generate_excel_report(db_manager: DuckDBManager, output_path: str, selected_web_acl_ids: Optional[List[str]] = None):
    """
    Generate Excel report with visualizations.

    Args:
        db_manager (DuckDBManager): Database manager instance
        output_path (str): Path to save Excel report
        selected_web_acl_ids (Optional[List[str]]): List of Web ACL IDs to include in report. If None, includes all.
    """
    if selected_web_acl_ids:
        logger.info(f"Generating Excel report for {len(selected_web_acl_ids)} Web ACL(s)...")
    else:
        logger.info("Generating Excel report for all Web ACLs...")

    # Calculate metrics with Web ACL filter
    calculator = MetricsCalculator(db_manager, web_acl_ids=selected_web_acl_ids)
    metrics = calculator.calculate_all_metrics()

    # Get Web ACL data
    conn = db_manager.get_connection()

    # Filter Web ACLs if specific ones selected
    if selected_web_acl_ids:
        # Escape single quotes in IDs
        escaped_ids = [id.replace("'", "''") for id in selected_web_acl_ids]
        ids_str = "', '".join(escaped_ids)
        web_acl_filter = f"WHERE web_acl_id IN ('{ids_str}')"
    else:
        web_acl_filter = ""

    web_acls = conn.execute(f"SELECT * FROM web_acls {web_acl_filter}").fetchall()
    web_acls_list = [dict(zip(['web_acl_id', 'name', 'scope', 'default_action', 'description',
                               'visibility_config', 'capacity', 'managed_by_firewall_manager',
                               'created_at', 'updated_at'], row)) for row in web_acls]

    resources = conn.execute(f"SELECT * FROM resource_associations {web_acl_filter}").fetchall()
    resources_list = [dict(zip(['association_id', 'web_acl_id', 'resource_arn',
                                'resource_type', 'created_at'], row)) for row in resources]

    # Get Web ACL names for resources
    web_acl_names = {acl['web_acl_id']: acl['name'] for acl in web_acls_list}
    for resource in resources_list:
        resource['web_acl_name'] = web_acl_names.get(resource['web_acl_id'], 'Unknown')

    logging_configs = conn.execute(f"SELECT * FROM logging_configurations {web_acl_filter}").fetchall()
    logging_configs_list = [dict(zip(['config_id', 'web_acl_id', 'destination_type',
                                     'destination_arn', 'log_format', 'sampling_rate',
                                     'redacted_fields', 'created_at'], row)) for row in logging_configs]

    # Get rules
    rules = conn.execute(f"SELECT * FROM rules {web_acl_filter}").fetchall()
    rules_list = [dict(zip(['rule_id', 'web_acl_id', 'name', 'priority', 'rule_type', 'action',
                            'statement', 'visibility_config', 'override_action', 'created_at', 'updated_at'], row)) for row in rules]

    # Group rules by Web ACL
    rules_by_web_acl = {}
    for rule in rules_list:
        web_acl_id = rule.get('web_acl_id')
        if web_acl_id not in rules_by_web_acl:
            rules_by_web_acl[web_acl_id] = []
        rules_by_web_acl[web_acl_id].append(rule)

    # Generate Excel report
    generator = ExcelReportGenerator(output_path)
    generator.generate_report(metrics, web_acls_list, resources_list, logging_configs_list, rules_by_web_acl)

    logger.info(f"Excel report generated: {output_path}")

    # Export LLM prompts with injected data
    try:
        # Determine export directory based on account (fallbacks to 'default' offline)
        session_info = {}
        try:
            session_info = get_session_info()
        except Exception as session_error:
            logger.warning(f"Could not retrieve AWS session info for prompt export: {session_error}")

        account_id = session_info.get('account_id') if session_info else None
        account_alias = session_info.get('account_alias') if session_info else None
        account_identifier = get_account_identifier(account_id, account_alias)

        prompt_export_dir = f"exported-prompt/{account_identifier}"

        exporter = PromptExporter()
        prompt_count = exporter.export_all_prompts(
            metrics, web_acls_list, resources_list, rules_by_web_acl, logging_configs_list, prompt_export_dir
        )
        logger.info(f"Exported {prompt_count} LLM prompts to: {prompt_export_dir}")
    except Exception as e:
        logger.warning(f"Failed to export prompts: {e}")


def interactive_menu(db_manager: DuckDBManager):
    """
    Display interactive menu for user actions.

    Args:
        db_manager (DuckDBManager): Database manager instance

    Returns:
        str: User's choice
    """
    print("\n" + "="*80)
    print("🎯 What would you like to do?")
    print("="*80)
    print("1. Fetch WAF Configurations (Web ACLs, Rules, Resources)")
    print("2. Fetch WAF Logs (CloudWatch or S3)")
    print("3. View Current Inventory (Web ACLs and Resources)")
    print("4. Generate Excel Report")
    print("5. View Database Statistics")
    print("0. Exit")
    print("="*80)

    choice = input("\nEnter your choice (0-5): ").strip()
    return choice


def get_cloudwatch_log_groups_from_db(db_manager: DuckDBManager):
    """
    Extract CloudWatch log group names and regions from logging configurations in the database.

    Args:
        db_manager (DuckDBManager): Database manager instance

    Returns:
        list: List of tuples (log_group_name, web_acl_name, web_acl_id, region)
    """
    conn = db_manager.get_connection()

    # Query logging configurations for CloudWatch destinations
    results = conn.execute("""
        SELECT
            lc.destination_arn,
            lc.web_acl_id,
            wa.name as web_acl_name
        FROM logging_configurations lc
        JOIN web_acls wa ON lc.web_acl_id = wa.web_acl_id
        WHERE lc.destination_type = 'CLOUDWATCH'
        ORDER BY wa.name
    """).fetchall()

    log_groups = []
    for dest_arn, web_acl_id, web_acl_name in results:
        # Parse CloudWatch log group ARN
        # Format: arn:aws:logs:region:account-id:log-group:log-group-name:*
        # or: arn:aws:logs:region:account-id:log-group:log-group-name
        try:
            # Extract region and log group name from ARN
            # ARN format: arn:partition:service:region:account:resource
            arn_parts = dest_arn.split(':')
            if len(arn_parts) >= 6 and ':log-group:' in dest_arn:
                region = arn_parts[3]  # Region is at index 3
                log_group_part = dest_arn.split(':log-group:')[1]
                # Remove trailing ':*' if present
                log_group_name = log_group_part.rstrip(':*')
                log_groups.append((log_group_name, web_acl_name, web_acl_id, region))
            else:
                logger.warning(f"Could not parse log group from ARN: {dest_arn}")
        except Exception as e:
            logger.error(f"Error parsing CloudWatch ARN {dest_arn}: {e}")

    return log_groups


def interactive_scope_selection():
    """
    Let user select WAF scope interactively.

    Returns:
        list: List of scopes to fetch
    """
    print("\n📍 Select WAF Scope:")
    print("1. REGIONAL (ALB, API Gateway)")
    print("2. CLOUDFRONT (CloudFront distributions)")
    print("3. Both REGIONAL and CLOUDFRONT")

    while True:
        choice = input("\nEnter choice (1-3): ").strip()

        if choice == '1':
            return ['REGIONAL']
        elif choice == '2':
            return ['CLOUDFRONT']
        elif choice == '3':
            return ['REGIONAL', 'CLOUDFRONT']
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


def interactive_time_window():
    """
    Let user select time window for log analysis.

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) as UTC datetime objects
    """
    print("\n⏰ Select time window for log analysis:")
    print("1. Today (since midnight UTC)")
    print("2. Yesterday (full 24 hours)")
    print("3. Past week (last 7 days)")
    print("4. Past 3 months (~90 days)")
    print("5. Past 6 months (~180 days)")
    print("6. Custom date range")

    while True:
        choice = input("\nEnter choice (1-6): ").strip()

        if choice == '1':
            return get_today_window()
        elif choice == '2':
            return get_yesterday_window()
        elif choice == '3':
            return get_past_week_window()
        elif choice == '4':
            return get_time_window(3)
        elif choice == '5':
            return get_time_window(6)
        elif choice == '6':
            # Custom range
            print("\nEnter custom date range:")
            print("Supported formats: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
            print("Example: 2024-01-01 or 2024-01-01 12:00:00")

            while True:
                try:
                    start_date = input("Start date: ").strip()
                    end_date = input("End date: ").strip()

                    if not start_date or not end_date:
                        print("❌ Both start and end dates are required")
                        continue

                    return get_custom_window(start_date, end_date)
                except ValueError as e:
                    print(f"❌ {e}")
                    print("Please try again or press Ctrl+C to cancel")
        else:
            print("❌ Invalid choice. Please enter 1-6.")


def main():
    """Main execution function."""
    print_banner()

    # Parse arguments
    parser = argparse.ArgumentParser(description='AWS WAF Security Analysis Tool')
    parser.add_argument('--db-path', default='data/waf_analysis.duckdb',
                       help='Path to DuckDB database file (default: data/{account_id}/{account_id}_waf_analysis.duckdb)')
    parser.add_argument('--months', type=int, choices=[3, 6],
                       help='Number of months of logs to analyze (3 or 6)')
    parser.add_argument('--scope', choices=['REGIONAL', 'CLOUDFRONT'],
                       help='WAF scope to analyze')
    parser.add_argument('--skip-config', action='store_true',
                       help='Skip fetching WAF configurations')
    parser.add_argument('--skip-logs', action='store_true',
                       help='Skip fetching logs')
    parser.add_argument('--log-source', choices=['cloudwatch', 's3'],
                       help='Log source (cloudwatch or s3)')
    parser.add_argument('--log-group', help='CloudWatch log group name')
    parser.add_argument('--s3-bucket', help='S3 bucket name')
    parser.add_argument('--s3-prefix', help='S3 key prefix')
    parser.add_argument('--output', help='Output Excel report filename (default: output/{account_identifier}/{account_identifier}_{timestamp}_waf_report.xlsx)')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Run in non-interactive mode (no prompts)')

    args = parser.parse_args()

    # Determine if running in interactive mode
    # Interactive if no scope/log-source specified and not explicitly disabled
    interactive_mode = not args.non_interactive and (args.scope is None or args.log_source is None)

    # Verify environment first to get account ID
    if not verify_environment():
        return 1

    # Get AWS account info for directory organization
    session_info = get_session_info()
    account_id = session_info.get('account_id')
    account_alias = session_info.get('account_alias')

    # Generate account identifier for naming
    account_identifier = get_account_identifier(account_id, account_alias)

    # Setup account-specific directories
    dir_paths = setup_directories(account_id, account_alias)

    # Update database path if using default and we have a real account ID
    if args.db_path == 'data/waf_analysis.duckdb' and account_id:
        args.db_path = f"{dir_paths['data']}/{account_identifier}_waf_analysis.duckdb"
        logger.info(f"Using account-specific database: {args.db_path}")

    # Initialize database
    logger.info("Initializing database...")
    db_manager = DuckDBManager(args.db_path)
    db_manager.initialize_database()

    try:
        # Interactive mode: Menu-driven workflow
        if interactive_mode:
            while True:
                choice = interactive_menu(db_manager)

                if choice == '0':
                    # Exit
                    logger.info("Exiting...")
                    break

                elif choice == '1':
                    # Fetch WAF Configurations
                    scopes = interactive_scope_selection()
                    for scope in scopes:
                        count = fetch_waf_configurations(db_manager, scope=scope, interactive=True)
                        if count == 0 and scope == 'REGIONAL':
                            logger.warning("No REGIONAL Web ACLs found")

                elif choice == '2':
                    # Fetch WAF Logs
                    # First check if we have any Web ACLs
                    stats = db_manager.get_database_stats()
                    if stats.get('web_acls', 0) == 0:
                        print("\n⚠️  No Web ACLs found in database.")
                        print("Please fetch WAF configurations first (Option 1)")
                        continue

                    # Select time window
                    start_time, end_time = interactive_time_window()

                    # Select log source
                    print("\n📦 Select log source:")
                    print("1. CloudWatch Logs")
                    print("2. S3")
                    log_choice = input("\nEnter choice (1 or 2): ").strip()

                    if log_choice == '1':
                        # CloudWatch - First try to get log groups from database
                        db_log_groups = get_cloudwatch_log_groups_from_db(db_manager)

                        log_group_name = None
                        log_group_region = None

                        if db_log_groups:
                            print("\n📋 CloudWatch log groups from Web ACL configurations:")
                            for idx, (lg_name, web_acl_name, web_acl_id, region) in enumerate(db_log_groups, 1):
                                print(f"{idx}. {lg_name}")
                                print(f"    Web ACL: {web_acl_name}")
                                print(f"    Region: {region}")

                            print(f"{len(db_log_groups) + 1}. Enter a different log group name")

                            selection = input(f"\nEnter choice (1-{len(db_log_groups) + 1}): ").strip()
                            try:
                                idx = int(selection) - 1
                                if 0 <= idx < len(db_log_groups):
                                    log_group_name = db_log_groups[idx][0]
                                    log_group_region = db_log_groups[idx][3]
                                else:
                                    # Manual entry
                                    log_group_name = input("Enter CloudWatch log group name: ")
                                    log_group_region = None  # Use current region
                            except ValueError:
                                # Try to use it as log group name directly
                                log_group_name = selection
                                log_group_region = None  # Use current region
                        else:
                            # Fallback: Query CloudWatch API for log groups
                            print("\n💡 No CloudWatch log groups found in database configurations.")
                            print("Querying CloudWatch API for available log groups...")

                            fetcher = CloudWatchFetcher()
                            api_log_groups = fetcher.list_log_groups(prefix='aws-waf-logs')

                            if api_log_groups:
                                print("\n📋 Available WAF log groups from CloudWatch:")
                                for idx, lg in enumerate(api_log_groups, 1):
                                    print(f"{idx}. {lg['logGroupName']}")

                                selection = input("\nEnter log group number or full name: ").strip()
                                try:
                                    idx = int(selection) - 1
                                    log_group_name = api_log_groups[idx]['logGroupName']
                                except (ValueError, IndexError):
                                    log_group_name = selection
                            else:
                                log_group_name = input("Enter CloudWatch log group name: ")

                        # Fetch logs using the fetch_logs_from_cloudwatch function
                        # This handles fetching, parsing, raw logs export, and database storage
                        fetch_logs_from_cloudwatch(
                            db_manager,
                            log_group_name,
                            start_time,
                            end_time,
                            raw_logs_dir='raw-logs',
                            region=log_group_region
                        )

                    elif log_choice == '2':
                        # S3
                        bucket = input("\nEnter S3 bucket name: ")
                        prefix = input("Enter S3 key prefix (or press Enter for root): ").strip() or ""

                        fetch_logs_from_s3(db_manager, bucket, prefix, start_time, end_time, 'raw-logs')

                    else:
                        print("❌ Invalid choice")

                elif choice == '3':
                    # View Current Inventory
                    display_web_acl_summary(db_manager)

                elif choice == '4':
                    # Generate Excel Report
                    stats = db_manager.get_database_stats()
                    if stats.get('web_acls', 0) == 0:
                        print("\n⚠️  No data found in database.")
                        print("Please fetch WAF configurations first (Option 1)")
                        continue

                    # Auto-generate output filename
                    timestamp = format_datetime(datetime.now(), 'filename')
                    output_path = f"output/{account_identifier}_{timestamp}_waf_report.xlsx"

                    # Get list of Web ACLs for selection
                    conn = db_manager.get_connection()
                    web_acls = conn.execute("SELECT web_acl_id, name, scope FROM web_acls ORDER BY name").fetchall()

                    if not web_acls:
                        print("\n⚠️  No Web ACLs found in database.")
                        print("Please fetch WAF configurations first (Option 1)")
                        continue

                    # Display Web ACLs and let user select
                    print("\n📋 Available Web ACLs:")
                    print("="*80)
                    for idx, (web_acl_id, name, scope) in enumerate(web_acls, 1):
                        print(f"{idx}. {name} (Scope: {scope})")
                    print(f"{len(web_acls) + 1}. All Web ACLs")
                    print("="*80)

                    while True:
                        choice_input = input(f"\nSelect Web ACL to export (1-{len(web_acls) + 1}): ").strip()
                        try:
                            selection = int(choice_input)
                            if 1 <= selection <= len(web_acls) + 1:
                                break
                            else:
                                print(f"❌ Please enter a number between 1 and {len(web_acls) + 1}")
                        except ValueError:
                            print("❌ Please enter a valid number")

                    # Determine which Web ACL(s) to export
                    if selection == len(web_acls) + 1:
                        # Export all Web ACLs
                        selected_web_acl_ids = None
                        print(f"\n📊 Generating report for all Web ACLs...")
                    else:
                        # Export specific Web ACL
                        selected_web_acl_id = web_acls[selection - 1][0]
                        selected_web_acl_name = web_acls[selection - 1][1]
                        selected_web_acl_ids = [selected_web_acl_id]
                        print(f"\n📊 Generating report for Web ACL: {selected_web_acl_name}...")

                    generate_excel_report(db_manager, output_path, selected_web_acl_ids)

                    print(f"\n✓ Excel report generated: {output_path}")
                    print("\nNext steps:")
                    print("1. Review the Excel report for security insights")
                    print("2. Use LLM prompt templates in config/prompts/ for AI analysis")
                    print("3. Populate the 'LLM Recommendations' sheet with AI-generated insights")

                elif choice == '5':
                    # View Database Statistics
                    stats = db_manager.get_database_stats()
                    print("\n" + "="*80)
                    print("📊 Database Statistics")
                    print("="*80)
                    for table, count in stats.items():
                        print(f"{table:30s}: {count:>10,} records")
                    print("="*80)

                else:
                    print("❌ Invalid choice. Please enter 0-5.")

        # Non-interactive mode: Traditional CLI workflow
        else:
            # Fetch WAF configurations
            if not args.skip_config:
                scope = args.scope or 'REGIONAL'
                fetch_waf_configurations(db_manager, scope=scope, interactive=False)

                # Also fetch CloudFront if in us-east-1 and not explicitly specified
                if scope == 'REGIONAL' and args.scope is None and get_current_region() == 'us-east-1':
                    response = input("Would you like to also fetch CloudFront WAF ACLs? (y/n): ")
                    if response.lower() == 'y':
                        fetch_waf_configurations(db_manager, scope='CLOUDFRONT', interactive=False)

            # Fetch logs
            if not args.skip_logs:
                # Get time window
                months = args.months or 3
                start_time, end_time = get_time_window(months)

                if args.log_source == 'cloudwatch':
                    if not args.log_group:
                        # List available log groups
                        fetcher = CloudWatchFetcher()
                        log_groups = fetcher.list_log_groups(prefix='aws-waf-logs')

                        if log_groups:
                            print("\nAvailable WAF log groups:")
                            for idx, lg in enumerate(log_groups, 1):
                                print(f"{idx}. {lg['logGroupName']}")

                            selection = input("\nEnter log group number or full name: ")
                            try:
                                idx = int(selection) - 1
                                log_group_name = log_groups[idx]['logGroupName']
                            except (ValueError, IndexError):
                                log_group_name = selection
                        else:
                            log_group_name = input("Enter CloudWatch log group name: ")
                    else:
                        log_group_name = args.log_group

                    fetch_logs_from_cloudwatch(db_manager, log_group_name, start_time, end_time, dir_paths.get('raw_logs'))

                elif args.log_source == 's3':
                    bucket = args.s3_bucket or input("Enter S3 bucket name: ")
                    prefix = args.s3_prefix or input("Enter S3 key prefix: ")

                    fetch_logs_from_s3(db_manager, bucket, prefix, start_time, end_time, 'raw-logs')

                else:
                    logger.error("Log source not specified. Use --log-source cloudwatch or --log-source s3")
                    return 1

            # Show database statistics
            stats = db_manager.get_database_stats()
            logger.info("Database statistics:")
            for table, count in stats.items():
                logger.info(f"  {table}: {count:,} records")

            # Generate Excel report
            if args.output:
                output_path = args.output
            else:
                timestamp = format_datetime(datetime.now(), 'filename')
                output_path = f"output/{account_identifier}_{timestamp}_waf_report.xlsx"

            generate_excel_report(db_manager, output_path)

            # Show summary
            print("\n" + "="*60)
            print("Analysis Complete!")
            print("="*60)
            print(f"Database: {args.db_path}")
            print(f"Excel Report: {output_path}")
            print("\nNext steps:")
            print("1. Review the Excel report for security insights")
            print("2. Use LLM prompt templates in config/prompts/ for AI analysis")
            print("3. Populate the 'LLM Recommendations' sheet with AI-generated insights")
            print("="*60)

        return 0

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

    finally:
        db_manager.close()


if __name__ == '__main__':
    sys.exit(main())
