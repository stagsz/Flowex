"""Tests for export functionality."""

import tempfile
from pathlib import Path
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
    drawing.status = DrawingStatus.COMPLETE
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
