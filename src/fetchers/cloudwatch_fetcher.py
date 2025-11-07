"""
CloudWatch Logs Fetcher

This module fetches AWS WAF logs from CloudWatch Logs using the AWS CLI
and boto3 SDK with proper pagination and rate limiting.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from botocore.exceptions import ClientError
from tqdm import tqdm

from utils.aws_helpers import get_logs_client, handle_aws_error
from utils.time_helpers import datetime_to_timestamp

logger = logging.getLogger(__name__)


class CloudWatchFetcher:
    """
    Fetches WAF logs from CloudWatch Logs.
    """

    def __init__(self, region: Optional[str] = None):
        """
        Initialize the CloudWatch Logs fetcher.

        Args:
            region (Optional[str]): AWS region (uses current region if not specified)
        """
        self.client = get_logs_client(region)
        self.region = region
        logger.info("CloudWatch Logs fetcher initialized")

    def list_log_groups(self, prefix: str = "aws-waf-logs") -> List[Dict[str, Any]]:
        """
        List CloudWatch log groups with a given prefix.

        Args:
            prefix (str): Log group name prefix (default: 'aws-waf-logs')

        Returns:
            List[Dict[str, Any]]: List of log group information
        """
        log_groups = []

        try:
            paginator = self.client.get_paginator('describe_log_groups')
            page_iterator = paginator.paginate(logGroupNamePrefix=prefix)

            for page in page_iterator:
                log_groups.extend(page.get('logGroups', []))

            logger.info(f"Found {len(log_groups)} log groups with prefix '{prefix}'")

            # Sort by creation time (most recent first)
            log_groups.sort(key=lambda x: x.get('creationTime', 0), reverse=True)

            return log_groups

        except ClientError as e:
            handle_aws_error(e, "listing CloudWatch log groups")
            return []

    def get_log_events(self, log_group_name: str, start_time: datetime,
                      end_time: datetime, filter_pattern: str = "",
                      max_results: int = 10000) -> List[Dict[str, Any]]:
        """
        Fetch log events from a CloudWatch log group.

        Args:
            log_group_name (str): Name of the CloudWatch log group
            start_time (datetime): Start of time range
            end_time (datetime): End of time range
            filter_pattern (str): CloudWatch Logs filter pattern (optional)
            max_results (int): Maximum number of results to fetch

        Returns:
            List[Dict[str, Any]]: List of log events
        """
        logger.info(f"Fetching logs from CloudWatch log group: {log_group_name}")
        logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")

        log_events = []
        start_time_ms = datetime_to_timestamp(start_time)
        end_time_ms = datetime_to_timestamp(end_time)

        try:
            # Use filter_log_events for efficient querying
            kwargs = {
                'logGroupName': log_group_name,
                'startTime': start_time_ms,
                'endTime': end_time_ms,
                'limit': 10000  # Max per request
            }

            if filter_pattern:
                kwargs['filterPattern'] = filter_pattern

            # Create progress bar
            pbar = tqdm(desc="Fetching CloudWatch logs", unit=" events")

            # Paginate through results
            next_token = None
            requests_made = 0

            while True:
                if next_token:
                    kwargs['nextToken'] = next_token

                response = self.client.filter_log_events(**kwargs)
                events = response.get('events', [])

                log_events.extend(events)
                pbar.update(len(events))

                # Rate limiting: CloudWatch Logs has 5 TPS limit per region
                requests_made += 1
                if requests_made % 5 == 0:
                    time.sleep(1)

                # Check if we've hit the max results limit
                if len(log_events) >= max_results:
                    logger.warning(f"Reached max results limit: {max_results}")
                    break

                # Check for more results
                next_token = response.get('nextToken')
                if not next_token:
                    break

            pbar.close()

            logger.info(f"Fetched {len(log_events)} log events from CloudWatch")
            return log_events

        except ClientError as e:
            handle_aws_error(e, f"fetching logs from {log_group_name}")
            return []

    def get_log_streams(self, log_group_name: str,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        List log streams in a log group, optionally filtered by time.

        Args:
            log_group_name (str): Name of the CloudWatch log group
            start_time (Optional[datetime]): Filter streams after this time
            end_time (Optional[datetime]): Filter streams before this time

        Returns:
            List[Dict[str, Any]]: List of log stream information
        """
        log_streams = []

        try:
            paginator = self.client.get_paginator('describe_log_streams')
            kwargs = {
                'logGroupName': log_group_name,
                'orderBy': 'LastEventTime',
                'descending': True
            }

            page_iterator = paginator.paginate(**kwargs)

            for page in page_iterator:
                streams = page.get('logStreams', [])

                # Filter by time if specified
                if start_time or end_time:
                    filtered_streams = []
                    start_ms = datetime_to_timestamp(start_time) if start_time else 0
                    end_ms = datetime_to_timestamp(end_time) if end_time else float('inf')

                    for stream in streams:
                        last_event_time = stream.get('lastEventTimestamp', 0)
                        if start_ms <= last_event_time <= end_ms:
                            filtered_streams.append(stream)

                    log_streams.extend(filtered_streams)
                else:
                    log_streams.extend(streams)

            logger.info(f"Found {len(log_streams)} log streams in {log_group_name}")
            return log_streams

        except ClientError as e:
            handle_aws_error(e, f"listing log streams for {log_group_name}")
            return []

    def get_log_events_by_stream(self, log_group_name: str, log_stream_name: str,
                                 start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch log events from a specific log stream.

        Args:
            log_group_name (str): Name of the CloudWatch log group
            log_stream_name (str): Name of the log stream
            start_time (Optional[datetime]): Start of time range
            end_time (Optional[datetime]): End of time range

        Returns:
            List[Dict[str, Any]]: List of log events
        """
        log_events = []

        try:
            kwargs = {
                'logGroupName': log_group_name,
                'logStreamName': log_stream_name,
                'startFromHead': True
            }

            if start_time:
                kwargs['startTime'] = datetime_to_timestamp(start_time)
            if end_time:
                kwargs['endTime'] = datetime_to_timestamp(end_time)

            next_token = None

            while True:
                if next_token:
                    kwargs['nextToken'] = next_token

                response = self.client.get_log_events(**kwargs)
                events = response.get('events', [])

                if not events:
                    break

                log_events.extend(events)

                # Check for more results
                next_forward_token = response.get('nextForwardToken')
                if next_forward_token == next_token:
                    # No more events
                    break

                next_token = next_forward_token

            logger.debug(f"Fetched {len(log_events)} events from stream {log_stream_name}")
            return log_events

        except ClientError as e:
            handle_aws_error(e, f"fetching events from stream {log_stream_name}")
            return []

    def estimate_log_volume(self, log_group_name: str, start_time: datetime,
                           end_time: datetime) -> Dict[str, Any]:
        """
        Estimate the volume of logs in a time range.

        Args:
            log_group_name (str): Name of the CloudWatch log group
            start_time (datetime): Start of time range
            end_time (datetime): End of time range

        Returns:
            Dict[str, Any]: Volume estimation including bytes and event count
        """
        try:
            # Get a sample of logs to estimate
            sample_events = self.get_log_events(
                log_group_name, start_time, end_time, max_results=1000
            )

            if not sample_events:
                return {
                    'estimated_events': 0,
                    'estimated_bytes': 0,
                    'sample_size': 0
                }

            # Calculate average event size
            # Support both '@message' and 'message' field names
            total_bytes = sum(len(event.get('@message') or event.get('message', '')) for event in sample_events)
            avg_event_size = total_bytes / len(sample_events) if sample_events else 0

            # Get log streams to estimate total volume
            log_streams = self.get_log_streams(log_group_name, start_time, end_time)
            total_stored_bytes = sum(stream.get('storedBytes', 0) for stream in log_streams)

            estimated_events = int(total_stored_bytes / avg_event_size) if avg_event_size > 0 else 0

            estimation = {
                'estimated_events': estimated_events,
                'estimated_bytes': total_stored_bytes,
                'sample_size': len(sample_events),
                'avg_event_size': avg_event_size,
                'log_streams': len(log_streams)
            }

            logger.info(f"Log volume estimation: ~{estimated_events:,} events, ~{total_stored_bytes:,} bytes")
            return estimation

        except Exception as e:
            logger.error(f"Error estimating log volume: {e}")
            return {
                'estimated_events': 0,
                'estimated_bytes': 0,
                'sample_size': 0,
                'error': str(e)
            }

    def fetch_logs_chunked(self, log_group_name: str, start_time: datetime,
                          end_time: datetime, chunk_days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch logs in time-based chunks to handle large volumes.

        Args:
            log_group_name (str): Name of the CloudWatch log group
            start_time (datetime): Start of time range
            end_time (datetime): End of time range
            chunk_days (int): Number of days per chunk (default: 7)

        Returns:
            List[Dict[str, Any]]: All log events across chunks
        """
        from datetime import timedelta

        logger.info(f"Fetching logs in {chunk_days}-day chunks")

        all_events = []
        current_start = start_time

        while current_start < end_time:
            current_end = min(current_start + timedelta(days=chunk_days), end_time)

            logger.info(f"Fetching chunk: {current_start.date()} to {current_end.date()}")

            chunk_events = self.get_log_events(
                log_group_name, current_start, current_end
            )

            all_events.extend(chunk_events)
            logger.info(f"Chunk complete: {len(chunk_events)} events. Total: {len(all_events)}")

            current_start = current_end

        logger.info(f"Chunked fetch complete: {len(all_events)} total events")
        return all_events
