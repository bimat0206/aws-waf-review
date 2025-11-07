"""
S3 Logs Fetcher

This module fetches AWS WAF logs from S3 buckets and handles compressed
log files with proper error handling and progress tracking.
"""

import gzip
import json
import logging
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from botocore.exceptions import ClientError
from tqdm import tqdm
import tempfile

from utils.aws_helpers import get_s3_client, handle_aws_error
from utils.time_helpers import get_s3_prefix_for_date, get_daily_buckets

logger = logging.getLogger(__name__)


class S3Fetcher:
    """
    Fetches WAF logs from S3 buckets.
    """

    def __init__(self):
        """
        Initialize the S3 fetcher.
        """
        self.client = get_s3_client()
        logger.info("S3 fetcher initialized")

    def list_objects(self, bucket: str, prefix: str = "",
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        List objects in an S3 bucket with optional time-based filtering.

        Args:
            bucket (str): S3 bucket name
            prefix (str): Object key prefix
            start_time (Optional[datetime]): Filter objects after this time
            end_time (Optional[datetime]): Filter objects before this time

        Returns:
            List[Dict[str, Any]]: List of S3 object metadata
        """
        objects = []

        try:
            paginator = self.client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

            logger.info(f"Listing objects in s3://{bucket}/{prefix}")

            for page in page_iterator:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    # Filter by time if specified
                    if start_time or end_time:
                        last_modified = obj['LastModified']

                        if start_time and last_modified < start_time:
                            continue
                        if end_time and last_modified > end_time:
                            continue

                    objects.append(obj)

            logger.info(f"Found {len(objects)} objects matching criteria")
            return objects

        except ClientError as e:
            handle_aws_error(e, f"listing objects in s3://{bucket}/{prefix}")
            return []

    def download_object(self, bucket: str, key: str, local_path: Optional[str] = None) -> Optional[str]:
        """
        Download an object from S3.

        Args:
            bucket (str): S3 bucket name
            key (str): Object key
            local_path (Optional[str]): Local file path (uses temp file if not specified)

        Returns:
            Optional[str]: Path to downloaded file or None on error
        """
        try:
            if not local_path:
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.gz')
                local_path = temp_file.name
                temp_file.close()

            logger.debug(f"Downloading s3://{bucket}/{key} to {local_path}")
            self.client.download_file(bucket, key, local_path)

            return local_path

        except ClientError as e:
            handle_aws_error(e, f"downloading s3://{bucket}/{key}")
            return None

    def read_log_file(self, bucket: str, key: str) -> List[Dict[str, Any]]:
        """
        Read and parse a WAF log file from S3.

        Args:
            bucket (str): S3 bucket name
            key (str): Object key

        Returns:
            List[Dict[str, Any]]: Parsed log entries
        """
        log_entries = []

        try:
            # Download the file
            local_path = self.download_object(bucket, key)
            if not local_path:
                return []

            # Determine if file is compressed
            is_compressed = key.endswith('.gz')

            # Read and parse the file
            if is_compressed:
                with gzip.open(local_path, 'rt', encoding='utf-8') as f:
                    log_entries = self._parse_log_content(f)
            else:
                with open(local_path, 'r', encoding='utf-8') as f:
                    log_entries = self._parse_log_content(f)

            # Clean up temporary file
            Path(local_path).unlink()

            logger.debug(f"Read {len(log_entries)} log entries from {key}")
            return log_entries

        except Exception as e:
            logger.error(f"Error reading log file {key}: {e}")
            return []

    def _parse_log_content(self, file_handle) -> List[Dict[str, Any]]:
        """
        Parse log content from a file handle.

        Supports both newline-delimited JSON (standard WAF logging) and
        CloudWatch export files where each object spans multiple lines and
        wraps the real payload inside an ``@message`` field.
        """
        content = file_handle.read()

        if not content:
            return []

        # Ensure we are working with text
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')

        log_entries: List[Dict[str, Any]] = []
        json_objects = self._extract_json_objects(content)

        for obj in json_objects:
            decoded = self._decode_log_record(obj)
            if decoded:
                log_entries.append(decoded)

        return log_entries

    def _extract_json_objects(self, content: str) -> List[Any]:
        """Extract JSON objects from a string without requiring an array wrapper."""
        decoder = json.JSONDecoder()
        objects: List[Any] = []
        idx = 0
        length = len(content)

        while idx < length:
            # Skip whitespace between objects
            while idx < length and content[idx].isspace():
                idx += 1

            if idx >= length:
                break

            try:
                obj, offset = decoder.raw_decode(content, idx)
                objects.append(obj)
                idx = offset
            except json.JSONDecodeError:
                # Move to the next line to resume parsing without infinite loops
                next_idx = content.find('\n', idx)
                if next_idx == -1:
                    break
                idx = next_idx + 1

        return objects

    def _decode_log_record(self, record: Any) -> Optional[Dict[str, Any]]:
        """Normalize different record shapes into a WAF log dictionary."""
        if isinstance(record, dict):
            if '@message' in record:
                return self._decode_cloudwatch_export_record(record)
            return record

        if isinstance(record, str):
            try:
                decoded = json.loads(record)
                return decoded if isinstance(decoded, dict) else None
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse log record string: {e}")
                return None

        return None

    def _decode_cloudwatch_export_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Decode CloudWatch export entries that wrap payloads in @message."""
        message = record.get('@message')

        if not isinstance(message, str):
            logger.warning("CloudWatch export record missing '@message' string")
            return None

        try:
            inner = json.loads(message)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode CloudWatch export message: {e}")
            return None

        metadata = {}
        if record.get('@timestamp'):
            metadata['timestamp'] = record.get('@timestamp')
        if record.get('@ptr'):
            metadata['ptr'] = record.get('@ptr')

        if metadata:
            inner['_cloudwatch_export_metadata'] = metadata

        inner['_source'] = 'cloudwatch_export'
        return inner

    def fetch_logs(self, bucket: str, prefix: str, start_time: datetime,
                  end_time: datetime) -> List[Dict[str, Any]]:
        """
        Fetch all WAF logs from S3 for a given time range.

        Args:
            bucket (str): S3 bucket name
            prefix (str): Base prefix for WAF logs
            start_time (datetime): Start of time range
            end_time (datetime): End of time range

        Returns:
            List[Dict[str, Any]]: All parsed log entries
        """
        logger.info(f"Fetching WAF logs from s3://{bucket}/{prefix}")
        logger.info(f"Time range: {start_time.date()} to {end_time.date()}")

        all_log_entries = []

        # Generate date-based prefixes
        date_prefixes = self._generate_date_prefixes(prefix, start_time, end_time)

        logger.info(f"Scanning {len(date_prefixes)} date-based prefixes")

        # Process each date prefix
        for date_prefix in tqdm(date_prefixes, desc="Processing S3 prefixes"):
            # List objects for this prefix
            objects = self.list_objects(bucket, date_prefix, start_time, end_time)

            # Read each log file
            for obj in tqdm(objects, desc=f"Reading {date_prefix}", leave=False):
                key = obj['Key']

                # Skip non-log files
                if not self._is_log_file(key):
                    continue

                log_entries = self.read_log_file(bucket, key)
                all_log_entries.extend(log_entries)

        logger.info(f"Fetched {len(all_log_entries)} total log entries from S3")
        return all_log_entries

    def _generate_date_prefixes(self, base_prefix: str, start_time: datetime,
                               end_time: datetime) -> List[str]:
        """
        Generate date-based S3 prefixes for the time range.

        Args:
            base_prefix (str): Base S3 prefix
            start_time (datetime): Start of time range
            end_time (datetime): End of time range

        Returns:
            List[str]: List of S3 prefixes to scan
        """
        prefixes = []
        daily_buckets = get_daily_buckets(start_time, end_time)

        for date in daily_buckets:
            date_suffix = get_s3_prefix_for_date(date)
            full_prefix = f"{base_prefix.rstrip('/')}/{date_suffix}"
            prefixes.append(full_prefix)

        return prefixes

    def _is_log_file(self, key: str) -> bool:
        """
        Determine if an S3 key represents a log file.

        Args:
            key (str): S3 object key

        Returns:
            bool: True if the key is a log file
        """
        # WAF log files typically end with .gz or .json
        return key.endswith('.gz') or key.endswith('.json')

    def fetch_logs_streaming(self, bucket: str, prefix: str, start_time: datetime,
                            end_time: datetime) -> Iterator[Dict[str, Any]]:
        """
        Fetch logs as a streaming iterator to reduce memory usage.

        Args:
            bucket (str): S3 bucket name
            prefix (str): Base prefix for WAF logs
            start_time (datetime): Start of time range
            end_time (datetime): End of time range

        Yields:
            Dict[str, Any]: Individual log entries
        """
        logger.info(f"Streaming WAF logs from s3://{bucket}/{prefix}")

        date_prefixes = self._generate_date_prefixes(prefix, start_time, end_time)

        for date_prefix in date_prefixes:
            objects = self.list_objects(bucket, date_prefix, start_time, end_time)

            for obj in objects:
                key = obj['Key']

                if not self._is_log_file(key):
                    continue

                log_entries = self.read_log_file(bucket, key)
                for entry in log_entries:
                    yield entry

    def get_bucket_info(self, bucket: str) -> Dict[str, Any]:
        """
        Get information about an S3 bucket.

        Args:
            bucket (str): S3 bucket name

        Returns:
            Dict[str, Any]: Bucket information
        """
        try:
            # Check if bucket exists and is accessible
            response = self.client.head_bucket(Bucket=bucket)

            # Get bucket location
            location_response = self.client.get_bucket_location(Bucket=bucket)
            region = location_response.get('LocationConstraint') or 'us-east-1'

            info = {
                'bucket': bucket,
                'region': region,
                'accessible': True,
                'http_status': response['ResponseMetadata']['HTTPStatusCode']
            }

            logger.info(f"Bucket {bucket} is accessible in region {region}")
            return info

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            if error_code == '404':
                logger.error(f"Bucket {bucket} does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to bucket {bucket}")
            else:
                handle_aws_error(e, f"accessing bucket {bucket}")

            return {
                'bucket': bucket,
                'accessible': False,
                'error': error_code
            }

    def estimate_log_volume(self, bucket: str, prefix: str, start_time: datetime,
                           end_time: datetime) -> Dict[str, Any]:
        """
        Estimate the volume of logs in S3 for a time range.

        Args:
            bucket (str): S3 bucket name
            prefix (str): Base prefix for WAF logs
            start_time (datetime): Start of time range
            end_time (datetime): End of time range

        Returns:
            Dict[str, Any]: Volume estimation
        """
        logger.info(f"Estimating log volume in s3://{bucket}/{prefix}")

        date_prefixes = self._generate_date_prefixes(prefix, start_time, end_time)
        total_size = 0
        total_objects = 0

        for date_prefix in tqdm(date_prefixes, desc="Scanning prefixes"):
            objects = self.list_objects(bucket, date_prefix, start_time, end_time)

            for obj in objects:
                if self._is_log_file(obj['Key']):
                    total_size += obj.get('Size', 0)
                    total_objects += 1

        # Estimate number of events based on average compressed size
        # Typical WAF log entry is ~500-1000 bytes uncompressed, ~100-200 bytes compressed
        avg_compressed_entry_size = 150  # bytes
        estimated_events = total_size // avg_compressed_entry_size

        estimation = {
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_objects': total_objects,
            'estimated_events': estimated_events,
            'date_prefixes_scanned': len(date_prefixes)
        }

        logger.info(f"Estimated {estimated_events:,} log entries across {total_objects} files ({estimation['total_size_mb']} MB)")
        return estimation

    def parse_waf_bucket_arn(self, bucket_arn: str) -> Dict[str, str]:
        """
        Parse a WAF logging bucket ARN to extract bucket name and prefix.

        Args:
            bucket_arn (str): S3 bucket ARN from WAF logging configuration

        Returns:
            Dict[str, str]: Parsed bucket information

        Example:
            >>> parse_waf_bucket_arn('arn:aws:s3:::aws-waf-logs-example/prefix/')
            {'bucket': 'aws-waf-logs-example', 'prefix': 'prefix/'}
        """
        # Remove 'arn:aws:s3:::' prefix
        s3_path = bucket_arn.replace('arn:aws:s3:::', '')

        # Split bucket and prefix
        parts = s3_path.split('/', 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ''

        return {
            'bucket': bucket,
            'prefix': prefix,
            'full_arn': bucket_arn
        }
