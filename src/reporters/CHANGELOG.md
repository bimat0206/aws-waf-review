# Changelog - Reporters Module

All notable changes to the reporters module will be documented in this file.

## [1.1.1] - 2025-11-07

### Added

- **Prompt Exporter JSON Injection**: Prompt exports now include serialized rule inventories, traffic distributions, attack patterns, and compliance data directly inside the markdown templates.

### Changed

- **Prompt Export API**: `PromptExporter.export_all_prompts()` accepts logging configuration metadata so compliance prompts can describe destinations without manual edits.
- **Structured Placeholders**: Single-brace placeholders like `{current_rules}` and `{rule_metrics}` are automatically replaced during export, keeping all templates synchronized with the latest WAF metrics.

## [1.0.0] - 2025-11-07

### Added

#### Excel Report Generator (`excel_generator.py`)
- `ExcelReportGenerator` class for multi-sheet Excel workbook creation
- `generate_report()` - Main report generation orchestration
- `create_inventory_sheet()` - Web ACLs and resource inventory
- `create_executive_summary_sheet()` - High-level KPIs and metrics
- `create_traffic_analysis_sheet()` - Traffic patterns and geographic data
- `create_rule_effectiveness_sheet()` - Rule performance and attack types
- `create_client_analysis_sheet()` - IP analysis and bot detection
- `create_llm_recommendations_sheet()` - AI recommendations template
- Professional styling with color coding
- Conditional formatting for warnings and alerts
- Embedded chart images from matplotlib
- Auto-adjusted column widths
- Cell merging for headers and titles

#### Visualization Helpers (`visualization_helpers.py`)
- `VisualizationHelpers` class with static chart creation methods
- `create_action_distribution_chart()` - Pie chart for WAF actions
- `create_daily_traffic_chart()` - Line chart for traffic trends
- `create_geographic_threat_chart()` - Horizontal bar chart for countries
- `create_attack_type_chart()` - Horizontal bar chart for attack types
- `create_hourly_pattern_chart()` - Grouped bar chart for hourly patterns
- `create_rule_effectiveness_chart()` - Horizontal bar chart for rules
- `get_severity_color()` - Color mapping for severity levels
- Professional color scheme (red, green, orange, blue, purple)
- Matplotlib customization (fonts, grids, legends)
- Image buffer output (BytesIO) for Excel embedding
- High-resolution PNG rendering (150 DPI)

### Excel Report Structure

#### Sheet 1: Executive Summary
- **Title**: AWS WAF Security Analysis - Executive Summary
- **Content**:
  - Key metrics table (8 rows)
    - Total Requests Analyzed
    - Blocked Requests
    - Block Rate
    - Unique Client IPs
    - Unique Countries
    - Web ACLs Configured
    - Protected Resources
    - Logging Coverage
  - Analysis period (start/end dates)
  - Action distribution pie chart (embedded image)
- **Styling**: Bold headers, 16pt title, 30x20 column widths

#### Sheet 2: Inventory
- **Title**: AWS WAF Inventory
- **Content**:
  - Web ACLs table with columns:
    - Name, ID, Scope, Default Action, Capacity, Logging Enabled
  - Color coding: Red for missing logging, green for enabled
  - Protected resources table with columns:
    - Web ACL Name, Resource Type, Resource ARN
- **Styling**: Header row with dark blue background, white text

#### Sheet 3: Traffic Analysis
- **Title**: Traffic Analysis
- **Content**:
  - Daily traffic trends line chart (embedded, 800x400px)
  - Geographic distribution table (top 20 countries)
    - Country, Total Requests, Blocked, Allowed, Threat Score
  - Color coding for threat scores (red >50%, yellow >25%)
  - Geographic threat chart (embedded, 800x500px)
- **Styling**: Auto-filter on tables, 18px column widths

#### Sheet 4: Rule Effectiveness
- **Title**: Rule Effectiveness Analysis
- **Content**:
  - Rule effectiveness table with columns:
    - Rule ID, Type, Hit Count, Blocks, Allows, Hit Rate %, Block Rate %
  - Color coding: Red for 0% hit rate, green for >10%
  - Rule effectiveness chart (embedded, 800x500px)
  - Attack type distribution chart (embedded, 700x500px)
- **Styling**: 50px width for Rule ID column, truncated names

#### Sheet 5: Client Analysis
- **Title**: Client and Bot Analysis
- **Content**:
  - Top blocked IPs table (top 30)
    - IP, Country, Block Count, Unique Rules Hit, First Seen, Last Seen
  - Bot traffic statistics
    - JA3 fingerprint count
    - JA4 fingerprint count
  - Top user agents list (top 15)
  - Hourly pattern chart (embedded, 800x400px)
- **Styling**: 50px width for IP column, 18px for timestamps

#### Sheet 6: LLM Recommendations
- **Title**: AI-Generated Security Recommendations
- **Content**:
  - Instructions section (4 bullet points)
  - Four priority sections:
    - Critical Findings (immediate action)
    - High Priority Recommendations (30 days)
    - Medium Priority Optimizations (90 days)
    - Low Priority Suggestions (nice to have)
  - Each section has table with columns:
    - Priority, Finding/Recommendation, Impact, Action Items
  - 3 empty rows per section for manual population
- **Styling**: Light blue fill for section headers, italic instructions

### Chart Specifications

#### Action Distribution Pie Chart
- Type: Pie chart
- Size: 600x400px
- Colors: Red (BLOCK), Green (ALLOW), Orange (COUNT), Blue (CAPTCHA), Purple (CHALLENGE)
- Labels: Action names with percentages
- Font: 11pt labels, 10pt percentages
- Format: PNG, 150 DPI

#### Daily Traffic Line Chart
- Type: Multi-line chart
- Size: 800x400px
- Lines: Total Requests (blue), Blocked (red), Allowed (green)
- Markers: Circle, square, triangle
- X-axis: Date (rotated 45°)
- Y-axis: Request count
- Grid: Dotted, 30% opacity
- Legend: Top right with shadow

#### Geographic Threat Horizontal Bar Chart
- Type: Horizontal stacked bar chart
- Size: 800x500px
- Bars: Blocked (red), Allowed (green)
- Y-axis: Country codes/names
- X-axis: Request count
- Top N: 15 countries
- Grid: X-axis only, dotted

#### Attack Type Horizontal Bar Chart
- Type: Horizontal bar chart
- Size: 700x500px
- Bars: Red color
- Labels: Count values on bars
- Categories: SQLi, XSS, scanners, bots, etc.
- Sorted: Descending by count

#### Hourly Pattern Grouped Bar Chart
- Type: Grouped bar chart
- Size: 800x400px
- Groups: Blocked (red), Allowed (green)
- X-axis: Hours (00:00 to 23:00)
- Y-axis: Request count
- Bar width: 0.35
- X-labels: Rotated 45°

#### Rule Effectiveness Horizontal Bar Chart
- Type: Horizontal bar chart
- Size: 800x500px
- Bars: Blue color
- Labels: Hit count on bars
- Y-axis: Rule IDs (truncated to 40 chars)
- Top N: 15 rules
- Sorted: Descending by hit count

### Features

#### Excel Generation
- **Multi-Sheet**: 6 sheets with different purposes
- **Professional Styling**: Consistent fonts, colors, borders
- **Conditional Formatting**: Automatic color coding based on values
- **Auto-Sizing**: Column widths adjusted to content
- **Cell Merging**: Headers and titles merged across columns
- **Data Validation**: Auto-filters on data tables
- **Image Embedding**: Charts embedded as images using XLImage
- **Metadata**: Timestamps and version information

#### Visualization
- **Consistent Colors**: Professional color scheme across all charts
- **High Quality**: 150 DPI rendering for crisp images
- **Error Handling**: Graceful fallback if chart generation fails
- **Memory Efficient**: Charts created as BytesIO buffers
- **No Display Required**: Uses 'Agg' backend (no GUI needed)
- **Customizable**: Easy to modify colors, sizes, styles

### Technical Details

#### Excel Generation
- Library: `openpyxl==3.1.2`
- Format: `.xlsx` (Office Open XML)
- Max rows: 1,048,576 per sheet
- Max columns: 16,384 per sheet
- Image format: PNG embedded in workbook
- File size: Typically 1-5 MB for standard reports

#### Visualization
- Library: `matplotlib==3.8.0`
- Backend: 'Agg' (non-interactive)
- Image format: PNG via BytesIO
- Resolution: 150 DPI
- Color space: RGB
- Font: Default matplotlib font

#### Styling Classes
```python
# Fonts
header_font = Font(bold=True, size=12, color='FFFFFF')
title_font = Font(bold=True, size=14)

# Fills
header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')

# Alignment
center_align = Alignment(horizontal='center')
```

#### Color Scheme
```python
COLORS = {
    'block': '#E74C3C',      # Red
    'allow': '#27AE60',      # Green
    'count': '#F39C12',      # Orange
    'captcha': '#3498DB',    # Blue
    'challenge': '#9B59B6',  # Purple
    'primary': '#2C3E50',    # Dark blue
    'danger': '#E74C3C',     # Red
    'warning': '#F39C12',    # Orange
    'success': '#27AE60'     # Green
}
```

### Performance

#### Generation Time
- Small datasets (<10k logs): 5-10 seconds
- Medium datasets (10k-100k logs): 10-30 seconds
- Large datasets (>100k logs): 30-60 seconds
- Chart generation: 1-2 seconds per chart
- Total charts: 6 (5-10 seconds total)

#### Memory Usage
- Base: ~50 MB for openpyxl
- Per chart: ~10-20 MB during generation
- Final file: 1-5 MB
- Peak: ~100-150 MB for large reports

#### File Size
- Typical: 1-3 MB
- With large tables: 3-5 MB
- Images contribute: ~100-200 KB per chart
- Compression: Automatic in .xlsx format

### Error Handling
- Missing data: Generates empty tables with headers
- Chart failures: Logs warning and continues without chart
- Invalid data: Shows "No data available" message
- File write errors: Raises exception with clear message
- Memory errors: Chunked processing where possible

### Known Limitations
- Large datasets (>500k rows) may exceed Excel row limit
- Chart generation requires matplotlib (no fallback)
- Image quality fixed at 150 DPI (not configurable)
- Color scheme not customizable without code changes
- No support for Excel formulas or pivot tables
- Manual population required for LLM Recommendations sheet

### Future Enhancements
- [ ] PDF export option
- [ ] HTML report generation
- [ ] Interactive charts (Plotly)
- [ ] Configurable color schemes
- [ ] Excel formulas for dynamic calculations
- [ ] Pivot tables for drill-down analysis
- [ ] Chart customization via config file
- [ ] Multi-language support
- [ ] Corporate branding/logo support
- [ ] Email delivery integration
- [ ] Scheduled report generation
- [ ] Comparison reports (current vs previous)

### Usage Examples

#### Basic Report Generation
```python
from reporters.excel_generator import ExcelReportGenerator

generator = ExcelReportGenerator('waf_report.xlsx')
generator.generate_report(metrics, web_acls, resources, logging_configs)
```

#### Custom Output Path
```python
from datetime import datetime

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_path = f'reports/waf_report_{timestamp}.xlsx'

generator = ExcelReportGenerator(output_path)
generator.generate_report(metrics, web_acls, resources, logging_configs)
```

#### Standalone Chart Creation
```python
from reporters.visualization_helpers import VisualizationHelpers

viz = VisualizationHelpers()
chart_buffer = viz.create_action_distribution_chart(action_data)

# Save to file
with open('action_chart.png', 'wb') as f:
    f.write(chart_buffer.read())
```

### Dependencies
- `openpyxl==3.1.2` - Excel file creation
- `matplotlib==3.8.0` - Chart generation
- `pandas==2.2.0` - Data frame handling
- `Pillow` - Image handling (via openpyxl)
- `io.BytesIO` - In-memory buffers

### Compatibility
- Excel: 2007+ (.xlsx format)
- LibreOffice: Calc 5.0+
- Google Sheets: Full import support
- Apple Numbers: Import supported
- Python: 3.9+
