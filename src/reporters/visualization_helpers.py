"""
Visualization Helpers

This module provides helper functions for creating charts and visualizations
for Excel reports using matplotlib.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO
import pandas as pd

logger = logging.getLogger(__name__)


class VisualizationHelpers:
    """
    Helper class for creating visualizations.
    """

    # Color scheme for professional reports
    COLORS = {
        'block': '#E74C3C',      # Red
        'allow': '#27AE60',      # Green
        'count': '#F39C12',      # Orange
        'captcha': '#3498DB',    # Blue
        'challenge': '#9B59B6',  # Purple
        'primary': '#2C3E50',    # Dark blue
        'secondary': '#7F8C8D',  # Gray
        'success': '#27AE60',    # Green
        'warning': '#F39C12',    # Orange
        'danger': '#E74C3C',     # Red
        'info': '#3498DB'        # Blue
    }

    @staticmethod
    def create_action_distribution_chart(action_data: Dict[str, Dict[str, Any]],
                                        figsize: Tuple[int, int] = (10, 6)) -> BytesIO:
        """
        Create a pie chart showing action distribution.

        Args:
            action_data (Dict[str, Dict[str, Any]]): Action distribution data
            figsize (Tuple[int, int]): Figure size

        Returns:
            BytesIO: Image buffer containing the chart
        """
        fig, ax = plt.subplots(figsize=figsize)

        actions = list(action_data.keys())
        counts = [action_data[a]['count'] for a in actions]

        # Map actions to colors
        colors = [VisualizationHelpers.COLORS.get(a.lower(), '#95A5A6') for a in actions]

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            counts,
            labels=actions,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )

        # Improve text
        for text in texts:
            text.set_fontsize(11)
            text.set_weight('bold')

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')

        ax.set_title('WAF Action Distribution', fontsize=14, weight='bold', pad=20)

        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    @staticmethod
    def create_daily_traffic_chart(daily_data: pd.DataFrame,
                                  figsize: Tuple[int, int] = (12, 6)) -> BytesIO:
        """
        Create a line chart showing daily traffic trends.

        Args:
            daily_data (pd.DataFrame): Daily traffic DataFrame
            figsize (Tuple[int, int]): Figure size

        Returns:
            BytesIO: Image buffer containing the chart
        """
        fig, ax = plt.subplots(figsize=figsize)

        if daily_data.empty:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            return buffer

        # Plot lines
        ax.plot(daily_data['date'], daily_data['total_requests'],
                marker='o', linewidth=2, label='Total Requests',
                color=VisualizationHelpers.COLORS['primary'])

        ax.plot(daily_data['date'], daily_data['blocked'],
                marker='s', linewidth=2, label='Blocked',
                color=VisualizationHelpers.COLORS['danger'])

        ax.plot(daily_data['date'], daily_data['allowed'],
                marker='^', linewidth=2, label='Allowed',
                color=VisualizationHelpers.COLORS['success'])

        # Formatting
        ax.set_xlabel('Date', fontsize=11, weight='bold')
        ax.set_ylabel('Request Count', fontsize=11, weight='bold')
        ax.set_title('Daily Traffic Trends', fontsize=14, weight='bold', pad=20)
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    @staticmethod
    def create_geographic_threat_chart(geo_data: List[Dict[str, Any]],
                                      top_n: int = 15,
                                      figsize: Tuple[int, int] = (12, 8)) -> BytesIO:
        """
        Create a horizontal bar chart showing geographic threat distribution.

        Args:
            geo_data (List[Dict[str, Any]]): Geographic distribution data
            top_n (int): Number of top countries to show
            figsize (Tuple[int, int]): Figure size

        Returns:
            BytesIO: Image buffer containing the chart
        """
        fig, ax = plt.subplots(figsize=figsize)

        if not geo_data:
            ax.text(0.5, 0.5, 'No geographic data available', ha='center', va='center')
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            return buffer

        # Get top N countries by blocked requests
        top_countries = sorted(geo_data, key=lambda x: x['blocked_requests'], reverse=True)[:top_n]

        countries = [c['country'] for c in top_countries]
        blocked = [c['blocked_requests'] for c in top_countries]
        allowed = [c['allowed_requests'] for c in top_countries]

        y_pos = range(len(countries))

        # Create horizontal stacked bar chart
        ax.barh(y_pos, blocked, label='Blocked',
                color=VisualizationHelpers.COLORS['danger'])
        ax.barh(y_pos, allowed, left=blocked, label='Allowed',
                color=VisualizationHelpers.COLORS['success'])

        ax.set_yticks(y_pos)
        ax.set_yticklabels(countries)
        ax.set_xlabel('Request Count', fontsize=11, weight='bold')
        ax.set_title(f'Top {top_n} Countries by Traffic Volume', fontsize=14, weight='bold', pad=20)
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    @staticmethod
    def create_attack_type_chart(attack_data: Dict[str, int],
                                figsize: Tuple[int, int] = (10, 8)) -> BytesIO:
        """
        Create a horizontal bar chart showing attack type distribution.

        Args:
            attack_data (Dict[str, int]): Attack type distribution
            figsize (Tuple[int, int]): Figure size

        Returns:
            BytesIO: Image buffer containing the chart
        """
        fig, ax = plt.subplots(figsize=figsize)

        if not attack_data:
            ax.text(0.5, 0.5, 'No attack data available', ha='center', va='center')
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            return buffer

        # Sort by count
        sorted_attacks = sorted(attack_data.items(), key=lambda x: x[1], reverse=True)
        attack_types = [a[0] for a in sorted_attacks]
        counts = [a[1] for a in sorted_attacks]

        y_pos = range(len(attack_types))

        # Create horizontal bar chart
        bars = ax.barh(y_pos, counts, color=VisualizationHelpers.COLORS['danger'])

        # Add value labels
        for i, (bar, count) in enumerate(zip(bars, counts)):
            width = bar.get_width()
            ax.text(width, i, f' {count:,}',
                   ha='left', va='center', fontsize=10)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(attack_types)
        ax.set_xlabel('Blocked Requests', fontsize=11, weight='bold')
        ax.set_title('Attack Type Distribution', fontsize=14, weight='bold', pad=20)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    @staticmethod
    def create_hourly_pattern_chart(hourly_data: List[Dict[str, Any]],
                                   figsize: Tuple[int, int] = (12, 6)) -> BytesIO:
        """
        Create a bar chart showing hourly traffic patterns.

        Args:
            hourly_data (List[Dict[str, Any]]): Hourly traffic data
            figsize (Tuple[int, int]): Figure size

        Returns:
            BytesIO: Image buffer containing the chart
        """
        fig, ax = plt.subplots(figsize=figsize)

        if not hourly_data:
            ax.text(0.5, 0.5, 'No hourly data available', ha='center', va='center')
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            return buffer

        hours = [d['hour'] for d in hourly_data]
        blocked = [d['blocked'] for d in hourly_data]
        allowed = [d['allowed'] for d in hourly_data]

        width = 0.35
        x = range(len(hours))

        # Create grouped bar chart
        ax.bar([i - width/2 for i in x], blocked, width, label='Blocked',
               color=VisualizationHelpers.COLORS['danger'])
        ax.bar([i + width/2 for i in x], allowed, width, label='Allowed',
               color=VisualizationHelpers.COLORS['success'])

        ax.set_xlabel('Hour of Day (UTC)', fontsize=11, weight='bold')
        ax.set_ylabel('Request Count', fontsize=11, weight='bold')
        ax.set_title('Hourly Traffic Patterns', fontsize=14, weight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45, ha='right')
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    @staticmethod
    def create_rule_effectiveness_chart(rule_data: List[Dict[str, Any]],
                                       top_n: int = 15,
                                       figsize: Tuple[int, int] = (12, 8)) -> BytesIO:
        """
        Create a chart showing rule effectiveness.

        Args:
            rule_data (List[Dict[str, Any]]): Rule effectiveness data
            top_n (int): Number of top rules to show
            figsize (Tuple[int, int]): Figure size

        Returns:
            BytesIO: Image buffer containing the chart
        """
        fig, ax = plt.subplots(figsize=figsize)

        if not rule_data:
            ax.text(0.5, 0.5, 'No rule data available', ha='center', va='center')
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            return buffer

        # Get top N rules by hit count
        top_rules = sorted(rule_data, key=lambda x: x['hit_count'], reverse=True)[:top_n]

        # Truncate long rule names
        rule_names = [r['rule_id'][:40] + '...' if len(r['rule_id']) > 40 else r['rule_id']
                     for r in top_rules]
        hit_counts = [r['hit_count'] for r in top_rules]

        y_pos = range(len(rule_names))

        # Create horizontal bar chart
        bars = ax.barh(y_pos, hit_counts, color=VisualizationHelpers.COLORS['primary'])

        # Add value labels
        for i, (bar, count) in enumerate(zip(bars, hit_counts)):
            width = bar.get_width()
            ax.text(width, i, f' {count:,}',
                   ha='left', va='center', fontsize=9)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(rule_names, fontsize=9)
        ax.set_xlabel('Hit Count', fontsize=11, weight='bold')
        ax.set_title(f'Top {top_n} Rules by Hit Count', fontsize=14, weight='bold', pad=20)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    @staticmethod
    def get_severity_color(severity: str) -> str:
        """
        Get color code for severity level.

        Args:
            severity (str): Severity level (critical, high, medium, low)

        Returns:
            str: Hex color code
        """
        severity_colors = {
            'critical': '#C0392B',
            'high': '#E74C3C',
            'medium': '#F39C12',
            'low': '#F1C40F',
            'info': '#3498DB'
        }

        return severity_colors.get(severity.lower(), '#95A5A6')
