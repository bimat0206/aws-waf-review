"""
Metrics Calculator

This module calculates security metrics and analytics from WAF data stored
in DuckDB. It provides methods for generating statistics, trends, and insights.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

from storage.duckdb_manager import DuckDBManager

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculates security metrics and analytics from WAF data.
    """

    def __init__(self, db_manager: DuckDBManager):
        """
        Initialize the metrics calculator.

        Args:
            db_manager (DuckDBManager): Database manager instance
        """
        self.db = db_manager
        logger.info("Metrics calculator initialized")

    def calculate_all_metrics(self) -> Dict[str, Any]:
        """
        Calculate all available metrics.

        Returns:
            Dict[str, Any]: Complete metrics dataset
        """
        logger.info("Calculating all metrics...")

        metrics = {
            'summary': self.get_summary_metrics(),
            'action_distribution': self.get_action_distribution(),
            'rule_effectiveness': self.get_rule_effectiveness(),
            'geographic_distribution': self.get_geographic_distribution(),
            'top_blocked_ips': self.get_top_blocked_ips(limit=50),
            'attack_type_distribution': self.get_attack_type_distribution(),
            'hourly_patterns': self.get_hourly_traffic_patterns(),
            'daily_trends': self.get_daily_traffic_trends(),
            'web_acl_coverage': self.get_web_acl_coverage(),
            'bot_analysis': self.get_bot_traffic_analysis()
        }

        logger.info("All metrics calculated successfully")
        return metrics

    def get_summary_metrics(self) -> Dict[str, Any]:
        """
        Get high-level summary metrics.

        Returns:
            Dict[str, Any]: Summary metrics
        """
        logger.info("Calculating summary metrics...")

        conn = self.db.get_connection()

        # Total requests
        result = conn.execute("SELECT COUNT(*) as total FROM waf_logs").fetchone()
        total_requests = result[0] if result else 0

        # Action counts
        result = conn.execute("""
            SELECT action, COUNT(*) as count
            FROM waf_logs
            GROUP BY action
        """).fetchall()

        actions = {row[0]: row[1] for row in result}

        # Time range
        result = conn.execute("""
            SELECT MIN(timestamp) as start, MAX(timestamp) as end
            FROM waf_logs
        """).fetchone()

        time_range = None
        if result and result[0]:
            time_range = {
                'start': result[0],
                'end': result[1]
            }

        # Unique clients
        result = conn.execute("""
            SELECT COUNT(DISTINCT client_ip) as unique_ips
            FROM waf_logs
            WHERE client_ip IS NOT NULL
        """).fetchone()
        unique_ips = result[0] if result else 0

        # Unique countries
        result = conn.execute("""
            SELECT COUNT(DISTINCT country) as unique_countries
            FROM waf_logs
            WHERE country IS NOT NULL AND country != '-'
        """).fetchone()
        unique_countries = result[0] if result else 0

        # Calculate block rate
        blocked = actions.get('BLOCK', 0)
        block_rate = (blocked / total_requests * 100) if total_requests > 0 else 0

        summary = {
            'total_requests': total_requests,
            'actions': actions,
            'blocked_requests': blocked,
            'allowed_requests': actions.get('ALLOW', 0),
            'block_rate_percent': round(block_rate, 2),
            'unique_client_ips': unique_ips,
            'unique_countries': unique_countries,
            'time_range': time_range
        }

        return summary

    def get_action_distribution(self) -> Dict[str, Any]:
        """
        Get distribution of WAF actions.

        Returns:
            Dict[str, Any]: Action distribution data
        """
        conn = self.db.get_connection()

        result = conn.execute("""
            SELECT action, COUNT(*) as count
            FROM waf_logs
            GROUP BY action
            ORDER BY count DESC
        """).fetchall()

        total = sum(row[1] for row in result)

        distribution = {}
        for row in result:
            action = row[0]
            count = row[1]
            percentage = (count / total * 100) if total > 0 else 0

            distribution[action] = {
                'count': count,
                'percentage': round(percentage, 2)
            }

        return distribution

    def get_rule_effectiveness(self) -> List[Dict[str, Any]]:
        """
        Calculate rule effectiveness metrics.

        Returns:
            List[Dict[str, Any]]: Rule performance metrics
        """
        logger.info("Calculating rule effectiveness...")

        conn = self.db.get_connection()

        result = conn.execute("""
            SELECT
                terminating_rule_id,
                terminating_rule_type,
                COUNT(*) as hit_count,
                COUNT(DISTINCT client_ip) as unique_ips,
                SUM(CASE WHEN action = 'BLOCK' THEN 1 ELSE 0 END) as blocks,
                SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allows,
                SUM(CASE WHEN action = 'COUNT' THEN 1 ELSE 0 END) as counts
            FROM waf_logs
            WHERE terminating_rule_id IS NOT NULL
            GROUP BY terminating_rule_id, terminating_rule_type
            ORDER BY hit_count DESC
        """).fetchall()

        total_requests = self.get_summary_metrics()['total_requests']

        rules = []
        for row in result:
            rule_id = row[0]
            rule_type = row[1]
            hit_count = row[2]
            unique_ips = row[3]
            blocks = row[4]
            allows = row[5]
            counts = row[6]

            hit_rate = (hit_count / total_requests * 100) if total_requests > 0 else 0
            block_rate = (blocks / hit_count * 100) if hit_count > 0 else 0

            rules.append({
                'rule_id': rule_id,
                'rule_type': rule_type,
                'hit_count': hit_count,
                'unique_ips': unique_ips,
                'blocks': blocks,
                'allows': allows,
                'counts': counts,
                'hit_rate_percent': round(hit_rate, 2),
                'block_rate_percent': round(block_rate, 2)
            })

        return rules

    def get_geographic_distribution(self) -> List[Dict[str, Any]]:
        """
        Get geographic distribution of traffic and threats.

        Returns:
            List[Dict[str, Any]]: Geographic distribution data
        """
        conn = self.db.get_connection()

        result = conn.execute("""
            SELECT
                country,
                COUNT(*) as total_requests,
                SUM(CASE WHEN action = 'BLOCK' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allowed,
                COUNT(DISTINCT client_ip) as unique_ips
            FROM waf_logs
            WHERE country IS NOT NULL AND country != '-'
            GROUP BY country
            ORDER BY total_requests DESC
        """).fetchall()

        countries = []
        for row in result:
            country = row[0]
            total = row[1]
            blocked = row[2]
            allowed = row[3]
            unique_ips = row[4]

            threat_score = (blocked / total * 100) if total > 0 else 0

            countries.append({
                'country': country,
                'total_requests': total,
                'blocked_requests': blocked,
                'allowed_requests': allowed,
                'unique_ips': unique_ips,
                'threat_score': round(threat_score, 2)
            })

        return countries

    def get_top_blocked_ips(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get top blocked IP addresses.

        Args:
            limit (int): Number of results to return

        Returns:
            List[Dict[str, Any]]: Top blocked IPs
        """
        conn = self.db.get_connection()

        result = conn.execute(f"""
            SELECT
                client_ip,
                country,
                COUNT(*) as block_count,
                COUNT(DISTINCT terminating_rule_id) as unique_rules_hit,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM waf_logs
            WHERE action = 'BLOCK' AND client_ip IS NOT NULL
            GROUP BY client_ip, country
            ORDER BY block_count DESC
            LIMIT {limit}
        """).fetchall()

        ips = []
        for row in result:
            ips.append({
                'ip': row[0],
                'country': row[1],
                'block_count': row[2],
                'unique_rules_hit': row[3],
                'first_seen': row[4],
                'last_seen': row[5]
            })

        return ips

    def get_attack_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of attack types from blocked requests.

        Returns:
            Dict[str, int]: Attack type counts
        """
        conn = self.db.get_connection()

        result = conn.execute("""
            SELECT terminating_rule_id, COUNT(*) as count
            FROM waf_logs
            WHERE action = 'BLOCK' AND terminating_rule_id IS NOT NULL
            GROUP BY terminating_rule_id
            ORDER BY count DESC
        """).fetchall()

        # Classify attack types based on rule IDs
        attack_types = {
            'SQL Injection': 0,
            'Cross-Site Scripting': 0,
            'Scanner/Reconnaissance': 0,
            'Bot Traffic': 0,
            'Geographic Block': 0,
            'Rate Limiting': 0,
            'IP Reputation': 0,
            'File Inclusion': 0,
            'Remote Code Execution': 0,
            'Other': 0
        }

        for row in result:
            rule_id = row[0].lower()
            count = row[1]

            if 'sqli' in rule_id or 'sql' in rule_id:
                attack_types['SQL Injection'] += count
            elif 'xss' in rule_id:
                attack_types['Cross-Site Scripting'] += count
            elif 'scanner' in rule_id or 'recon' in rule_id:
                attack_types['Scanner/Reconnaissance'] += count
            elif 'bot' in rule_id:
                attack_types['Bot Traffic'] += count
            elif 'geo' in rule_id:
                attack_types['Geographic Block'] += count
            elif 'rate' in rule_id:
                attack_types['Rate Limiting'] += count
            elif 'ip' in rule_id or 'reputation' in rule_id:
                attack_types['IP Reputation'] += count
            elif 'rfi' in rule_id or 'lfi' in rule_id:
                attack_types['File Inclusion'] += count
            elif 'rce' in rule_id or 'command' in rule_id:
                attack_types['Remote Code Execution'] += count
            else:
                attack_types['Other'] += count

        # Remove zero counts
        attack_types = {k: v for k, v in attack_types.items() if v > 0}

        return attack_types

    def get_hourly_traffic_patterns(self) -> List[Dict[str, Any]]:
        """
        Get hourly traffic patterns.

        Returns:
            List[Dict[str, Any]]: Hourly traffic data
        """
        conn = self.db.get_connection()

        result = conn.execute("""
            SELECT
                EXTRACT(HOUR FROM timestamp) as hour,
                COUNT(*) as total_requests,
                SUM(CASE WHEN action = 'BLOCK' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allowed
            FROM waf_logs
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        hourly_data = []
        for row in result:
            hour = int(row[0])
            total = row[1]
            blocked = row[2]
            allowed = row[3]

            hourly_data.append({
                'hour': hour,
                'total_requests': total,
                'blocked': blocked,
                'allowed': allowed,
                'block_rate_percent': round((blocked / total * 100) if total > 0 else 0, 2)
            })

        return hourly_data

    def get_daily_traffic_trends(self) -> pd.DataFrame:
        """
        Get daily traffic trends as a pandas DataFrame.

        Returns:
            pd.DataFrame: Daily traffic data
        """
        conn = self.db.get_connection()

        query = """
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as total_requests,
                SUM(CASE WHEN action = 'BLOCK' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allowed,
                COUNT(DISTINCT client_ip) as unique_ips
            FROM waf_logs
            GROUP BY DATE(timestamp)
            ORDER BY date
        """

        df = conn.execute(query).df()

        if not df.empty:
            df['block_rate_percent'] = (df['blocked'] / df['total_requests'] * 100).round(2)

        return df

    def get_web_acl_coverage(self) -> Dict[str, Any]:
        """
        Calculate Web ACL coverage metrics.

        Returns:
            Dict[str, Any]: Coverage metrics
        """
        conn = self.db.get_connection()

        # Total Web ACLs
        result = conn.execute("SELECT COUNT(*) FROM web_acls").fetchone()
        total_web_acls = result[0] if result else 0

        # Web ACLs with logging
        result = conn.execute("""
            SELECT COUNT(DISTINCT web_acl_id) FROM logging_configurations
        """).fetchone()
        with_logging = result[0] if result else 0

        # Total resources
        result = conn.execute("SELECT COUNT(*) FROM resource_associations").fetchone()
        total_resources = result[0] if result else 0

        # Resources by type
        result = conn.execute("""
            SELECT resource_type, COUNT(*) as count
            FROM resource_associations
            GROUP BY resource_type
        """).fetchall()

        resources_by_type = {row[0]: row[1] for row in result}

        coverage = {
            'total_web_acls': total_web_acls,
            'web_acls_with_logging': with_logging,
            'logging_coverage_percent': round((with_logging / total_web_acls * 100) if total_web_acls > 0 else 0, 2),
            'total_protected_resources': total_resources,
            'resources_by_type': resources_by_type
        }

        return coverage

    def get_bot_traffic_analysis(self) -> Dict[str, Any]:
        """
        Analyze bot traffic patterns using JA3/JA4 fingerprints and user agents.

        Returns:
            Dict[str, Any]: Bot traffic analysis
        """
        conn = self.db.get_connection()

        # Requests with JA3 fingerprints
        result = conn.execute("""
            SELECT COUNT(*) as count
            FROM waf_logs
            WHERE ja3_fingerprint IS NOT NULL
        """).fetchone()
        with_ja3 = result[0] if result else 0

        # Requests with JA4 fingerprints
        result = conn.execute("""
            SELECT COUNT(*) as count
            FROM waf_logs
            WHERE ja4_fingerprint IS NOT NULL
        """).fetchone()
        with_ja4 = result[0] if result else 0

        # Top user agents
        result = conn.execute("""
            SELECT user_agent, COUNT(*) as count
            FROM waf_logs
            WHERE user_agent IS NOT NULL
            GROUP BY user_agent
            ORDER BY count DESC
            LIMIT 20
        """).fetchall()

        top_user_agents = [{'user_agent': row[0], 'count': row[1]} for row in result]

        analysis = {
            'requests_with_ja3': with_ja3,
            'requests_with_ja4': with_ja4,
            'top_user_agents': top_user_agents
        }

        return analysis

    def calculate_security_posture_score(self) -> int:
        """
        Calculate an overall security posture score (0-100).

        Returns:
            int: Security posture score
        """
        score = 100

        # Check logging coverage (up to -30 points)
        coverage = self.get_web_acl_coverage()
        logging_coverage = coverage['logging_coverage_percent']
        if logging_coverage < 50:
            score -= 30
        elif logging_coverage < 75:
            score -= 15
        elif logging_coverage < 100:
            score -= 5

        # Check block rate (up to -20 points)
        summary = self.get_summary_metrics()
        block_rate = summary['block_rate_percent']
        if block_rate > 50:  # Too high, might indicate false positives
            score -= 20
        elif block_rate > 30:
            score -= 10
        elif block_rate < 0.1:  # Too low, might not be effective
            score -= 15

        # Check rule effectiveness (up to -20 points)
        rules = self.get_rule_effectiveness()
        if rules:
            zero_hit_rules = sum(1 for r in rules if r['hit_count'] == 0)
            zero_hit_rate = (zero_hit_rules / len(rules) * 100) if rules else 0

            if zero_hit_rate > 50:
                score -= 20
            elif zero_hit_rate > 25:
                score -= 10

        # Check resource coverage (up to -30 points)
        if coverage['total_protected_resources'] == 0:
            score -= 30
        elif coverage['total_protected_resources'] < 3:
            score -= 15

        return max(0, score)
