"""
WAF Configuration Processor

This module fetches and processes AWS WAF configurations including Web ACLs,
rules, resource associations, and logging configurations.
"""

import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from tqdm import tqdm

from utils.aws_helpers import (
    get_wafv2_client,
    handle_aws_error,
    determine_resource_type,
    parse_arn
)

logger = logging.getLogger(__name__)


class WAFConfigProcessor:
    """
    Processes AWS WAF configurations.
    """

    def __init__(self, scope: str = 'REGIONAL', region: Optional[str] = None):
        """
        Initialize the WAF configuration processor.

        Args:
            scope (str): WAF scope - 'REGIONAL' or 'CLOUDFRONT'
            region (Optional[str]): AWS region (only for REGIONAL scope)
        """
        self.scope = scope
        self.region = region
        self.client = get_wafv2_client(scope)
        logger.info(f"WAF configuration processor initialized for {scope} scope")

    def list_web_acls(self) -> List[Dict[str, Any]]:
        """
        List all Web ACLs in the current scope.

        Returns:
            List[Dict[str, Any]]: List of Web ACL summaries
        """
        logger.info(f"Listing Web ACLs for {self.scope} scope")

        try:
            response = self.client.list_web_acls(Scope=self.scope)
            web_acls = response.get('WebACLs', [])

            logger.info(f"Found {len(web_acls)} Web ACLs")
            return web_acls

        except ClientError as e:
            handle_aws_error(e, "listing Web ACLs")
            return []

    def get_web_acl(self, name: str, web_acl_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed configuration for a specific Web ACL.

        Args:
            name (str): Web ACL name
            web_acl_id (str): Web ACL ID

        Returns:
            Optional[Dict[str, Any]]: Web ACL configuration
        """
        logger.info(f"Fetching Web ACL configuration: {name}")

        try:
            response = self.client.get_web_acl(
                Name=name,
                Scope=self.scope,
                Id=web_acl_id
            )

            web_acl = response.get('WebACL', {})
            lock_token = response.get('LockToken')

            # Add metadata and scope (AWS API doesn't include scope in response)
            web_acl['_LockToken'] = lock_token
            web_acl['Scope'] = self.scope  # Add scope for database insertion

            logger.info(f"Retrieved Web ACL: {name} ({web_acl_id})")
            return web_acl

        except ClientError as e:
            handle_aws_error(e, f"getting Web ACL {name}")
            return None

    def get_all_web_acl_configs(self) -> List[Dict[str, Any]]:
        """
        Get detailed configurations for all Web ACLs.

        Returns:
            List[Dict[str, Any]]: List of complete Web ACL configurations
        """
        web_acl_summaries = self.list_web_acls()

        if not web_acl_summaries:
            logger.warning("No Web ACLs found")
            return []

        web_acl_configs = []

        for summary in tqdm(web_acl_summaries, desc="Fetching Web ACL configs"):
            name = summary['Name']
            web_acl_id = summary['Id']

            config = self.get_web_acl(name, web_acl_id)
            if config:
                # Add summary information
                config['_Summary'] = summary
                web_acl_configs.append(config)

        return web_acl_configs

    def get_resources_for_web_acl(self, web_acl_arn: str) -> List[str]:
        """
        Get list of resources associated with a Web ACL.

        Args:
            web_acl_arn (str): Web ACL ARN

        Returns:
            List[str]: List of resource ARNs
        """
        logger.debug(f"Fetching resources for Web ACL: {web_acl_arn}")

        try:
            resources = []
            next_marker = None

            while True:
                kwargs = {
                    'WebACLArn': web_acl_arn,
                    'ResourceType': 'APPLICATION_LOAD_BALANCER'
                }

                if next_marker:
                    kwargs['NextMarker'] = next_marker

                response = self.client.list_resources_for_web_acl(**kwargs)
                resources.extend(response.get('ResourceArns', []))

                next_marker = response.get('NextMarker')
                if not next_marker:
                    break

            # Also check for API Gateway resources
            try:
                kwargs = {
                    'WebACLArn': web_acl_arn,
                    'ResourceType': 'API_GATEWAY'
                }
                response = self.client.list_resources_for_web_acl(**kwargs)
                resources.extend(response.get('ResourceArns', []))
            except ClientError:
                pass  # API Gateway might not be available in this region

            # For CloudFront, check CLOUDFRONT resource type
            if self.scope == 'CLOUDFRONT':
                try:
                    kwargs = {
                        'WebACLArn': web_acl_arn,
                        'ResourceType': 'CLOUDFRONT'
                    }
                    response = self.client.list_resources_for_web_acl(**kwargs)
                    resources.extend(response.get('ResourceArns', []))
                except ClientError:
                    pass

            logger.debug(f"Found {len(resources)} resources for Web ACL")
            return resources

        except ClientError as e:
            handle_aws_error(e, f"listing resources for Web ACL")
            return []

    def get_logging_configuration(self, web_acl_arn: str) -> Optional[Dict[str, Any]]:
        """
        Get logging configuration for a Web ACL.

        Args:
            web_acl_arn (str): Web ACL ARN

        Returns:
            Optional[Dict[str, Any]]: Logging configuration
        """
        logger.debug(f"Fetching logging configuration for: {web_acl_arn}")

        try:
            response = self.client.get_logging_configuration(
                ResourceArn=web_acl_arn
            )

            logging_config = response.get('LoggingConfiguration', {})
            logger.debug(f"Retrieved logging configuration for Web ACL")
            return logging_config

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            if error_code == 'WAFNonexistentItemException':
                logger.warning(f"No logging configuration found for Web ACL")
                return None
            else:
                handle_aws_error(e, f"getting logging configuration")
                return None

    def get_complete_web_acl_info(self, web_acl_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete information for a Web ACL including resources and logging.

        Args:
            web_acl_config (Dict[str, Any]): Basic Web ACL configuration

        Returns:
            Dict[str, Any]: Complete Web ACL information
        """
        web_acl_arn = web_acl_config.get('ARN')
        web_acl_name = web_acl_config.get('Name')

        logger.info(f"Gathering complete information for Web ACL: {web_acl_name}")

        # Get associated resources
        resources = self.get_resources_for_web_acl(web_acl_arn)

        # Parse resource types
        resource_details = []
        for resource_arn in resources:
            resource_details.append({
                'arn': resource_arn,
                'type': determine_resource_type(resource_arn),
                'parsed': parse_arn(resource_arn)
            })

        # Get logging configuration
        logging_config = self.get_logging_configuration(web_acl_arn)

        # Combine all information
        complete_info = {
            'web_acl': web_acl_config,
            'resources': resource_details,
            'logging_configuration': logging_config,
            'resource_count': len(resource_details),
            'logging_enabled': logging_config is not None
        }

        return complete_info

    def extract_rules_from_web_acl(self, web_acl_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and process rules from a Web ACL configuration.

        Args:
            web_acl_config (Dict[str, Any]): Web ACL configuration

        Returns:
            List[Dict[str, Any]]: List of processed rules
        """
        rules = web_acl_config.get('Rules', [])
        processed_rules = []

        for rule in rules:
            processed_rule = {
                'Name': rule.get('Name'),
                'Priority': rule.get('Priority'),
                'Action': rule.get('Action', {}),
                'VisibilityConfig': rule.get('VisibilityConfig', {}),
                'Statement': rule.get('Statement', {}),
                'Type': self._determine_rule_type(rule)
            }

            # Extract managed rule group info if applicable
            statement = rule.get('Statement', {})
            if 'ManagedRuleGroupStatement' in statement:
                mrg = statement['ManagedRuleGroupStatement']
                processed_rule['ManagedRuleGroup'] = {
                    'VendorName': mrg.get('VendorName'),
                    'Name': mrg.get('Name'),
                    'Version': mrg.get('Version')
                }

            processed_rules.append(processed_rule)

        return processed_rules

    def _determine_rule_type(self, rule: Dict[str, Any]) -> str:
        """
        Determine the type of a WAF rule.

        Args:
            rule (Dict[str, Any]): Rule configuration

        Returns:
            str: Rule type classification
        """
        statement = rule.get('Statement', {})

        if 'ManagedRuleGroupStatement' in statement:
            return 'MANAGED_RULE_GROUP'
        elif 'RateBasedStatement' in statement:
            return 'RATE_BASED'
        elif 'RuleGroupReferenceStatement' in statement:
            return 'RULE_GROUP_REFERENCE'
        elif 'GeoMatchStatement' in statement:
            return 'GEO_MATCH'
        elif 'IPSetReferenceStatement' in statement:
            return 'IP_SET'
        elif 'RegexPatternSetReferenceStatement' in statement:
            return 'REGEX_PATTERN_SET'
        elif 'SizeConstraintStatement' in statement:
            return 'SIZE_CONSTRAINT'
        elif 'SqliMatchStatement' in statement:
            return 'SQLI_MATCH'
        elif 'XssMatchStatement' in statement:
            return 'XSS_MATCH'
        elif 'ByteMatchStatement' in statement:
            return 'BYTE_MATCH'
        elif 'AndStatement' in statement or 'OrStatement' in statement or 'NotStatement' in statement:
            return 'LOGICAL'
        else:
            return 'CUSTOM'

    def get_ip_sets(self) -> List[Dict[str, Any]]:
        """
        List all IP sets in the current scope.

        Returns:
            List[Dict[str, Any]]: List of IP set summaries
        """
        logger.info(f"Listing IP sets for {self.scope} scope")

        try:
            response = self.client.list_ip_sets(Scope=self.scope)
            ip_sets = response.get('IPSets', [])

            logger.info(f"Found {len(ip_sets)} IP sets")
            return ip_sets

        except ClientError as e:
            handle_aws_error(e, "listing IP sets")
            return []

    def get_regex_pattern_sets(self) -> List[Dict[str, Any]]:
        """
        List all regex pattern sets in the current scope.

        Returns:
            List[Dict[str, Any]]: List of regex pattern set summaries
        """
        logger.info(f"Listing regex pattern sets for {self.scope} scope")

        try:
            response = self.client.list_regex_pattern_sets(Scope=self.scope)
            pattern_sets = response.get('RegexPatternSets', [])

            logger.info(f"Found {len(pattern_sets)} regex pattern sets")
            return pattern_sets

        except ClientError as e:
            handle_aws_error(e, "listing regex pattern sets")
            return []

    def get_rule_groups(self) -> List[Dict[str, Any]]:
        """
        List all rule groups in the current scope.

        Returns:
            List[Dict[str, Any]]: List of rule group summaries
        """
        logger.info(f"Listing rule groups for {self.scope} scope")

        try:
            response = self.client.list_rule_groups(Scope=self.scope)
            rule_groups = response.get('RuleGroups', [])

            logger.info(f"Found {len(rule_groups)} rule groups")
            return rule_groups

        except ClientError as e:
            handle_aws_error(e, "listing rule groups")
            return []

    def analyze_web_acl_complexity(self, web_acl_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the complexity of a Web ACL configuration.

        Args:
            web_acl_config (Dict[str, Any]): Web ACL configuration

        Returns:
            Dict[str, Any]: Complexity analysis
        """
        rules = web_acl_config.get('Rules', [])

        rule_types = {}
        for rule in rules:
            rule_type = self._determine_rule_type(rule)
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1

        analysis = {
            'total_rules': len(rules),
            'capacity_used': web_acl_config.get('Capacity', 0),
            'rule_types': rule_types,
            'has_rate_limiting': 'RATE_BASED' in rule_types,
            'has_geo_blocking': 'GEO_MATCH' in rule_types,
            'has_ip_filtering': 'IP_SET' in rule_types,
            'managed_rule_groups': rule_types.get('MANAGED_RULE_GROUP', 0),
            'default_action': web_acl_config.get('DefaultAction', {})
        }

        return analysis
