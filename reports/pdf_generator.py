"""
PDF Report Generator for Weekly Economic Indicators
Uses ReportLab for PDF generation
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import io


class PDFReportGenerator:
    """Generate PDF reports for economic indicators"""

    # Colors matching the original report
    COLORS = {
        'header_bg': colors.Color(0.2, 0.4, 0.2),  # Dark green
        'good': colors.Color(0.78, 0.94, 0.81),     # Light green
        'neutral': colors.Color(1.0, 0.92, 0.61),   # Light yellow
        'bad': colors.Color(1.0, 0.78, 0.81),       # Light red
        'border': colors.Color(0.8, 0.8, 0.8),
        'text': colors.black,
        'header_text': colors.white
    }

    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "output"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=TA_LEFT
        ))

        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=20
        ))

        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=4,
            spaceAfter=4
        ))

        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        ))

    def _get_cell_color(self, value: float, indicator_type: str) -> colors.Color:
        """Determine cell background color based on value and indicator type"""
        if pd.isna(value):
            return colors.white

        if indicator_type == 'pmi':
            if value >= 55:
                return self.COLORS['good']
            elif value >= 50:
                return colors.Color(0.85, 0.95, 0.85)  # Lighter green
            elif value >= 45:
                return self.COLORS['bad']
            else:
                return colors.Color(1.0, 0.6, 0.6)  # Darker red

        elif indicator_type == 'inflation':
            if 1.5 <= value <= 2.5:
                return self.COLORS['good']
            elif value < 1.5 or value > 3.5:
                return self.COLORS['bad']
            else:
                return self.COLORS['neutral']

        elif indicator_type == 'sentiment':
            if value >= 65:
                return self.COLORS['good']
            elif value >= 55:
                return self.COLORS['neutral']
            else:
                return self.COLORS['bad']

        elif indicator_type == 'spread':
            if value <= 0.2:
                return self.COLORS['good']
            elif value <= 0.35:
                return self.COLORS['neutral']
            else:
                return self.COLORS['bad']

        return colors.white

    def create_key_metrics_table(self, metrics: Dict[str, Any]) -> Table:
        """Create the top key metrics summary table"""
        data = [
            ['Consumer Price Index\n(Dec)', 'Live Register\n(Dec)',
             'Consumer Sentiment\nIndex (Dec)', '10-year bond spread\n(as of date)',
             'Euro-Sterling\n(as of date)'],
            [
                f"{metrics.get('cpi', 'N/A')}%",
                f"{metrics.get('live_register', 'N/A'):,}",
                f"{metrics.get('sentiment', 'N/A')}",
                f"{metrics.get('bond_spread', 'N/A')}",
                f"£{metrics.get('eur_gbp', 'N/A')}"
            ]
        ]

        table = Table(data, colWidths=[2.8*cm]*5)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['header_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        return table

    def create_heatmap_table(self, data: pd.DataFrame) -> Table:
        """Create the heatmap table for page 2"""
        # Prepare headers
        headers = ['Irish Economy Indicator\nHeatmap'] + list(data.columns[1:])

        # Convert DataFrame to list of lists
        table_data = [headers]
        for _, row in data.iterrows():
            table_data.append([str(v) if pd.notna(v) else 'N/A' for v in row])

        # Create table
        col_widths = [4*cm] + [1.2*cm] * (len(headers) - 1)
        table = Table(table_data, colWidths=col_widths)

        # Base style
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['header_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ]

        table.setStyle(TableStyle(style))

        return table

    def generate_report(self, data: Dict[str, Any],
                       commentary: List[str],
                       report_date: datetime = None,
                       filename: str = None) -> Path:
        """
        Generate the full PDF report

        Args:
            data: Dictionary containing all data for the report
            commentary: List of bullet point commentary strings
            report_date: Date for the report (defaults to now)
            filename: Output filename (defaults to date-based name)

        Returns:
            Path to the generated PDF
        """
        if report_date is None:
            report_date = datetime.now()

        if filename is None:
            filename = f"Weekly Economic Indicators - {report_date.strftime('%d %b %Y')}.pdf"

        output_path = self.output_dir / filename

        # Create document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )

        # Build content
        story = []

        # Header
        header_table = Table([
            [Paragraph('Economic Indicators', self.styles['ReportTitle']),
             Paragraph(report_date.strftime('%d %B %Y'), self.styles['ReportSubtitle'])]
        ], colWidths=[12*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 12))

        # Key metrics table
        if 'key_metrics' in data:
            story.append(self.create_key_metrics_table(data['key_metrics']))
            story.append(Spacer(1, 12))

        # Commentary bullets
        for bullet in commentary:
            bullet_text = f"• {bullet}"
            story.append(Paragraph(bullet_text, self.styles['BulletPoint']))

        story.append(Spacer(1, 20))

        # Note: Charts would be added here as images
        # For now, add placeholder text
        story.append(Paragraph(
            "<i>Charts are available in the interactive web dashboard</i>",
            self.styles['Normal']
        ))

        # Page break for heatmap
        story.append(PageBreak())

        # Page 2 header
        story.append(header_table)
        story.append(Spacer(1, 12))

        # Heatmap table
        if 'heatmap_data' in data:
            story.append(self.create_heatmap_table(data['heatmap_data']))

        # Footer
        story.append(Spacer(1, 20))
        footer_table = Table([
            ['IGEES', 'DOT Economic Policy Unit']
        ], colWidths=[9*cm, 9*cm])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(footer_table)

        # Build PDF
        doc.build(story)

        return output_path


# Test
if __name__ == "__main__":
    generator = PDFReportGenerator()

    # Test data
    test_data = {
        'key_metrics': {
            'cpi': 2.8,
            'live_register': 172224,
            'sentiment': 61.2,
            'bond_spread': 0.112,
            'eur_gbp': 0.868
        }
    }

    test_commentary = [
        "The monthly Live Register (unadjusted) for December stood at 172,224.",
        "The market average rate for a 40ft container from Asia to North Europe increased to $2,730.",
        "UK Natural Gas futures last week traded between 87.50 and 106.77 GBp/Thm."
    ]

    output = generator.generate_report(test_data, test_commentary)
    print(f"Generated report: {output}")
