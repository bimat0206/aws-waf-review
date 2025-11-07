"""
WAF Log Parser

This module parses AWS WAF logs from various sources (CloudWatch, S3) and
normalizes them according to the official WAF log schema.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from utils.time_helpers import parse_iso_timestamp, timestamp_to_datetime

logger = logging.getLogger(__name__)


class WAFLogParser:
    """
    Parses and normalizes AWS WAF log entries.
    """

    def __init__(self, schema_path: str = "config/waf_schema.json"):
        """
        Initialize the WAF log parser.

        Args:
            schema_path (str): Path to the WAF schema JSON file
        """
        self.schema = self._load_schema(schema_path)
        self.required_fields = self.schema.get('required_fields', [])
        self.security_fields = self.schema.get('security_fields', [])
        self.action_values = self.schema.get('action_values', [])
        logger.info("WAF log parser initialized")

    def _load_schema(self, schema_path: str) -> Dict[str, Any]:
        """
        Load the WAF log schema from JSON file.

        Args:
            schema_path (str): Path to schema file

        Returns:
            Dict[str, Any]: Schema definition
        """
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            logger.info(f"Loaded WAF schema from {schema_path}")
            return schema
        except FileNotFoundError:
            logger.warning(f"Schema file not found: {schema_path}, using defaults")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing schema file: {e}")
            return {}

    def parse_cloudwatch_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a log event from CloudWatch Logs.

        Args:
            event (Dict[str, Any]): Raw CloudWatch log event

        Returns:
            Optional[Dict[str, Any]]: Parsed and normalized log entry
        """
        try:
            # CloudWatch events have 'message' field with JSON content
            message = event.get('message', '')

            if not message:
                logger.warning("Empty message in CloudWatch event")
                return None

            # Parse the JSON message
            log_entry = json.loads(message)

            # Add CloudWatch metadata
            log_entry['_source'] = 'cloudwatch'
            log_entry['_event_id'] = event.get('eventId')
            log_entry['_ingestion_time'] = event.get('ingestionTime')

            # Normalize the entry
            return self.normalize_log_entry(log_entry)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CloudWatch event message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing CloudWatch event: {e}")
            return None

    def parse_s3_log_entry(self, log_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a log entry from S3.

        Args:
            log_entry (Dict[str, Any]): Raw S3 log entry

        Returns:
            Optional[Dict[str, Any]]: Parsed and normalized log entry
        """
        try:
            # S3 logs are already in JSON format
            log_entry['_source'] = 's3'

            # Normalize the entry
            return self.normalize_log_entry(log_entry)

        except Exception as e:
            logger.error(f"Error parsing S3 log entry: {e}")
            return None

    def normalize_log_entry(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a WAF log entry according to the schema.

        Args:
            log_entry (Dict[str, Any]): Raw log entry

        Returns:
            Dict[str, Any]: Normalized log entry
        """
        normalized = {}

        # Parse timestamp
        timestamp = log_entry.get('timestamp')
        if timestamp:
            if isinstance(timestamp, int):
                normalized['timestamp'] = timestamp_to_datetime(timestamp)
            elif isinstance(timestamp, str):
                normalized['timestamp'] = parse_iso_timestamp(timestamp)
            else:
                normalized['timestamp'] = timestamp
        else:
            logger.warning("Missing timestamp in log entry")
            normalized['timestamp'] = datetime.utcnow()

        # Extract action
        action = log_entry.get('action', '')
        if action in self.action_values:
            normalized['action'] = action
        else:
            logger.warning(f"Unknown action value: {action}")
            normalized['action'] = action or 'UNKNOWN'

        # Extract Web ACL information
        normalized['webaclId'] = log_entry.get('webaclId') or log_entry.get('webAclId')
        normalized['webaclName'] = log_entry.get('webaclName') or log_entry.get('webAclName')

        # Extract HTTP request information
        http_request = log_entry.get('httpRequest', {})

        normalized['clientIp'] = http_request.get('clientIp') or log_entry.get('clientIp')
        normalized['country'] = http_request.get('country') or log_entry.get('country')
        normalized['uri'] = http_request.get('uri') or log_entry.get('uri')
        normalized['httpMethod'] = http_request.get('httpMethod') or log_entry.get('httpMethod')
        normalized['httpVersion'] = http_request.get('httpVersion') or log_entry.get('httpVersion')

        # Extract headers
        headers = http_request.get('headers', [])
        normalized['httpRequest'] = http_request
        normalized['requestHeaders'] = headers

        # Find User-Agent header
        for header in headers:
            if header.get('name', '').lower() == 'user-agent':
                normalized['userAgent'] = header.get('value')
                break

        # Extract HTTP status
        normalized['httpStatus'] = log_entry.get('httpStatus')
        normalized['responseCodeSent'] = log_entry.get('responseCodeSent')

        # Extract terminating rule information
        normalized['terminatingRuleId'] = log_entry.get('terminatingRuleId')
        normalized['terminatingRuleType'] = log_entry.get('terminatingRuleType')
        normalized['terminatingRuleMatchDetails'] = log_entry.get('terminatingRuleMatchDetails')

        # Extract rule group information
        normalized['ruleGroupList'] = log_entry.get('ruleGroupList', [])
        normalized['rateBasedRuleList'] = log_entry.get('rateBasedRuleList', [])
        normalized['nonTerminatingMatchingRules'] = log_entry.get('nonTerminatingMatchingRules', [])

        # Extract labels
        normalized['labels'] = log_entry.get('labels', [])

        # Extract fingerprints
        normalized['ja3Fingerprint'] = log_entry.get('ja3Fingerprint')
        normalized['ja4Fingerprint'] = log_entry.get('ja4Fingerprint')

        # Extract HTTP source information
        normalized['httpSourceName'] = log_entry.get('httpSourceName')
        normalized['httpSourceId'] = log_entry.get('httpSourceId')

        # Store the complete raw log for reference
        normalized['_raw'] = log_entry

        # Add metadata
        normalized['_source'] = log_entry.get('_source', 'unknown')

        return normalized

    def parse_batch(self, log_entries: List[Dict[str, Any]],
                   source: str = 'unknown') -> List[Dict[str, Any]]:
        """
        Parse a batch of log entries.

        Args:
            log_entries (List[Dict[str, Any]]): List of raw log entries
            source (str): Source of the logs ('cloudwatch' or 's3')

        Returns:
            List[Dict[str, Any]]: List of parsed log entries
        """
        logger.info(f"Parsing batch of {len(log_entries)} log entries from {source}")

        parsed_entries = []
        errors = 0

        for entry in log_entries:
            try:
                if source == 'cloudwatch':
                    parsed = self.parse_cloudwatch_event(entry)
                elif source == 's3':
                    parsed = self.parse_s3_log_entry(entry)
                else:
                    parsed = self.normalize_log_entry(entry)

                if parsed:
                    parsed_entries.append(parsed)
                else:
                    errors += 1

            except Exception as e:
                logger.error(f"Error parsing log entry: {e}")
                errors += 1

        logger.info(f"Successfully parsed {len(parsed_entries)} entries, {errors} errors")
        return parsed_entries

    def validate_log_entry(self, log_entry: Dict[str, Any]) -> bool:
        """
        Validate a log entry against the schema.

        Args:
            log_entry (Dict[str, Any]): Log entry to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Check required fields
        for field in self.required_fields:
            # Handle nested fields (e.g., httpRequest.clientIp)
            if '.' in field:
                parts = field.split('.')
                value = log_entry
                for part in parts:
                    value = value.get(part, {})
                    if not value:
                        break

                if not value:
                    logger.warning(f"Missing required field: {field}")
                    return False
            else:
                if field not in log_entry or log_entry[field] is None:
                    logger.warning(f"Missing required field: {field}")
                    return False

        # Validate action value
        action = log_entry.get('action')
        if action and action not in self.action_values:
            logger.warning(f"Invalid action value: {action}")
            return False

        return True

    def extract_attack_type(self, log_entry: Dict[str, Any]) -> str:
        """
        Determine the type of attack from a blocked request.

        Args:
            log_entry (Dict[str, Any]): Parsed log entry

        Returns:
            str: Attack type classification
        """
        if log_entry.get('action') != 'BLOCK':
            return 'N/A'

        terminating_rule = log_entry.get('terminatingRuleId', '').lower()

        # Common attack type patterns in rule IDs
        if 'sqli' in terminating_rule or 'sql' in terminating_rule:
            return 'SQL Injection'
        elif 'xss' in terminating_rule:
            return 'Cross-Site Scripting'
        elif 'rfi' in terminating_rule or 'lfi' in terminating_rule:
            return 'File Inclusion'
        elif 'rce' in terminating_rule or 'command' in terminating_rule:
            return 'Remote Code Execution'
        elif 'scanner' in terminating_rule or 'recon' in terminating_rule:
            return 'Scanner/Reconnaissance'
        elif 'bot' in terminating_rule:
            return 'Bot Traffic'
        elif 'geo' in terminating_rule:
            return 'Geographic Block'
        elif 'rate' in terminating_rule:
            return 'Rate Limiting'
        elif 'ip' in terminating_rule:
            return 'IP Reputation'
        else:
            return 'Other'

    def extract_rule_groups_hit(self, log_entry: Dict[str, Any]) -> List[str]:
        """
        Extract the names of rule groups that were hit.

        Args:
            log_entry (Dict[str, Any]): Parsed log entry

        Returns:
            List[str]: List of rule group names
        """
        rule_groups = []

        rule_group_list = log_entry.get('ruleGroupList', [])
        for rg in rule_group_list:
            if isinstance(rg, dict):
                name = rg.get('ruleGroupId') or rg.get('ruleGroupName')
                if name:
                    rule_groups.append(name)

        return rule_groups

    def get_log_summary(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of parsed log entries.

        Args:
            log_entries (List[Dict[str, Any]]): List of parsed log entries

        Returns:
            Dict[str, Any]: Summary statistics
        """
        if not log_entries:
            return {
                'total_entries': 0,
                'actions': {},
                'unique_ips': 0,
                'unique_countries': 0,
                'time_range': None
            }

        actions = {}
        ips = set()
        countries = set()
        timestamps = []

        for entry in log_entries:
            # Count actions
            action = entry.get('action', 'UNKNOWN')
            actions[action] = actions.get(action, 0) + 1

            # Collect unique IPs
            client_ip = entry.get('clientIp')
            if client_ip:
                ips.add(client_ip)

            # Collect unique countries
            country = entry.get('country')
            if country:
                countries.add(country)

            # Collect timestamps
            timestamp = entry.get('timestamp')
            if timestamp:
                timestamps.append(timestamp)

        # Determine time range
        time_range = None
        if timestamps:
            timestamps.sort()
            time_range = {
                'start': timestamps[0],
                'end': timestamps[-1]
            }

        summary = {
            'total_entries': len(log_entries),
            'actions': actions,
            'unique_ips': len(ips),
            'unique_countries': len(countries),
            'time_range': time_range,
            'block_rate': round(actions.get('BLOCK', 0) / len(log_entries) * 100, 2) if log_entries else 0
        }

        return summary
