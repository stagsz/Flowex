"""DXF/DWG export service for P&ID drawings."""

import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import ezdxf
from ezdxf import units
from ezdxf.document import Drawing as DXFDocument
from ezdxf.enums import TextEntityAlignment
from ezdxf.layouts import Modelspace

from app.services.export.symbol_blocks import ISO10628BlockLibrary

if TYPE_CHECKING:
    from app.models.drawing import Drawing
    from app.models.line import Line
    from app.models.symbol import Symbol
    from app.models.text_annotation import TextAnnotation

logger = logging.getLogger(__name__)


class PaperSize(str, Enum):
    """Standard paper sizes for export."""

    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


# Paper dimensions in mm (width, height for landscape)
PAPER_DIMENSIONS = {
    PaperSize.A0: (1189, 841),
    PaperSize.A1: (841, 594),
    PaperSize.A2: (594, 420),
    PaperSize.A3: (420, 297),
    PaperSize.A4: (297, 210),
}


@dataclass
class ExportOptions:
    """Configuration options for DXF export."""

    format: str = "dxf"  # dxf or dwg
    paper_size: PaperSize = PaperSize.A1
    scale: str = "1:50"
    include_connections: bool = True
    include_annotations: bool = True
    include_title_block: bool = True


@dataclass
class TitleBlockInfo:
    """Information for the title block."""

    drawing_number: str
    drawing_title: str
    project_name: str
    revision: str = "A"
    date: str = ""
    prepared_by: str = "Flowex"
    checked_by: str = ""
    approved_by: str = ""


class LayerConfig:
    """DXF layer configuration per ISO 10628 spec."""

    LAYERS = [
        # (name, color, linetype, description)
        ("EQUIPMENT", 4, "Continuous", "Equipment symbols"),  # Cyan
        ("INSTRUMENTS", 6, "Continuous", "Instrument symbols"),  # Magenta
        ("VALVES", 3, "Continuous", "Valve symbols"),  # Green
        ("PIPING-PROCESS", 7, "Continuous", "Process piping"),  # White
        ("PIPING-UTILITY", 2, "DASHED", "Utility piping"),  # Yellow
        ("PIPING-INSTRUMENT", 5, "DASHED2", "Instrument lines"),  # Blue
        ("TEXT-TAGS", 7, "Continuous", "Equipment/tag labels"),  # White
        ("TEXT-LABELS", 7, "Continuous", "General labels"),  # White
        ("TEXT-NOTES", 8, "Continuous", "Annotations"),  # Gray
        ("TITLE-BLOCK", 7, "Continuous", "Title block"),  # White
        ("BORDER", 7, "Continuous", "Drawing border"),  # White
    ]

    @classmethod
    def get_layer_for_symbol(cls, category: str) -> str:
        """Get the appropriate layer for a symbol category."""
        mapping = {
            "equipment": "EQUIPMENT",
            "instrument": "INSTRUMENTS",
            "valve": "VALVES",
            "other": "EQUIPMENT",
        }
        return mapping.get(category.lower(), "EQUIPMENT")

    @classmethod
    def get_layer_for_line(cls, line_spec: str | None) -> str:
        """Get the appropriate layer for a line based on spec."""
        if not line_spec:
            return "PIPING-PROCESS"

        spec_lower = line_spec.lower()
        if "instrument" in spec_lower or "signal" in spec_lower:
            return "PIPING-INSTRUMENT"
        elif "utility" in spec_lower or "steam" in spec_lower or "air" in spec_lower:
            return "PIPING-UTILITY"
        return "PIPING-PROCESS"


class DXFExportService:
    """Service for exporting P&ID drawings to DXF format."""

    def __init__(self):
        self.doc: DXFDocument | None = None
        self.msp: Modelspace | None = None
        self.block_library: ISO10628BlockLibrary | None = None

    def export_drawing(
        self,
        drawing: "Drawing",
        symbols: list["Symbol"],
        lines: list["Line"],
        text_annotations: list["TextAnnotation"],
        options: ExportOptions | None = None,
        title_info: TitleBlockInfo | None = None,
    ) -> Path:
        """
        Export a P&ID drawing to DXF format.

        Args:
            drawing: The drawing model
            symbols: List of detected symbols
            lines: List of detected lines
            text_annotations: List of text annotations
            options: Export configuration options
            title_info: Title block information

        Returns:
            Path to the generated DXF file
        """
        if options is None:
            options = ExportOptions()

        if title_info is None:
            title_info = TitleBlockInfo(
                drawing_number=drawing.original_filename.rsplit(".", 1)[0],
                drawing_title=drawing.original_filename,
                project_name=drawing.project.name if drawing.project else "Unknown",
                date=datetime.utcnow().strftime("%Y-%m-%d"),
            )

        # Initialize DXF document
        self._initialize_document(options)

        # Create layers
        self._create_layers()

        # Create symbol block library
        self.block_library = ISO10628BlockLibrary(self.doc)

        # Get paper dimensions for scaling
        paper_width, paper_height = PAPER_DIMENSIONS[options.paper_size]

        # Place symbols
        self._place_symbols(symbols, options)

        # Draw lines
        self._draw_lines(lines, options)

        # Add text annotations
        if options.include_annotations:
            self._add_text_annotations(text_annotations)

        # Add title block
        if options.include_title_block:
            self._add_title_block(title_info, options)

        # Add border
        self._add_border(options)

        # Save file
        output_path = self._save_file(drawing.id, options)

        logger.info(f"DXF export completed: {output_path}")
        return output_path

    def _initialize_document(self, options: ExportOptions) -> None:
        """Initialize a new DXF document."""
        self.doc = ezdxf.new("R2018")  # AutoCAD 2018 format
        self.doc.units = units.MM
        self.msp = self.doc.modelspace()

        # Set up text styles
        self.doc.styles.add("STANDARD", font="arial.ttf")
        self.doc.styles.add("TAGS", font="arial.ttf")

        # Set up line types
        self._setup_linetypes()

    def _setup_linetypes(self) -> None:
        """Set up custom line types."""
        # DASHED2 for instrument lines (shorter dashes)
        if "DASHED2" not in self.doc.linetypes:
            self.doc.linetypes.add(
                "DASHED2",
                pattern=[0.25, 0.125, -0.125],
                description="Short dashed line",
            )

    def _create_layers(self) -> None:
        """Create all required layers."""
        for name, color, linetype, _description in LayerConfig.LAYERS:
            try:
                self.doc.layers.add(name, color=color, linetype=linetype)
            except ezdxf.DXFTableEntryError:
                # Layer already exists
                layer = self.doc.layers.get(name)
                layer.color = color
                layer.linetype = linetype

    def _place_symbols(self, symbols: list["Symbol"], options: ExportOptions) -> None:
        """Place symbol blocks in the drawing."""
        for symbol in symbols:
            if symbol.is_deleted:
                continue

            # Get or create the block for this symbol class
            block_name = self.block_library.get_or_create_block(symbol.symbol_class)

            # Calculate insertion point (center of bbox)
            x = symbol.bbox_x + symbol.bbox_width / 2
            y = symbol.bbox_y + symbol.bbox_height / 2

            # Determine layer
            layer = LayerConfig.get_layer_for_symbol(symbol.category.value)

            # Insert block reference
            block_ref = self.msp.add_blockref(
                block_name,
                insert=(x, y),
                dxfattribs={
                    "layer": layer,
                    "rotation": 0,  # Add rotation if stored in symbol
                },
            )

            # Add tag number as attribute if present
            if symbol.tag_number:
                # Add text below the symbol
                self.msp.add_text(
                    symbol.tag_number,
                    dxfattribs={
                        "layer": "TEXT-TAGS",
                        "height": 2.5,
                        "style": "TAGS",
                    },
                ).set_placement(
                    (x, y - symbol.bbox_height / 2 - 5),
                    align=TextEntityAlignment.MIDDLE_CENTER,
                )

    def _draw_lines(self, lines: list["Line"], options: ExportOptions) -> None:
        """Draw piping lines."""
        for line in lines:
            if line.is_deleted:
                continue

            # Determine layer based on line spec
            layer = LayerConfig.get_layer_for_line(line.line_spec)

            # Determine line weight based on layer
            lineweight = self._get_lineweight(layer)

            # Draw the line
            self.msp.add_line(
                (line.start_x, line.start_y),
                (line.end_x, line.end_y),
                dxfattribs={
                    "layer": layer,
                    "lineweight": lineweight,
                },
            )

            # Add line number label if present
            if line.line_number:
                # Place label at midpoint
                mid_x = (line.start_x + line.end_x) / 2
                mid_y = (line.start_y + line.end_y) / 2
                self.msp.add_text(
                    line.line_number,
                    dxfattribs={
                        "layer": "TEXT-LABELS",
                        "height": 2.0,
                    },
                ).set_placement(
                    (mid_x, mid_y + 3),
                    align=TextEntityAlignment.MIDDLE_CENTER,
                )

    def _get_lineweight(self, layer: str) -> int:
        """Get line weight based on layer (in 1/100 mm)."""
        weights = {
            "PIPING-PROCESS": 50,  # 0.5mm
            "PIPING-UTILITY": 35,  # 0.35mm
            "PIPING-INSTRUMENT": 25,  # 0.25mm
            "BORDER": 70,  # 0.7mm
        }
        return weights.get(layer, 25)

    def _add_text_annotations(self, annotations: list["TextAnnotation"]) -> None:
        """Add text annotations to the drawing."""
        for annotation in annotations:
            if annotation.is_deleted:
                continue

            # Calculate position (center of bbox)
            x = annotation.bbox_x + annotation.bbox_width / 2
            y = annotation.bbox_y + annotation.bbox_height / 2

            # Estimate text height based on bbox
            text_height = min(annotation.bbox_height * 0.8, 5.0)
            text_height = max(text_height, 1.5)  # Minimum readable size

            self.msp.add_text(
                annotation.text_content,
                dxfattribs={
                    "layer": "TEXT-LABELS",
                    "height": text_height,
                    "rotation": annotation.rotation,
                },
            ).set_placement(
                (x, y),
                align=TextEntityAlignment.MIDDLE_CENTER,
            )

    def _add_title_block(self, title_info: TitleBlockInfo, options: ExportOptions) -> None:
        """Add title block to the drawing."""
        paper_width, paper_height = PAPER_DIMENSIONS[options.paper_size]

        # Title block position (bottom right)
        tb_width = 180
        tb_height = 60
        tb_x = paper_width - tb_width - 10
        tb_y = 10

        layer = "TITLE-BLOCK"

        # Outer border
        self.msp.add_lwpolyline(
            [
                (tb_x, tb_y),
                (tb_x + tb_width, tb_y),
                (tb_x + tb_width, tb_y + tb_height),
                (tb_x, tb_y + tb_height),
            ],
            close=True,
            dxfattribs={"layer": layer},
        )

        # Horizontal dividers
        self.msp.add_line(
            (tb_x, tb_y + tb_height - 15),
            (tb_x + tb_width, tb_y + tb_height - 15),
            dxfattribs={"layer": layer},
        )
        self.msp.add_line(
            (tb_x, tb_y + 15),
            (tb_x + tb_width, tb_y + 15),
            dxfattribs={"layer": layer},
        )
        self.msp.add_line(
            (tb_x, tb_y + 30),
            (tb_x + tb_width, tb_y + 30),
            dxfattribs={"layer": layer},
        )

        # Vertical dividers
        self.msp.add_line(
            (tb_x + 60, tb_y),
            (tb_x + 60, tb_y + 30),
            dxfattribs={"layer": layer},
        )
        self.msp.add_line(
            (tb_x + 120, tb_y),
            (tb_x + 120, tb_y + 30),
            dxfattribs={"layer": layer},
        )

        # Text content
        text_height = 3.0
        small_text = 2.0

        # Title (top section)
        self.msp.add_text(
            title_info.drawing_title,
            dxfattribs={"layer": layer, "height": text_height + 1},
        ).set_placement(
            (tb_x + tb_width / 2, tb_y + tb_height - 7),
            align=TextEntityAlignment.MIDDLE_CENTER,
        )

        # Project name
        self.msp.add_text(
            title_info.project_name,
            dxfattribs={"layer": layer, "height": text_height},
        ).set_placement(
            (tb_x + tb_width / 2, tb_y + tb_height - 22),
            align=TextEntityAlignment.MIDDLE_CENTER,
        )

        # Drawing number
        self.msp.add_text(
            f"DWG: {title_info.drawing_number}",
            dxfattribs={"layer": layer, "height": text_height},
        ).set_placement(
            (tb_x + tb_width / 2, tb_y + tb_height - 37),
            align=TextEntityAlignment.MIDDLE_CENTER,
        )

        # Labels in bottom row
        self.msp.add_text(
            "Prepared",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement((tb_x + 30, tb_y + 25), align=TextEntityAlignment.MIDDLE_CENTER)

        self.msp.add_text(
            "Checked",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement((tb_x + 90, tb_y + 25), align=TextEntityAlignment.MIDDLE_CENTER)

        self.msp.add_text(
            "Approved",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement((tb_x + 150, tb_y + 25), align=TextEntityAlignment.MIDDLE_CENTER)

        # Values in bottom row
        self.msp.add_text(
            title_info.prepared_by,
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement((tb_x + 30, tb_y + 7), align=TextEntityAlignment.MIDDLE_CENTER)

        self.msp.add_text(
            title_info.checked_by or "-",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement((tb_x + 90, tb_y + 7), align=TextEntityAlignment.MIDDLE_CENTER)

        self.msp.add_text(
            title_info.approved_by or "-",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement((tb_x + 150, tb_y + 7), align=TextEntityAlignment.MIDDLE_CENTER)

        # Revision and date (top right corner)
        self.msp.add_text(
            f"Rev: {title_info.revision}",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement(
            (tb_x + tb_width - 5, tb_y + tb_height + 3),
            align=TextEntityAlignment.BOTTOM_RIGHT,
        )

        self.msp.add_text(
            f"Date: {title_info.date}",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement(
            (tb_x + 5, tb_y + tb_height + 3),
            align=TextEntityAlignment.BOTTOM_LEFT,
        )

        # Scale
        self.msp.add_text(
            f"Scale: {options.scale}",
            dxfattribs={"layer": layer, "height": small_text},
        ).set_placement(
            (tb_x + tb_width / 2, tb_y - 3),
            align=TextEntityAlignment.TOP_CENTER,
        )

    def _add_border(self, options: ExportOptions) -> None:
        """Add drawing border."""
        paper_width, paper_height = PAPER_DIMENSIONS[options.paper_size]
        margin = 10  # 10mm margin

        self.msp.add_lwpolyline(
            [
                (margin, margin),
                (paper_width - margin, margin),
                (paper_width - margin, paper_height - margin),
                (margin, paper_height - margin),
            ],
            close=True,
            dxfattribs={
                "layer": "BORDER",
                "lineweight": 70,  # 0.7mm thick border
            },
        )

    def _save_file(self, drawing_id: uuid.UUID, options: ExportOptions) -> Path:
        """Save the DXF file."""
        # Create temp directory if needed
        output_dir = Path(tempfile.gettempdir()) / "flowex_exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"{drawing_id}.dxf"
        output_path = output_dir / filename

        # Save
        self.doc.saveas(output_path)

        return output_path


def export_drawing_to_dxf(
    drawing: "Drawing",
    symbols: list["Symbol"],
    lines: list["Line"],
    text_annotations: list["TextAnnotation"],
    options: ExportOptions | None = None,
    title_info: TitleBlockInfo | None = None,
) -> Path:
    """
    Convenience function to export a drawing to DXF.

    Args:
        drawing: The drawing model
        symbols: List of detected symbols
        lines: List of detected lines
        text_annotations: List of text annotations
        options: Export configuration options
        title_info: Title block information

    Returns:
        Path to the generated DXF file
    """
    service = DXFExportService()
    return service.export_drawing(
        drawing, symbols, lines, text_annotations, options, title_info
    )
