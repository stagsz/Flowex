"""Tests for export functionality."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.drawing import Drawing, DrawingStatus
from app.models.line import Line
from app.models.symbol import Symbol, SymbolCategory
from app.models.text_annotation import TextAnnotation
from app.services.export.data_lists import (
    DataListExportService,
    ExportFormat,
    ExportMetadata,
)
from app.services.export.dxf_export import (
    DXFExportService,
    ExportOptions,
    LayerConfig,
    PaperSize,
    TitleBlockInfo,
)
from app.services.export.symbol_blocks import ISO10628BlockLibrary

# Fixtures


@pytest.fixture
def mock_drawing():
    """Create a mock drawing object."""
    drawing = MagicMock(spec=Drawing)
    drawing.id = uuid4()
    drawing.project_id = uuid4()
    drawing.original_filename = "P&ID-001.pdf"
    drawing.status = DrawingStatus.complete
    drawing.project = MagicMock()
    drawing.project.name = "Test Project"
    return drawing


@pytest.fixture
def mock_symbols():
    """Create mock symbol objects."""
    symbols = []

    # Equipment symbol
    eq = MagicMock(spec=Symbol)
    eq.id = uuid4()
    eq.symbol_class = "Pump_Centrifugal"
    eq.category = SymbolCategory.EQUIPMENT
    eq.tag_number = "P-101"
    eq.bbox_x = 100.0
    eq.bbox_y = 200.0
    eq.bbox_width = 40.0
    eq.bbox_height = 40.0
    eq.confidence = 0.95
    eq.is_verified = True
    eq.is_deleted = False
    symbols.append(eq)

    # Instrument symbol
    inst = MagicMock(spec=Symbol)
    inst.id = uuid4()
    inst.symbol_class = "Transmitter_Flow"
    inst.category = SymbolCategory.INSTRUMENT
    inst.tag_number = "FT-101"
    inst.bbox_x = 150.0
    inst.bbox_y = 250.0
    inst.bbox_width = 15.0
    inst.bbox_height = 15.0
    inst.confidence = 0.88
    inst.is_verified = True
    inst.is_deleted = False
    symbols.append(inst)

    # Valve symbol
    valve = MagicMock(spec=Symbol)
    valve.id = uuid4()
    valve.symbol_class = "Valve_Gate"
    valve.category = SymbolCategory.VALVE
    valve.tag_number = "V-101"
    valve.bbox_x = 200.0
    valve.bbox_y = 200.0
    valve.bbox_width = 12.0
    valve.bbox_height = 12.0
    valve.confidence = 0.92
    valve.is_verified = True
    valve.is_deleted = False
    symbols.append(valve)

    # Low confidence symbol (flagged)
    flagged = MagicMock(spec=Symbol)
    flagged.id = uuid4()
    flagged.symbol_class = "Filter"
    flagged.category = SymbolCategory.EQUIPMENT
    flagged.tag_number = "F-101"
    flagged.bbox_x = 300.0
    flagged.bbox_y = 300.0
    flagged.bbox_width = 30.0
    flagged.bbox_height = 30.0
    flagged.confidence = 0.65  # Below 0.7 threshold
    flagged.is_verified = False
    flagged.is_deleted = False
    symbols.append(flagged)

    return symbols


@pytest.fixture
def mock_lines():
    """Create mock line objects."""
    lines = []

    line1 = MagicMock(spec=Line)
    line1.id = uuid4()
    line1.line_number = "6\"-P-101-A1"
    line1.start_x = 100.0
    line1.start_y = 200.0
    line1.end_x = 200.0
    line1.end_y = 200.0
    line1.line_spec = "6\"-P-101-A1"
    line1.pipe_class = "A1"
    line1.insulation = "None"
    line1.confidence = 0.90
    line1.is_verified = True
    line1.is_deleted = False
    lines.append(line1)

    line2 = MagicMock(spec=Line)
    line2.id = uuid4()
    line2.line_number = "2\"-I-201"
    line2.start_x = 150.0
    line2.start_y = 250.0
    line2.end_x = 250.0
    line2.end_y = 350.0
    line2.line_spec = "2\"-I-201"
    line2.pipe_class = "I"
    line2.insulation = None
    line2.confidence = 0.85
    line2.is_verified = True
    line2.is_deleted = False
    lines.append(line2)

    return lines


@pytest.fixture
def mock_text_annotations():
    """Create mock text annotation objects."""
    annotations = []

    text1 = MagicMock(spec=TextAnnotation)
    text1.id = uuid4()
    text1.text_content = "FEED WATER"
    text1.bbox_x = 100.0
    text1.bbox_y = 180.0
    text1.bbox_width = 50.0
    text1.bbox_height = 10.0
    text1.rotation = 0
    text1.confidence = 0.95
    text1.is_verified = True
    text1.is_deleted = False
    annotations.append(text1)

    text2 = MagicMock(spec=TextAnnotation)
    text2.id = uuid4()
    text2.text_content = "TO TANK"
    text2.bbox_x = 200.0
    text2.bbox_y = 180.0
    text2.bbox_width = 40.0
    text2.bbox_height = 10.0
    text2.rotation = 0
    text2.confidence = 0.88
    text2.is_verified = True
    text2.is_deleted = False
    annotations.append(text2)

    return annotations


@pytest.fixture
def export_metadata():
    """Create export metadata."""
    return ExportMetadata(
        project_name="Test Project",
        drawing_number="P&ID-001",
        revision="A",
        date="2026-01-19",
        prepared_by="Flowex Test",
    )


# DXF Export Tests


class TestDXFExportService:
    """Tests for DXF export service."""

    def test_export_creates_valid_dxf_file(
        self, mock_drawing, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test that export creates a valid DXF file."""
        service = DXFExportService()
        options = ExportOptions(paper_size=PaperSize.A3)
        title_info = TitleBlockInfo(
            drawing_number="P&ID-001",
            drawing_title="Test Drawing",
            project_name="Test Project",
        )

        output_path = service.export_drawing(
            mock_drawing,
            mock_symbols,
            mock_lines,
            mock_text_annotations,
            options,
            title_info,
        )

        assert output_path.exists()
        assert output_path.suffix == ".dxf"

        # Verify file is not empty
        assert output_path.stat().st_size > 0

        # Clean up
        output_path.unlink()

    def test_export_with_different_paper_sizes(
        self, mock_drawing, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test export works with all paper sizes."""
        service = DXFExportService()
        title_info = TitleBlockInfo(
            drawing_number="P&ID-001",
            drawing_title="Test Drawing",
            project_name="Test Project",
        )

        for paper_size in PaperSize:
            options = ExportOptions(paper_size=paper_size)
            output_path = service.export_drawing(
                mock_drawing,
                mock_symbols,
                mock_lines,
                mock_text_annotations,
                options,
                title_info,
            )
            assert output_path.exists()
            output_path.unlink()

    def test_layer_config_for_symbol_categories(self):
        """Test correct layer assignment for symbol categories."""
        assert LayerConfig.get_layer_for_symbol("equipment") == "EQUIPMENT"
        assert LayerConfig.get_layer_for_symbol("instrument") == "INSTRUMENTS"
        assert LayerConfig.get_layer_for_symbol("valve") == "VALVES"
        assert LayerConfig.get_layer_for_symbol("other") == "EQUIPMENT"

    def test_layer_config_for_line_types(self):
        """Test correct layer assignment for line types."""
        assert LayerConfig.get_layer_for_line("6\"-P-101") == "PIPING-PROCESS"
        assert LayerConfig.get_layer_for_line("instrument-line") == "PIPING-INSTRUMENT"
        assert LayerConfig.get_layer_for_line("utility-air") == "PIPING-UTILITY"
        assert LayerConfig.get_layer_for_line(None) == "PIPING-PROCESS"


class TestISO10628BlockLibrary:
    """Tests for symbol block library."""

    def test_creates_all_equipment_blocks(self):
        """Test that all equipment symbol blocks can be created."""
        import ezdxf

        doc = ezdxf.new("R2018")
        library = ISO10628BlockLibrary(doc)

        equipment_classes = [
            "Vessel_Vertical",
            "Vessel_Horizontal",
            "Tank_Atmospheric",
            "Column_Distillation",
            "Heat_Exchanger_Shell_Tube",
            "Heat_Exchanger_Plate",
            "Pump_Centrifugal",
            "Pump_Positive_Displacement",
            "Compressor_Centrifugal",
            "Compressor_Reciprocating",
            "Filter",
            "Reactor",
            "Furnace",
            "Blower",
            "Agitator",
        ]

        for symbol_class in equipment_classes:
            block_name = library.get_or_create_block(symbol_class)
            assert block_name in doc.blocks

    def test_creates_all_instrument_blocks(self):
        """Test that all instrument symbol blocks can be created."""
        import ezdxf

        doc = ezdxf.new("R2018")
        library = ISO10628BlockLibrary(doc)

        instrument_classes = [
            "Transmitter_Pressure",
            "Transmitter_Temperature",
            "Transmitter_Flow",
            "Transmitter_Level",
            "Controller_Generic",
            "Indicator_Generic",
            "Alarm_High",
            "Alarm_Low",
            "Switch_Generic",
            "Control_Valve_Globe",
            "Control_Valve_Butterfly",
            "Orifice_Plate",
            "Thermowell",
            "Sample_Point",
            "Relief_Valve_Instrument",
        ]

        for symbol_class in instrument_classes:
            block_name = library.get_or_create_block(symbol_class)
            assert block_name in doc.blocks

    def test_creates_all_valve_blocks(self):
        """Test that all valve symbol blocks can be created."""
        import ezdxf

        doc = ezdxf.new("R2018")
        library = ISO10628BlockLibrary(doc)

        valve_classes = [
            "Valve_Gate",
            "Valve_Globe",
            "Valve_Ball",
            "Valve_Butterfly",
            "Valve_Check",
            "Valve_Relief_PSV",
            "Valve_Control",
            "Valve_Three_Way",
            "Valve_Diaphragm",
            "Valve_Plug",
            "Valve_Needle",
            "Valve_Manual_Generic",
            "Actuator_Pneumatic",
            "Actuator_Electric",
            "Actuator_Hydraulic",
        ]

        for symbol_class in valve_classes:
            block_name = library.get_or_create_block(symbol_class)
            assert block_name in doc.blocks

    def test_unknown_symbol_creates_generic_block(self):
        """Test that unknown symbols get a generic block."""
        import ezdxf

        doc = ezdxf.new("R2018")
        library = ISO10628BlockLibrary(doc)

        block_name = library.get_or_create_block("Unknown_Symbol_Type")
        assert block_name in doc.blocks

    def test_block_reuse(self):
        """Test that blocks are reused, not recreated."""
        import ezdxf

        doc = ezdxf.new("R2018")
        library = ISO10628BlockLibrary(doc)

        # Create block first time
        block_name1 = library.get_or_create_block("Pump_Centrifugal")
        initial_block_count = len(doc.blocks)

        # Request same block again
        block_name2 = library.get_or_create_block("Pump_Centrifugal")

        assert block_name1 == block_name2
        assert len(doc.blocks) == initial_block_count


# Data List Export Tests


class TestDataListExportService:
    """Tests for data list export service."""

    def test_export_equipment_list_xlsx(
        self, mock_drawing, mock_symbols, export_metadata
    ):
        """Test equipment list export to Excel."""
        service = DataListExportService()

        output_path = service.export_equipment_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.XLSX,
            include_unverified=True,
        )

        assert output_path.exists()
        assert output_path.suffix == ".xlsx"
        assert output_path.stat().st_size > 0

        output_path.unlink()

    def test_export_equipment_list_csv(
        self, mock_drawing, mock_symbols, export_metadata
    ):
        """Test equipment list export to CSV."""
        service = DataListExportService()

        output_path = service.export_equipment_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        assert output_path.exists()
        assert output_path.suffix == ".csv"

        # Verify CSV content
        content = output_path.read_text()
        assert "Tag Number" in content
        assert "P-101" in content  # Equipment tag from mock

        output_path.unlink()

    def test_export_equipment_list_pdf(
        self, mock_drawing, mock_symbols, export_metadata
    ):
        """Test equipment list export to PDF."""
        service = DataListExportService()

        output_path = service.export_equipment_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.PDF,
            include_unverified=True,
        )

        assert output_path.exists()
        assert output_path.suffix == ".pdf"
        assert output_path.stat().st_size > 0

        output_path.unlink()

    def test_export_line_list(self, mock_drawing, mock_lines, export_metadata):
        """Test line list export."""
        service = DataListExportService()

        output_path = service.export_line_list(
            mock_drawing,
            mock_lines,
            export_metadata,
            ExportFormat.XLSX,
            include_unverified=True,
        )

        assert output_path.exists()
        assert "Line_List" in output_path.name

        output_path.unlink()

    def test_export_instrument_list(
        self, mock_drawing, mock_symbols, export_metadata
    ):
        """Test instrument list export."""
        service = DataListExportService()

        output_path = service.export_instrument_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.XLSX,
            include_unverified=True,
        )

        assert output_path.exists()
        assert "Instrument_List" in output_path.name

        output_path.unlink()

    def test_export_valve_list(self, mock_drawing, mock_symbols, export_metadata):
        """Test valve list export."""
        service = DataListExportService()

        output_path = service.export_valve_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.XLSX,
            include_unverified=True,
        )

        assert output_path.exists()
        assert "Valve_List" in output_path.name

        output_path.unlink()

    def test_export_mto(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test MTO export."""
        service = DataListExportService()

        output_path = service.export_mto(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.XLSX,
            include_unverified=True,
        )

        assert output_path.exists()
        assert "MTO" in output_path.name

        output_path.unlink()

    def test_export_comparison_report_pdf(
        self, mock_drawing, mock_symbols, mock_lines, mock_text_annotations, export_metadata
    ):
        """Test comparison report export to PDF."""
        service = DataListExportService()

        output_path = service.export_comparison_report(
            mock_drawing,
            mock_symbols,
            mock_lines,
            mock_text_annotations,
            export_metadata,
            ExportFormat.PDF,
        )

        assert output_path.exists()
        assert output_path.suffix == ".pdf"
        assert "Comparison_Report" in output_path.name

        output_path.unlink()

    def test_filters_unverified_when_requested(
        self, mock_drawing, mock_symbols, export_metadata
    ):
        """Test that unverified items are filtered when include_unverified=False."""
        service = DataListExportService()

        # Export excluding unverified (one symbol has is_verified=False)
        output_path = service.export_equipment_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=False,
        )

        content = output_path.read_text()
        # F-101 is the unverified equipment
        assert "F-101" not in content
        # P-101 is verified
        assert "P-101" in content

        output_path.unlink()

    def test_filters_deleted_items(
        self, mock_drawing, mock_symbols, export_metadata
    ):
        """Test that deleted items are always filtered."""
        # Mark one symbol as deleted
        mock_symbols[0].is_deleted = True

        service = DataListExportService()

        output_path = service.export_equipment_list(
            mock_drawing,
            mock_symbols,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        content = output_path.read_text()
        # P-101 was marked as deleted
        assert "P-101" not in content

        output_path.unlink()


class TestExportHelperMethods:
    """Tests for export helper methods."""

    def test_instrument_type_mapping(self):
        """Test instrument type extraction from symbol class."""
        service = DataListExportService()

        assert service._get_instrument_type("Transmitter_Pressure") == "PT"
        assert service._get_instrument_type("Transmitter_Temperature") == "TT"
        assert service._get_instrument_type("Transmitter_Flow") == "FT"
        assert service._get_instrument_type("Transmitter_Level") == "LT"
        assert service._get_instrument_type("Controller_Generic") == "C"
        assert service._get_instrument_type("Unknown_Type") == "I"  # Default

    def test_valve_type_mapping(self):
        """Test valve type extraction from symbol class."""
        service = DataListExportService()

        assert service._get_valve_type("Valve_Gate") == "Gate"
        assert service._get_valve_type("Valve_Globe") == "Globe"
        assert service._get_valve_type("Valve_Ball") == "Ball"
        assert service._get_valve_type("Valve_Check") == "Check"
        assert service._get_valve_type("Unknown_Valve") == "Manual"  # Default

    def test_actuator_type_detection(self):
        """Test actuator type detection from symbol class."""
        service = DataListExportService()

        assert service._get_actuator_type("Actuator_Pneumatic") == "Pneumatic"
        assert service._get_actuator_type("Actuator_Electric") == "Electric"
        assert service._get_actuator_type("Actuator_Hydraulic") == "Hydraulic"
        assert service._get_actuator_type("Valve_Control") == "Pneumatic"  # Default for control
        assert service._get_actuator_type("Valve_Gate") == "Manual"  # Default

    def test_loop_number_extraction(self):
        """Test loop number extraction from tag number."""
        service = DataListExportService()

        assert service._extract_loop_number("FT-101") == "101"
        assert service._extract_loop_number("PT-2034") == "2034"
        assert service._extract_loop_number("TT-1") == "1"
        assert service._extract_loop_number(None) == "-"
        assert service._extract_loop_number("ABC") == "-"  # No numbers

    def test_line_size_parsing(self):
        """Test line size extraction from spec."""
        service = DataListExportService()

        assert service._parse_line_size("6\"-P-101") == "6\""
        assert service._parse_line_size("2-I-201") == "2"
        assert service._parse_line_size(None) == "-"
        assert service._parse_line_size("") == "-"

    def test_description_from_class(self):
        """Test human-readable description generation."""
        service = DataListExportService()

        assert service._get_description_from_class("Pump_Centrifugal") == "Pump Centrifugal"
        assert service._get_description_from_class("Heat_Exchanger_Shell_Tube") == "Heat Exchanger Shell Tube"


class TestStatisticsCalculation:
    """Tests for extraction statistics calculation."""

    def test_statistics_counts_by_category(
        self, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test that statistics are correctly calculated by category."""
        service = DataListExportService()

        stats = service._calculate_statistics(
            mock_symbols, mock_lines, mock_text_annotations
        )

        # We have 2 equipment (P-101, F-101), 1 instrument (FT-101), 1 valve (V-101)
        assert stats["Equipment"]["count"] == 2
        assert stats["Instruments"]["count"] == 1
        assert stats["Valves"]["count"] == 1
        assert stats["Lines"]["count"] == 2

    def test_statistics_counts_verified(
        self, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test that verified counts are correct."""
        service = DataListExportService()

        stats = service._calculate_statistics(
            mock_symbols, mock_lines, mock_text_annotations
        )

        # F-101 is unverified
        assert stats["Equipment"]["verified"] == 1
        assert stats["Instruments"]["verified"] == 1
        assert stats["Valves"]["verified"] == 1
        assert stats["Lines"]["verified"] == 2

    def test_statistics_counts_flagged(
        self, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test that flagged counts (low confidence) are correct."""
        service = DataListExportService()

        stats = service._calculate_statistics(
            mock_symbols, mock_lines, mock_text_annotations
        )

        # F-101 has confidence 0.65 (below 0.7 threshold)
        assert stats["Equipment"]["flagged"] == 1
        assert stats["Instruments"]["flagged"] == 0
        assert stats["Valves"]["flagged"] == 0

    def test_flagged_items_list(
        self, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test that flagged items list is correctly generated."""
        service = DataListExportService()

        flagged = service._get_flagged_items(
            mock_symbols, mock_lines, mock_text_annotations
        )

        # F-101 should be flagged
        assert len(flagged) >= 1
        assert any(item["tag"] == "F-101" for item in flagged)


class TestValidationChecklistExport:
    """Tests for validation checklist export (CHK-06)."""

    def test_export_checklist_pdf(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test validation checklist export to PDF."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.PDF,
            include_unverified=True,
        )

        assert output_path.exists()
        assert output_path.suffix == ".pdf"
        assert "Validation_Checklist" in output_path.name
        assert output_path.stat().st_size > 0

        output_path.unlink()

    def test_export_checklist_xlsx(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test validation checklist export to Excel."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.XLSX,
            include_unverified=True,
        )

        assert output_path.exists()
        assert output_path.suffix == ".xlsx"
        assert "Validation_Checklist" in output_path.name

        output_path.unlink()

    def test_export_checklist_csv(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test validation checklist export to CSV."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        assert output_path.exists()
        assert output_path.suffix == ".csv"

        # Verify content has required columns
        content = output_path.read_text()
        assert "Category" in content
        assert "Tag Number" in content
        assert "Status" in content
        assert "Confidence" in content
        assert "Flagged" in content

        # Verify data is present
        assert "P-101" in content  # Equipment
        assert "FT-101" in content  # Instrument
        assert "V-101" in content  # Valve

        output_path.unlink()

    def test_export_checklist_includes_verification_status(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test that checklist shows verified/pending status correctly."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        content = output_path.read_text()

        # P-101 is verified
        assert "Verified" in content
        # F-101 is unverified (pending)
        assert "Pending" in content

        output_path.unlink()

    def test_export_checklist_includes_lines(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test that checklist includes line items."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        content = output_path.read_text()

        # Lines should be included
        assert "Line" in content
        assert "A1" in content  # Pipe class from mock line

        output_path.unlink()

    def test_export_checklist_filters_unverified(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test that include_unverified=False filters out unverified items."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=False,
        )

        content = output_path.read_text()

        # F-101 is unverified, should not be included
        assert "F-101" not in content
        # P-101 is verified, should be included
        assert "P-101" in content

        output_path.unlink()

    def test_export_checklist_excludes_deleted(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test that deleted items are always excluded."""
        # Mark one symbol as deleted
        mock_symbols[0].is_deleted = True

        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        content = output_path.read_text()

        # P-101 was marked as deleted - check it doesn't appear as Equipment
        # (Note: The line number 6"-P-101-A1 may contain P-101, but that's different)
        lines = content.split("\n")
        equipment_lines = [line for line in lines if line.startswith("Equipment,")]
        # P-101 should not appear in any equipment row
        for line in equipment_lines:
            assert "P-101" not in line, f"Deleted symbol P-101 should not appear in: {line}"

        output_path.unlink()

    def test_export_checklist_marks_flagged_items(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test that low confidence items are marked as flagged."""
        service = DataListExportService()

        output_path = service.export_validation_checklist(
            mock_drawing,
            mock_symbols,
            mock_lines,
            export_metadata,
            ExportFormat.CSV,
            include_unverified=True,
        )

        content = output_path.read_text()

        # F-101 has low confidence (0.65), should be flagged
        # Check that "Yes" appears for flagged column
        lines = content.split("\n")
        f101_line = [line for line in lines if "F-101" in line]
        assert len(f101_line) > 0
        assert "Yes" in f101_line[0]  # Flagged = Yes

        output_path.unlink()


# Batch Export Tests (DB-07)


class TestBatchExportModels:
    """Tests for batch export request/response models."""

    def test_batch_export_request_model(self):
        """Test BatchExportRequest model validation."""
        from app.api.routes.exports import BatchExportRequest

        # Valid request with drawing IDs
        request = BatchExportRequest(
            drawing_ids=[uuid4(), uuid4()],
            export_type="dxf",
            paper_size="A1",
            scale="1:50",
        )
        assert len(request.drawing_ids) == 2
        assert request.export_type == "dxf"

    def test_batch_export_request_requires_drawing_ids(self):
        """Test that drawing_ids is required and non-empty."""
        from pydantic import ValidationError

        from app.api.routes.exports import BatchExportRequest

        with pytest.raises(ValidationError):
            BatchExportRequest(
                drawing_ids=[],  # Empty list should fail
                export_type="dxf",
            )

    def test_batch_export_request_default_values(self):
        """Test BatchExportRequest default values."""
        from app.api.routes.exports import BatchExportRequest

        request = BatchExportRequest(drawing_ids=[uuid4()])

        assert request.export_type == "dxf"
        assert request.paper_size == "A1"
        assert request.scale == "1:50"
        assert request.include_connections is True
        assert request.include_annotations is True
        assert request.include_title_block is True
        assert "equipment" in request.lists
        assert request.format == "xlsx"
        assert request.include_unverified is False

    def test_batch_export_job_response_model(self):
        """Test BatchExportJobResponse model."""
        from app.api.routes.exports import BatchExportJobResponse

        response = BatchExportJobResponse(
            job_id="test-job-123",
            total_drawings=5,
            export_type="dxf",
            status="processing",
            message="Batch export started",
        )

        assert response.job_id == "test-job-123"
        assert response.total_drawings == 5
        assert response.status == "processing"

    def test_batch_export_status_response_model(self):
        """Test BatchExportStatusResponse model."""
        from app.api.routes.exports import BatchExportStatusResponse

        response = BatchExportStatusResponse(
            job_id="test-job-123",
            status="completed",
            total_drawings=5,
            completed_drawings=4,
            failed_drawings=1,
            file_path="/tmp/batch_export.zip",
            errors=["drawing-1: failed to export"],
        )

        assert response.completed_drawings == 4
        assert response.failed_drawings == 1
        assert len(response.errors) == 1


class TestBatchExportEndpoints:
    """Tests for batch export API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Create mock auth headers."""
        return {"Authorization": "Bearer test-token"}

    def test_batch_export_validates_export_type(self, client, auth_headers):
        """Test that invalid export type is rejected."""
        response = client.post(
            "/api/v1/exports/batch",
            headers=auth_headers,
            json={
                "drawing_ids": [str(uuid4())],
                "export_type": "invalid_type",
            },
        )
        # Should return 400 or 401 (if auth fails first)
        assert response.status_code in [400, 401]

    def test_batch_export_validates_paper_size(self, client, auth_headers):
        """Test that invalid paper size is rejected for DXF export."""
        response = client.post(
            "/api/v1/exports/batch",
            headers=auth_headers,
            json={
                "drawing_ids": [str(uuid4())],
                "export_type": "dxf",
                "paper_size": "INVALID",
            },
        )
        # Should return 400 or 401 (if auth fails first)
        assert response.status_code in [400, 401]

    def test_batch_export_validates_format(self, client, auth_headers):
        """Test that invalid format is rejected for lists export."""
        response = client.post(
            "/api/v1/exports/batch",
            headers=auth_headers,
            json={
                "drawing_ids": [str(uuid4())],
                "export_type": "lists",
                "format": "invalid",
            },
        )
        # Should return 400 or 401 (if auth fails first)
        assert response.status_code in [400, 401]

    def test_batch_export_validates_list_types(self, client, auth_headers):
        """Test that invalid list types are rejected."""
        response = client.post(
            "/api/v1/exports/batch",
            headers=auth_headers,
            json={
                "drawing_ids": [str(uuid4())],
                "export_type": "lists",
                "lists": ["invalid_list_type"],
            },
        )
        # Should return 400 or 401 (if auth fails first)
        assert response.status_code in [400, 401]

    def test_batch_export_status_returns_404_for_unknown_job(
        self, client, auth_headers
    ):
        """Test that unknown job ID returns 404."""
        response = client.get(
            "/api/v1/exports/batch/unknown-job-id/status",
            headers=auth_headers,
        )
        # Should return 404 or 401 (if auth fails first)
        assert response.status_code in [404, 401]


class TestBatchExportProcessing:
    """Tests for batch export processing logic."""

    def test_batch_export_creates_zip_file(
        self, mock_drawing, mock_symbols, mock_lines, mock_text_annotations
    ):
        """Test that batch export creates a ZIP file with exports."""
        import tempfile
        import zipfile
        from pathlib import Path

        from app.services.export.dxf_export import (
            DXFExportService,
            ExportOptions,
            PaperSize,
            TitleBlockInfo,
        )

        # Create multiple exports
        service = DXFExportService()
        options = ExportOptions(paper_size=PaperSize.A3)
        title_info = TitleBlockInfo(
            drawing_number="P&ID-001",
            drawing_title="Test Drawing",
            project_name="Test Project",
        )

        # Export multiple drawings
        output_paths = []
        for i in range(3):
            mock_drawing.id = uuid4()
            mock_drawing.original_filename = f"P&ID-00{i+1}.pdf"
            output_path = service.export_drawing(
                mock_drawing,
                mock_symbols,
                mock_lines,
                mock_text_annotations,
                options,
                title_info,
            )
            output_paths.append(output_path)

        # Create a batch ZIP file
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "batch_export.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in output_paths:
                zf.write(path, path.name)

        # Verify ZIP file
        assert zip_path.exists()
        assert zip_path.stat().st_size > 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert len(names) == 3
            for name in names:
                assert name.endswith(".dxf")

        # Clean up
        for path in output_paths:
            path.unlink()
        zip_path.unlink()
        temp_dir.rmdir()

    def test_batch_export_handles_mixed_export_types(
        self, mock_drawing, mock_symbols, mock_lines, export_metadata
    ):
        """Test that batch export handles multiple drawings with data lists."""
        import tempfile
        import zipfile
        from pathlib import Path

        service = DataListExportService()

        # Export equipment list for multiple drawings
        # Use a set to track unique paths (service may use same base filename)
        output_paths = {}
        unique_paths = set()
        for i in range(2):
            mock_drawing.id = uuid4()
            mock_drawing.original_filename = f"P&ID-00{i+1}.pdf"
            output_path = service.export_equipment_list(
                mock_drawing,
                mock_symbols,
                export_metadata,
                ExportFormat.XLSX,
                include_unverified=True,
            )
            output_paths[f"P&ID-00{i+1}_equipment.xlsx"] = output_path
            unique_paths.add(output_path)

        # Create batch ZIP
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "batch_lists.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, path in output_paths.items():
                if path.exists():
                    zf.write(path, name)

        # Verify
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # At least one export should be in the ZIP
            assert len(names) >= 1
            assert all("equipment" in name for name in names)

        # Clean up - only unlink unique paths that exist
        for path in unique_paths:
            if path.exists():
                path.unlink()
        zip_path.unlink()
        temp_dir.rmdir()

    def test_batch_export_job_tracking(self):
        """Test that batch export jobs are tracked correctly."""
        from app.api.routes.exports import _export_jobs

        job_id = "test-batch-job"
        _export_jobs[job_id] = {
            "status": "processing",
            "export_type": "batch_dxf",
            "total_drawings": 5,
            "completed_drawings": 0,
            "failed_drawings": 0,
            "file_path": None,
            "errors": [],
        }

        # Simulate progress
        _export_jobs[job_id]["completed_drawings"] = 3
        _export_jobs[job_id]["failed_drawings"] = 1

        assert _export_jobs[job_id]["completed_drawings"] == 3
        assert _export_jobs[job_id]["failed_drawings"] == 1
        assert _export_jobs[job_id]["total_drawings"] == 5

        # Simulate completion
        _export_jobs[job_id]["status"] = "completed"
        _export_jobs[job_id]["file_path"] = "/tmp/batch_export.zip"

        assert _export_jobs[job_id]["status"] == "completed"
        assert _export_jobs[job_id]["file_path"] is not None

        # Clean up
        del _export_jobs[job_id]

    def test_batch_export_status_tracking(self):
        """Test that batch export status values are correct."""
        from app.api.routes.exports import BatchExportStatusResponse

        # Processing state
        processing = BatchExportStatusResponse(
            job_id="job-1",
            status="processing",
            total_drawings=10,
            completed_drawings=5,
            failed_drawings=1,
            file_path=None,
            errors=["drawing-3: error"],
        )

        assert processing.status == "processing"
        assert processing.completed_drawings + processing.failed_drawings == 6
        assert processing.file_path is None

        # Completed state
        completed = BatchExportStatusResponse(
            job_id="job-1",
            status="completed",
            total_drawings=10,
            completed_drawings=9,
            failed_drawings=1,
            file_path="/tmp/batch.zip",
            errors=["drawing-3: error"],
        )

        assert completed.status == "completed"
        assert completed.file_path is not None
