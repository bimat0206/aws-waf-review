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
from datetime import datetime
from pathlib import Path
import coloredlogs

from storage.duckdb_manager import DuckDBManager
from fetchers.cloudwatch_fetcher import CloudWatchFetcher
from fetchers.s3_fetcher import S3Fetcher
from processors.config_processor import WAFConfigProcessor
from processors.log_parser import WAFLogParser
from processors.metrics_calculator import MetricsCalculator
from reporters.excel_generator import ExcelReportGenerator
from utils.aws_helpers import (
    verify_aws_credentials,
    get_session_info,
    get_current_region
)
from utils.time_helpers import (
    get_time_window,
    format_datetime,
    get_time_window_description
)

# Setup logging
logger = logging.getLogger(__name__)
coloredlogs.install(
    level='INFO',
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


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
    logger.info(f"AWS Account: {session_info.get('account_id')}")
    logger.info(f"IAM Identity: {session_info.get('arn')}")

    return True


def fetch_waf_configurations(db_manager: DuckDBManager, scope: str = 'REGIONAL'):
    """
    Fetch WAF configurations and store in database.

    Args:
        db_manager (DuckDBManager): Database manager instance
        scope (str): WAF scope - 'REGIONAL' or 'CLOUDFRONT'
    """
    logger.info(f"Fetching WAF configurations for {scope} scope...")

    processor = WAFConfigProcessor(scope=scope)

    # Get all Web ACLs
    web_acl_configs = processor.get_all_web_acl_configs()

    if not web_acl_configs:
        logger.warning(f"No Web ACLs found in {scope} scope")
        return

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


def fetch_logs_from_cloudwatch(db_manager: DuckDBManager, log_group_name: str,
                               start_time: datetime, end_time: datetime):
    """
    Fetch logs from CloudWatch and store in database.

    Args:
        db_manager (DuckDBManager): Database manager instance
        log_group_name (str): CloudWatch log group name
        start_time (datetime): Start of time range
        end_time (datetime): End of time range
    """
    logger.info(f"Fetching logs from CloudWatch: {log_group_name}")
    logger.info(f"Time range: {get_time_window_description(start_time, end_time)}")

    fetcher = CloudWatchFetcher()
    parser = WAFLogParser()

    # Fetch logs
    log_events = fetcher.get_log_events(log_group_name, start_time, end_time)

    if not log_events:
        logger.warning("No log events found in CloudWatch")
        return

    logger.info(f"Fetched {len(log_events)} log events")

    # Parse logs
    parsed_logs = parser.parse_batch(log_events, source='cloudwatch')

    if not parsed_logs:
        logger.warning("No logs were successfully parsed")
        return

    # Store in database
    db_manager.insert_log_entries(parsed_logs)

    logger.info(f"Successfully stored {len(parsed_logs)} log entries")


def fetch_logs_from_s3(db_manager: DuckDBManager, bucket: str, prefix: str,
                      start_time: datetime, end_time: datetime):
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


def generate_excel_report(db_manager: DuckDBManager, output_path: str):
    """
    Generate Excel report with visualizations.

    Args:
        db_manager (DuckDBManager): Database manager instance
        output_path (str): Path to save Excel report
    """
    logger.info("Generating Excel report...")

    # Calculate metrics
    calculator = MetricsCalculator(db_manager)
    metrics = calculator.calculate_all_metrics()

    # Get Web ACL data
    conn = db_manager.get_connection()

    web_acls = conn.execute("SELECT * FROM web_acls").fetchall()
    web_acls_list = [dict(zip(['web_acl_id', 'name', 'scope', 'default_action', 'description',
                               'visibility_config', 'capacity', 'managed_by_firewall_manager',
                               'created_at', 'updated_at'], row)) for row in web_acls]

    resources = conn.execute("SELECT * FROM resource_associations").fetchall()
    resources_list = [dict(zip(['association_id', 'web_acl_id', 'resource_arn',
                                'resource_type', 'created_at'], row)) for row in resources]

    # Get Web ACL names for resources
    web_acl_names = {acl['web_acl_id']: acl['name'] for acl in web_acls_list}
    for resource in resources_list:
        resource['web_acl_name'] = web_acl_names.get(resource['web_acl_id'], 'Unknown')

    logging_configs = conn.execute("SELECT * FROM logging_configurations").fetchall()
    logging_configs_list = [dict(zip(['config_id', 'web_acl_id', 'destination_type',
                                     'destination_arn', 'log_format', 'sampling_rate',
                                     'redacted_fields', 'created_at'], row)) for row in logging_configs]

    # Generate report
    generator = ExcelReportGenerator(output_path)
    generator.generate_report(metrics, web_acls_list, resources_list, logging_configs_list)

    logger.info(f"Excel report generated: {output_path}")


def main():
    """Main execution function."""
    print_banner()

    # Parse arguments
    parser = argparse.ArgumentParser(description='AWS WAF Security Analysis Tool')
    parser.add_argument('--db-path', default='waf_analysis.duckdb',
                       help='Path to DuckDB database file')
    parser.add_argument('--months', type=int, default=3, choices=[3, 6],
                       help='Number of months of logs to analyze (3 or 6)')
    parser.add_argument('--scope', choices=['REGIONAL', 'CLOUDFRONT'], default='REGIONAL',
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
    parser.add_argument('--output', help='Output Excel report filename')

    args = parser.parse_args()

    # Verify environment
    if not verify_environment():
        return 1

    # Initialize database
    logger.info("Initializing database...")
    db_manager = DuckDBManager(args.db_path)
    db_manager.initialize_database()

    try:
        # Fetch WAF configurations
        if not args.skip_config:
            fetch_waf_configurations(db_manager, scope=args.scope)

            # Also fetch CloudFront WAF ACLs if in us-east-1
            if args.scope == 'REGIONAL' and get_current_region() == 'us-east-1':
                response = input("Would you like to also fetch CloudFront WAF ACLs? (y/n): ")
                if response.lower() == 'y':
                    fetch_waf_configurations(db_manager, scope='CLOUDFRONT')

        # Fetch logs
        if not args.skip_logs:
            # Get time window
            start_time, end_time = get_time_window(args.months)

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

                fetch_logs_from_cloudwatch(db_manager, log_group_name, start_time, end_time)

            elif args.log_source == 's3':
                bucket = args.s3_bucket or input("Enter S3 bucket name: ")
                prefix = args.s3_prefix or input("Enter S3 key prefix: ")

                fetch_logs_from_s3(db_manager, bucket, prefix, start_time, end_time)

            else:
                # Ask user for log source
                print("\nSelect log source:")
                print("1. CloudWatch Logs")
                print("2. S3")
                choice = input("Enter choice (1 or 2): ")

                if choice == '1':
                    # List available log groups
                    fetcher = CloudWatchFetcher()
                    log_groups = fetcher.list_log_groups(prefix='aws-waf-logs')

                    if log_groups:
                        print("\nAvailable WAF log groups:")
                        for idx, lg in enumerate(log_groups, 1):
                            print(f"{idx}. {lg['logGroupName']}")

                        selection = input("\nEnter log group number: ")
                        try:
                            idx = int(selection) - 1
                            log_group_name = log_groups[idx]['logGroupName']
                        except (ValueError, IndexError):
                            logger.error("Invalid selection")
                            return 1
                    else:
                        log_group_name = input("Enter CloudWatch log group name: ")

                    fetch_logs_from_cloudwatch(db_manager, log_group_name, start_time, end_time)

                elif choice == '2':
                    bucket = input("Enter S3 bucket name: ")
                    prefix = input("Enter S3 key prefix: ")

                    fetch_logs_from_s3(db_manager, bucket, prefix, start_time, end_time)

                else:
                    logger.error("Invalid choice")
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
            output_path = f"waf_report_{timestamp}.xlsx"

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
