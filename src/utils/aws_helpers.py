"""
AWS Helper Functions

This module provides utility functions for AWS operations including
profile detection, region management, and account information retrieval.
"""

import boto3
import logging
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, ProfileNotFound, NoCredentialsError

logger = logging.getLogger(__name__)


def get_current_aws_profile() -> Optional[str]:
    """
    Get the current AWS profile name from the session.

    Returns:
        Optional[str]: Profile name or None if using default credentials
    """
    try:
        session = boto3.Session()
        profile = session.profile_name
        logger.info(f"Using AWS profile: {profile}")
        return profile
    except Exception as e:
        logger.warning(f"Could not determine AWS profile: {e}")
        return None


def get_current_region() -> str:
    """
    Get the current AWS region from the session.

    Returns:
        str: AWS region name (defaults to us-east-1 if not set)
    """
    try:
        session = boto3.Session()
        region = session.region_name
        if not region:
            region = 'us-east-1'
            logger.warning(f"No region configured, defaulting to {region}")
        else:
            logger.info(f"Using AWS region: {region}")
        return region
    except Exception as e:
        logger.error(f"Error getting region: {e}")
        return 'us-east-1'


def get_account_id() -> Optional[str]:
    """
    Get the AWS account ID for the current credentials.

    Returns:
        Optional[str]: AWS account ID or None if unable to retrieve
    """
    try:
        sts_client = boto3.client('sts')
        response = sts_client.get_caller_identity()
        account_id = response['Account']
        logger.info(f"AWS Account ID: {account_id}")
        return account_id
    except (ClientError, NoCredentialsError) as e:
        logger.error(f"Error getting account ID: {e}")
        return None


def get_account_alias() -> Optional[str]:
    """
    Get the AWS account alias (friendly name) if set.

    Returns:
        Optional[str]: AWS account alias or None if not set or unable to retrieve

    Note:
        Requires iam:ListAccountAliases permission.
        If alias is not set or permission denied, returns None.
    """
    try:
        iam_client = boto3.client('iam')
        response = iam_client.list_account_aliases()
        aliases = response.get('AccountAliases', [])

        if aliases:
            alias = aliases[0]  # AWS accounts can have only one alias
            logger.info(f"AWS Account Alias: {alias}")
            return alias
        else:
            logger.info("No account alias set for this AWS account")
            return None
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'AccessDenied':
            logger.warning("Access denied when fetching account alias (iam:ListAccountAliases permission required)")
        else:
            logger.warning(f"Error getting account alias: {e}")
        return None
    except NoCredentialsError:
        logger.warning("No AWS credentials available to retrieve account alias")
        return None


def verify_aws_credentials() -> bool:
    """
    Verify that AWS credentials are configured and valid.

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    try:
        sts_client = boto3.client('sts')
        response = sts_client.get_caller_identity()
        logger.info(f"AWS credentials verified for account: {response['Account']}")
        logger.info(f"Identity ARN: {response['Arn']}")
        return True
    except (ClientError, ProfileNotFound, NoCredentialsError) as e:
        logger.error(f"AWS credentials verification failed: {e}")
        return False


def get_wafv2_client(scope: str = 'REGIONAL') -> boto3.client:
    """
    Create a WAFv2 client with appropriate region configuration.

    Args:
        scope (str): WAF scope - 'REGIONAL' or 'CLOUDFRONT'

    Returns:
        boto3.client: Configured WAFv2 client

    Note:
        CloudFront WAF ACLs must use us-east-1 region
    """
    if scope == 'CLOUDFRONT':
        region = 'us-east-1'
        logger.info("Creating WAFv2 client for CloudFront (us-east-1)")
    else:
        region = get_current_region()
        logger.info(f"Creating WAFv2 client for Regional scope ({region})")

    return boto3.client('wafv2', region_name=region)


def get_logs_client(region: Optional[str] = None) -> boto3.client:
    """
    Create a CloudWatch Logs client.

    Args:
        region (Optional[str]): AWS region (uses current region if not specified)

    Returns:
        boto3.client: Configured CloudWatch Logs client
    """
    if not region:
        region = get_current_region()

    logger.info(f"Creating CloudWatch Logs client for region: {region}")
    return boto3.client('logs', region_name=region)


def get_s3_client() -> boto3.client:
    """
    Create an S3 client.

    Returns:
        boto3.client: Configured S3 client
    """
    logger.info("Creating S3 client")
    return boto3.client('s3')


def parse_arn(arn: str) -> Dict[str, str]:
    """
    Parse an AWS ARN into its components.

    Args:
        arn (str): AWS ARN string

    Returns:
        Dict[str, str]: Dictionary with ARN components

    Example:
        >>> parse_arn('arn:aws:wafv2:us-east-1:123456789012:regional/webacl/test/a1b2c3d4')
        {
            'arn': 'arn',
            'partition': 'aws',
            'service': 'wafv2',
            'region': 'us-east-1',
            'account_id': '123456789012',
            'resource': 'regional/webacl/test/a1b2c3d4'
        }
    """
    parts = arn.split(':')

    if len(parts) < 6:
        logger.warning(f"Invalid ARN format: {arn}")
        return {}

    return {
        'arn': parts[0],
        'partition': parts[1],
        'service': parts[2],
        'region': parts[3],
        'account_id': parts[4],
        'resource': ':'.join(parts[5:])
    }


def determine_resource_type(arn: str) -> str:
    """
    Determine the resource type from an ARN.

    Args:
        arn (str): AWS resource ARN

    Returns:
        str: Resource type (ALB, API_GATEWAY, CLOUDFRONT, or UNKNOWN)
    """
    if 'elasticloadbalancing' in arn and 'loadbalancer/app/' in arn:
        return 'ALB'
    elif 'apigateway' in arn:
        return 'API_GATEWAY'
    elif 'cloudfront' in arn:
        return 'CLOUDFRONT'
    else:
        logger.warning(f"Unknown resource type for ARN: {arn}")
        return 'UNKNOWN'


def handle_aws_error(error: ClientError, operation: str) -> None:
    """
    Handle AWS ClientError with appropriate logging.

    Args:
        error (ClientError): The boto3 ClientError exception
        operation (str): Description of the operation that failed
    """
    error_code = error.response.get('Error', {}).get('Code', 'Unknown')
    error_message = error.response.get('Error', {}).get('Message', 'Unknown error')

    logger.error(f"AWS API Error during {operation}")
    logger.error(f"Error Code: {error_code}")
    logger.error(f"Error Message: {error_message}")

    if error_code == 'AccessDeniedException':
        logger.error("Access denied. Check IAM permissions for the current AWS profile.")
    elif error_code == 'ThrottlingException':
        logger.error("API rate limit exceeded. Consider adding retry logic or reducing request rate.")
    elif error_code == 'ResourceNotFoundException':
        logger.error("The requested AWS resource was not found.")


def get_session_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the current AWS session.

    Returns:
        Dict[str, Any]: Session information including profile, region, account ID, alias, and identity
    """
    session_info = {
        'profile': get_current_aws_profile(),
        'region': get_current_region(),
        'account_id': get_account_id(),
        'account_alias': get_account_alias(),
        'credentials_valid': verify_aws_credentials()
    }

    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        session_info['user_id'] = identity.get('UserId')
        session_info['arn'] = identity.get('Arn')
    except Exception as e:
        logger.warning(f"Could not get full session info: {e}")

    return session_info
