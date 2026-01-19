"""Tests for the ML pipeline components."""


from app.ml.ocr_pipeline import OCRPipeline, TagAssociator, TagType


class TestTagClassification:
    """Tests for tag classification logic."""

    def test_classify_equipment_tag(self):
        """Test equipment tag classification."""
        pipeline = OCRPipeline()

        # Valid equipment tags
        assert pipeline._classify_tag("V-101") == TagType.EQUIPMENT
        assert pipeline._classify_tag("P-201") == TagType.EQUIPMENT
        assert pipeline._classify_tag("E-301A") == TagType.EQUIPMENT
        assert pipeline._classify_tag("T-1001") == TagType.EQUIPMENT

    def test_classify_instrument_tag(self):
        """Test instrument tag classification."""
        pipeline = OCRPipeline()

        # Valid instrument tags (ISA format)
        assert pipeline._classify_tag("PT-101") == TagType.INSTRUMENT
        assert pipeline._classify_tag("FT-201") == TagType.INSTRUMENT
        assert pipeline._classify_tag("LIC-301") == TagType.INSTRUMENT
        assert pipeline._classify_tag("TI-401") == TagType.INSTRUMENT

    def test_classify_valve_tag(self):
        """Test valve tag classification."""
        pipeline = OCRPipeline()

        # Valid valve tags
        assert pipeline._classify_tag("XV-101") == TagType.VALVE
        assert pipeline._classify_tag("HV-201") == TagType.VALVE
        assert pipeline._classify_tag("PV-301A") == TagType.VALVE

    def test_classify_line_tag(self):
        """Test line tag classification."""
        pipeline = OCRPipeline()

        # Valid line tags
        assert pipeline._classify_tag('6"-P-101-A1') == TagType.LINE
        assert pipeline._classify_tag("2\"-W-201-B2") == TagType.LINE

    def test_classify_unknown(self):
        """Test unknown tag classification."""
        pipeline = OCRPipeline()

        # Invalid/unknown tags
        assert pipeline._classify_tag("Hello") == TagType.UNKNOWN
        assert pipeline._classify_tag("12345") == TagType.UNKNOWN
        assert pipeline._classify_tag("ABC") == TagType.UNKNOWN


class TestTagAssociator:
    """Tests for tag-symbol association."""

    def test_associate_nearby_symbol(self):
        """Test associating a tag with a nearby symbol."""
        from app.ml.ocr_pipeline import ExtractedText

        associator = TagAssociator(max_distance=100)

        texts = [
            ExtractedText(
                text="V-101",
                confidence=0.95,
                bbox=(100, 100, 50, 20),
                rotation=0,
                tag_type=TagType.EQUIPMENT,
                normalized_tag="V-101",
            )
        ]

        symbols = [
            {
                "bbox": (110, 130, 60, 80),  # Nearby
                "class_id": 1,
                "class_name": "vessel_vertical",
            },
            {
                "bbox": (500, 500, 60, 80),  # Far away
                "class_id": 2,
                "class_name": "pump_centrifugal",
            },
        ]

        associations = associator.associate(texts, symbols)

        assert len(associations) == 1
        assert associations[0]["symbol"]["class_name"] == "vessel_vertical"

    def test_no_association_when_too_far(self):
        """Test that far symbols are not associated."""
        from app.ml.ocr_pipeline import ExtractedText

        associator = TagAssociator(max_distance=50)

        texts = [
            ExtractedText(
                text="P-101",
                confidence=0.9,
                bbox=(100, 100, 50, 20),
                rotation=0,
                tag_type=TagType.EQUIPMENT,
                normalized_tag="P-101",
            )
        ]

        symbols = [
            {
                "bbox": (500, 500, 60, 80),  # Far away
                "class_id": 5,
                "class_name": "pump_centrifugal",
            },
        ]

        associations = associator.associate(texts, symbols)
        assert len(associations) == 0

    def test_ignore_unknown_tags(self):
        """Test that unknown tags are not associated."""
        from app.ml.ocr_pipeline import ExtractedText

        associator = TagAssociator(max_distance=100)

        texts = [
            ExtractedText(
                text="Hello",
                confidence=0.9,
                bbox=(100, 100, 50, 20),
                rotation=0,
                tag_type=TagType.UNKNOWN,
                normalized_tag=None,
            )
        ]

        symbols = [
            {
                "bbox": (110, 130, 60, 80),
                "class_id": 1,
                "class_name": "vessel_vertical",
            },
        ]

        associations = associator.associate(texts, symbols)
        assert len(associations) == 0


class TestInferenceService:
    """Tests for the inference service."""

    def test_service_initialization(self):
        """Test that inference service initializes without model."""
        from app.ml.inference import InferenceService

        service = InferenceService(model_path=None)
        assert service.symbol_model is None
        assert service.ocr_pipeline is not None

    def test_class_names_loaded(self):
        """Test that class names are loaded."""
        from app.ml.inference import InferenceService

        service = InferenceService()
        assert len(service.class_names) > 1
        assert service.class_names[0] == "__background__"
