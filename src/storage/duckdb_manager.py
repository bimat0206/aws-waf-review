"""
DuckDB Database Manager

This module manages all DuckDB database operations including schema creation,
data insertion, and query execution for AWS WAF analysis data.
"""

import duckdb
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime objects.
    Converts datetime objects to ISO 8601 format strings.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class DuckDBManager:
    """
    Manages DuckDB database operations for WAF analysis.
    """

    def __init__(self, db_path: str = "waf_analysis.duckdb"):
        """
        Initialize the DuckDB manager.

        Args:
            db_path (str): Path to the DuckDB database file
        """
        self.db_path = db_path
        self.connection = None
        logger.info(f"Initializing DuckDB manager with database: {db_path}")

    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        Establish connection to the DuckDB database.

        Returns:
            duckdb.DuckDBPyConnection: Database connection object
        """
        if self.connection is None:
            self.connection = duckdb.connect(self.db_path)
            logger.info(f"Connected to DuckDB database: {self.db_path}")
        return self.connection

    def close(self) -> None:
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("DuckDB connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def initialize_database(self) -> None:
        """
        Create all necessary tables and indexes for WAF analysis.
        """
        logger.info("Initializing database schema...")

        conn = self.connect()

        # Create web_acls table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS web_acls (
                web_acl_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                scope TEXT NOT NULL,
                default_action TEXT,
                description TEXT,
                visibility_config TEXT,
                capacity BIGINT,
                managed_by_firewall_manager BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        logger.info("Created table: web_acls")

        # Create resource_associations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resource_associations (
                association_id TEXT PRIMARY KEY,
                web_acl_id TEXT NOT NULL,
                resource_arn TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (web_acl_id) REFERENCES web_acls(web_acl_id)
            )
        """)
        logger.info("Created table: resource_associations")

        # Create logging_configurations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logging_configurations (
                config_id TEXT PRIMARY KEY,
                web_acl_id TEXT NOT NULL,
                destination_type TEXT NOT NULL,
                destination_arn TEXT NOT NULL,
                log_format TEXT,
                sampling_rate FLOAT,
                redacted_fields TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (web_acl_id) REFERENCES web_acls(web_acl_id)
            )
        """)
        logger.info("Created table: logging_configurations")

        # Create waf_logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS waf_logs (
                log_id BIGINT PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                web_acl_id TEXT,
                web_acl_name TEXT,
                action TEXT NOT NULL,
                client_ip TEXT,
                country TEXT,
                uri TEXT,
                http_method TEXT,
                http_version TEXT,
                http_status INTEGER,
                terminating_rule_id TEXT,
                terminating_rule_type TEXT,
                terminating_rule_match_details TEXT,
                rule_group_list TEXT,
                rate_based_rule_list TEXT,
                non_terminating_matching_rules TEXT,
                labels TEXT,
                ja3_fingerprint TEXT,
                ja4_fingerprint TEXT,
                user_agent TEXT,
                request_headers TEXT,
                response_code_sent INTEGER,
                http_source_name TEXT,
                http_source_id TEXT,
                raw_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created table: waf_logs")

        # Create rules table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                rule_id TEXT PRIMARY KEY,
                web_acl_id TEXT NOT NULL,
                name TEXT NOT NULL,
                priority INTEGER NOT NULL,
                rule_type TEXT NOT NULL,
                action TEXT,
                visibility_config TEXT,
                statement TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (web_acl_id) REFERENCES web_acls(web_acl_id)
            )
        """)
        logger.info("Created table: rules")

        # Create indexes for performance
        logger.info("Creating indexes...")

        # Single column indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON waf_logs(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_web_acl ON waf_logs(web_acl_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_action ON waf_logs(action)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_client_ip ON waf_logs(client_ip)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_country ON waf_logs(country)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_terminating_rule ON waf_logs(terminating_rule_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_associations_web_acl ON resource_associations(web_acl_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_web_acl ON rules(web_acl_id)")
        
        # Composite indexes for common query patterns
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_action_timestamp ON waf_logs(action, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_web_acl_action ON waf_logs(web_acl_id, action)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_client_ip_timestamp ON waf_logs(client_ip, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_country_action ON waf_logs(country, action)")

        logger.info("Database initialization complete")

    def insert_web_acl(self, web_acl_data: Dict[str, Any]) -> None:
        """
        Insert or update a Web ACL configuration.

        Args:
            web_acl_data (Dict[str, Any]): Web ACL configuration data
        """
        conn = self.connect()

        web_acl_id = web_acl_data.get('Id') or web_acl_data.get('web_acl_id')
        name = web_acl_data.get('Name') or web_acl_data.get('name')
        scope = web_acl_data.get('Scope') or web_acl_data.get('scope')

        conn.execute("""
            INSERT INTO web_acls (
                web_acl_id, name, scope, default_action, description,
                visibility_config, capacity, managed_by_firewall_manager,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (web_acl_id) DO UPDATE SET
                name = EXCLUDED.name,
                scope = EXCLUDED.scope,
                default_action = EXCLUDED.default_action,
                description = EXCLUDED.description,
                visibility_config = EXCLUDED.visibility_config,
                capacity = EXCLUDED.capacity,
                managed_by_firewall_manager = EXCLUDED.managed_by_firewall_manager,
                updated_at = EXCLUDED.updated_at
        """, [
            web_acl_id,
            name,
            scope,
            json.dumps(web_acl_data.get('DefaultAction', {})),
            web_acl_data.get('Description', ''),
            json.dumps(web_acl_data.get('VisibilityConfig', {})),
            web_acl_data.get('Capacity', 0),
            web_acl_data.get('ManagedByFirewallManager', False),
            web_acl_data.get('CreatedAt') or datetime.utcnow(),
            datetime.utcnow()
        ])

        logger.info(f"Inserted Web ACL: {name} ({web_acl_id})")

    def insert_rules(self, web_acl_id: str, rules: List[Dict[str, Any]]) -> None:
        """
        Insert rules for a Web ACL.

        Args:
            web_acl_id (str): Web ACL ID
            rules (List[Dict[str, Any]]): List of rule configurations
        """
        conn = self.connect()

        for rule in rules:
            rule_id = f"{web_acl_id}_{rule.get('Name', 'unknown')}"

            conn.execute("""
                INSERT INTO rules (
                    rule_id, web_acl_id, name, priority, rule_type,
                    action, visibility_config, statement, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (rule_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    priority = EXCLUDED.priority,
                    rule_type = EXCLUDED.rule_type,
                    action = EXCLUDED.action,
                    visibility_config = EXCLUDED.visibility_config,
                    statement = EXCLUDED.statement,
                    created_at = EXCLUDED.created_at
            """, [
                rule_id,
                web_acl_id,
                rule.get('Name', ''),
                rule.get('Priority', 0),
                rule.get('Type', 'REGULAR'),
                json.dumps(rule.get('Action', {})),
                json.dumps(rule.get('VisibilityConfig', {})),
                json.dumps(rule.get('Statement', {})),
                datetime.utcnow()
            ])

        logger.info(f"Inserted {len(rules)} rules for Web ACL: {web_acl_id}")

    def insert_resource_association(self, web_acl_id: str, resource_arn: str,
                                   resource_type: str) -> None:
        """
        Insert a resource association for a Web ACL.

        Args:
            web_acl_id (str): Web ACL ID
            resource_arn (str): Resource ARN
            resource_type (str): Type of resource (ALB, API_GATEWAY, CLOUDFRONT)
        """
        conn = self.connect()

        association_id = f"{web_acl_id}_{resource_arn}"

        conn.execute("""
            INSERT INTO resource_associations (
                association_id, web_acl_id, resource_arn, resource_type, created_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (association_id) DO UPDATE SET
                resource_type = EXCLUDED.resource_type,
                created_at = EXCLUDED.created_at
        """, [association_id, web_acl_id, resource_arn, resource_type, datetime.utcnow()])

        logger.debug(f"Inserted resource association: {resource_type} - {resource_arn}")

    def insert_logging_configuration(self, web_acl_id: str, logging_config: Dict[str, Any]) -> None:
        """
        Insert logging configuration for a Web ACL.

        Args:
            web_acl_id (str): Web ACL ID
            logging_config (Dict[str, Any]): Logging configuration data
        """
        conn = self.connect()

        destinations = logging_config.get('LogDestinationConfigs', [])

        for dest in destinations:
            # Determine destination type from ARN
            if 'logs:' in dest:
                dest_type = 'CLOUDWATCH'
            elif 's3:' in dest:
                dest_type = 'S3'
            elif 'firehose:' in dest:
                dest_type = 'FIREHOSE'
            else:
                dest_type = 'UNKNOWN'

            config_id = f"{web_acl_id}_{dest_type}"

            conn.execute("""
                INSERT INTO logging_configurations (
                    config_id, web_acl_id, destination_type, destination_arn,
                    log_format, sampling_rate, redacted_fields, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (config_id) DO UPDATE SET
                    destination_arn = EXCLUDED.destination_arn,
                    log_format = EXCLUDED.log_format,
                    sampling_rate = EXCLUDED.sampling_rate,
                    redacted_fields = EXCLUDED.redacted_fields,
                    created_at = EXCLUDED.created_at
            """, [
                config_id,
                web_acl_id,
                dest_type,
                dest,
                logging_config.get('LogFormat', 'JSON'),
                logging_config.get('SamplingRate', 1.0),
                json.dumps(logging_config.get('RedactedFields', [])),
                datetime.utcnow()
            ])

        logger.info(f"Inserted logging configuration for Web ACL: {web_acl_id}")

    def insert_log_entries(self, log_entries: List[Dict[str, Any]]) -> int:
        """
        Bulk insert WAF log entries.

        Args:
            log_entries (List[Dict[str, Any]]): List of parsed log entries

        Returns:
            int: Number of records inserted
        """
        if not log_entries:
            logger.warning("No log entries to insert")
            return 0

        conn = self.connect()

        # Determine starting log_id to avoid primary key collisions
        try:
            current_max = conn.execute("SELECT COALESCE(MAX(log_id), -1) FROM waf_logs").fetchone()[0]
        except Exception as e:
            logger.warning(f"Failed to read current max log_id: {e}, defaulting to -1")
            current_max = -1

        if current_max is None:
            current_max = -1

        start_id = (current_max or 0) + 1 if current_max >= 0 else 0

        # Prepare data for bulk insert
        insert_data = []
        for idx, entry in enumerate(log_entries):
            insert_data.append([
                start_id + idx,
                entry.get('timestamp'),
                entry.get('webaclId'),
                entry.get('webaclName'),
                entry.get('action'),
                entry.get('clientIp') or entry.get('httpRequest', {}).get('clientIp'),
                entry.get('country') or entry.get('httpRequest', {}).get('country'),
                entry.get('uri') or entry.get('httpRequest', {}).get('uri'),
                entry.get('httpMethod') or entry.get('httpRequest', {}).get('httpMethod'),
                entry.get('httpVersion') or entry.get('httpRequest', {}).get('httpVersion'),
                entry.get('httpStatus'),
                entry.get('terminatingRuleId'),
                entry.get('terminatingRuleType'),
                json.dumps(entry.get('terminatingRuleMatchDetails'), cls=DateTimeEncoder),
                json.dumps(entry.get('ruleGroupList', []), cls=DateTimeEncoder),
                json.dumps(entry.get('rateBasedRuleList', []), cls=DateTimeEncoder),
                json.dumps(entry.get('nonTerminatingMatchingRules', []), cls=DateTimeEncoder),
                json.dumps(entry.get('labels', []), cls=DateTimeEncoder),
                entry.get('ja3Fingerprint'),
                entry.get('ja4Fingerprint'),
                # Extract user agent from headers if present - more efficient approach
                (lambda headers: next((header.get('value') for header in headers if header.get('name', '').lower() == 'user-agent'), None))(entry.get('httpRequest', {}).get('headers', [])),
                json.dumps(entry.get('httpRequest', {}).get('headers', []), cls=DateTimeEncoder),
                entry.get('responseCodeSent'),
                entry.get('httpSourceName'),
                entry.get('httpSourceId'),
                json.dumps(entry, cls=DateTimeEncoder),
                datetime.utcnow()
            ])

        # Use executemany for bulk insert
        conn.executemany("""
            INSERT INTO waf_logs (
                log_id, timestamp, web_acl_id, web_acl_name, action,
                client_ip, country, uri, http_method, http_version, http_status,
                terminating_rule_id, terminating_rule_type, terminating_rule_match_details,
                rule_group_list, rate_based_rule_list, non_terminating_matching_rules,
                labels, ja3_fingerprint, ja4_fingerprint, user_agent, request_headers,
                response_code_sent, http_source_name, http_source_id, raw_log, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, insert_data)

        logger.info(f"Inserted {len(log_entries)} log entries")
        return len(log_entries)

    def execute_query(self, query: str, params: Optional[List] = None) -> duckdb.DuckDBPyRelation:
        """
        Execute a SQL query and return results.

        Args:
            query (str): SQL query string
            params (Optional[List]): Query parameters

        Returns:
            duckdb.DuckDBPyRelation: Query results
        """
        conn = self.connect()
        logger.debug(f"Executing query: {query[:100]}...")

        if params:
            result = conn.execute(query, params)
        else:
            result = conn.execute(query)

        return result

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get the database connection.

        Returns:
            duckdb.DuckDBPyConnection: Database connection
        """
        return self.connect()

    def get_table_count(self, table_name: str) -> int:
        """
        Get the number of records in a table.

        Args:
            table_name (str): Name of the table

        Returns:
            int: Number of records
        """
        result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        count = result.fetchone()[0]
        logger.info(f"Table '{table_name}' has {count} records")
        return count

    def get_database_stats(self) -> Dict[str, int]:
        """
        Get statistics about the database.

        Returns:
            Dict[str, int]: Dictionary with table names and record counts
        """
        tables = ['web_acls', 'resource_associations', 'logging_configurations', 'waf_logs', 'rules']
        stats = {}

        for table in tables:
            try:
                stats[table] = self.get_table_count(table)
            except Exception as e:
                logger.warning(f"Could not get count for table {table}: {e}")
                stats[table] = 0

        return stats

    def vacuum(self) -> None:
        """
        Optimize the database by running VACUUM.
        """
        logger.info("Running VACUUM to optimize database...")
        conn = self.connect()
        conn.execute("VACUUM")
        logger.info("Database optimization complete")

    def migrate_web_acl_ids(self) -> int:
        """
        Migrate existing log entries to extract Web ACL ID from ARN format.
        This fixes the issue where log entries stored full ARN instead of just the ID,
        which caused joins with web_acls table to fail.

        Returns:
            int: Number of records updated
        """
        logger.info("Starting Web ACL ID migration...")
        conn = self.connect()
        
        try:
            # Count logs with ARN format before migration
            arn_count = conn.execute("""
                SELECT COUNT(*) 
                FROM waf_logs 
                WHERE web_acl_id LIKE 'arn:aws:wafv2:%'
            """).fetchone()[0]
            
            if arn_count > 0:
                logger.info(f"Found {arn_count} log entries with ARN format, migrating...")
                # Extract just the ID part from the ARN (last segment after the final '/')
                conn.execute("""
                    UPDATE waf_logs 
                    SET web_acl_id = SPLIT_PART(web_acl_id, '/', -1)
                    WHERE web_acl_id LIKE 'arn:aws:wafv2:%'
                """)
                logger.info(f"Migrated {arn_count} log entries from ARN to ID format")
            else:
                logger.info("No log entries with ARN format found, no migration needed")
            
            return arn_count
        except Exception as e:
            logger.error(f"Error during Web ACL ID migration: {e}")
            logger.warning("Continuing without migration - existing log data may have incorrect web_acl_id format")
            return 0

    def export_to_parquet(self, table_name: str, output_path: str) -> None:
        """
        Export a table to Parquet format.

        Args:
            table_name (str): Name of the table to export
            output_path (str): Path to the output Parquet file
        """
        logger.info(f"Exporting table '{table_name}' to {output_path}")
        conn = self.connect()
        conn.execute(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)")
        logger.info(f"Export complete: {output_path}")
