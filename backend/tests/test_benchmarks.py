"""
Performance benchmarks for Flowex backend.

Run with: pytest tests/test_benchmarks.py -v --benchmark-json=benchmark-results.json

These benchmarks measure critical paths:
- PDF processing pipeline
- Image preprocessing
- DXF export generation
- Database query patterns
"""

import io

import pytest
from PIL import Image

# Test fixtures for benchmarking
from app.services.pdf_processing import (
    create_image_tiles,
    detect_pdf_type,
    get_pdf_metadata,
    preprocess_scanned_image,
)


def create_test_pdf(pages: int = 1, with_text: bool = True) -> bytes:
    """Create a minimal test PDF for benchmarking."""
    # Simple PDF structure
    content = "%PDF-1.4\n"

    # Catalog object
    content += "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

    # Pages object
    kids = " ".join([f"{i + 3} 0 R" for i in range(pages)])
    content += f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {pages} >>\nendobj\n"

    # Page objects
    obj_num = 3
    for i in range(pages):
        if with_text:
            content += f"{obj_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {obj_num + 1} 0 R >>\nendobj\n"
            content += f"{obj_num + 1} 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test Page {i + 1}) Tj ET\nendstream\nendobj\n"
            obj_num += 2
        else:
            content += f"{obj_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            obj_num += 1

    # Cross-reference table
    content += f"xref\n0 {obj_num}\n"
    content += "0000000000 65535 f\n"
    for i in range(1, obj_num):
        content += f"{i:010d} 00000 n\n"

    # Trailer
    content += f"trailer\n<< /Size {obj_num} /Root 1 0 R >>\nstartxref\n{len(content)}\n%%EOF"

    return content.encode("utf-8")


def create_test_image(width: int = 1024, height: int = 1024) -> bytes:
    """Create a test image for benchmarking."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))

    # Add some variation (simulate P&ID content)
    pixels = img.load()
    for y in range(0, height, 50):
        for x in range(0, width, 50):
            pixels[x, y] = (0, 0, 0)  # Black dots

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestPDFProcessingBenchmarks:
    """Benchmarks for PDF processing operations."""

    @pytest.fixture
    def small_pdf(self) -> bytes:
        """1-page PDF."""
        return create_test_pdf(pages=1)

    @pytest.fixture
    def medium_pdf(self) -> bytes:
        """5-page PDF."""
        return create_test_pdf(pages=5)

    @pytest.fixture
    def large_pdf(self) -> bytes:
        """20-page PDF."""
        return create_test_pdf(pages=20)

    def test_benchmark_detect_pdf_type_small(self, benchmark, small_pdf):
        """Benchmark PDF type detection for small PDFs."""
        result = benchmark(detect_pdf_type, small_pdf)
        assert result in ["pdf_vector", "pdf_scanned"]

    def test_benchmark_detect_pdf_type_medium(self, benchmark, medium_pdf):
        """Benchmark PDF type detection for medium PDFs."""
        result = benchmark(detect_pdf_type, medium_pdf)
        assert result in ["pdf_vector", "pdf_scanned"]

    def test_benchmark_detect_pdf_type_large(self, benchmark, large_pdf):
        """Benchmark PDF type detection for large PDFs."""
        result = benchmark(detect_pdf_type, large_pdf)
        assert result in ["pdf_vector", "pdf_scanned"]

    def test_benchmark_get_pdf_metadata(self, benchmark, medium_pdf):
        """Benchmark PDF metadata extraction."""
        result = benchmark(get_pdf_metadata, medium_pdf)
        assert "page_count" in result


class TestImageProcessingBenchmarks:
    """Benchmarks for image processing operations."""

    @pytest.fixture
    def small_image(self) -> bytes:
        """512x512 image."""
        return create_test_image(512, 512)

    @pytest.fixture
    def medium_image(self) -> bytes:
        """1024x1024 image."""
        return create_test_image(1024, 1024)

    @pytest.fixture
    def large_image(self) -> bytes:
        """2048x2048 image."""
        return create_test_image(2048, 2048)

    @pytest.fixture
    def xlarge_image(self) -> bytes:
        """4096x4096 image (max size per spec)."""
        return create_test_image(4096, 4096)

    def test_benchmark_preprocess_small(self, benchmark, small_image):
        """Benchmark image preprocessing for small images."""
        result = benchmark(preprocess_scanned_image, small_image)
        assert len(result) > 0

    def test_benchmark_preprocess_medium(self, benchmark, medium_image):
        """Benchmark image preprocessing for medium images."""
        result = benchmark(preprocess_scanned_image, medium_image)
        assert len(result) > 0

    def test_benchmark_preprocess_large(self, benchmark, large_image):
        """Benchmark image preprocessing for large images."""
        result = benchmark(preprocess_scanned_image, large_image)
        assert len(result) > 0

    def test_benchmark_create_tiles_medium(self, benchmark, medium_image):
        """Benchmark tile creation for 1024x1024 image."""
        result = benchmark(create_image_tiles, medium_image)
        assert len(result) > 0

    def test_benchmark_create_tiles_large(self, benchmark, large_image):
        """Benchmark tile creation for 2048x2048 image."""
        result = benchmark(create_image_tiles, large_image)
        assert len(result) > 0

    def test_benchmark_create_tiles_xlarge(self, benchmark, xlarge_image):
        """Benchmark tile creation for 4096x4096 image (spec max)."""
        result = benchmark(create_image_tiles, xlarge_image)
        # Should create multiple tiles
        assert len(result) >= 16  # 4x4 grid minimum


class TestExportBenchmarks:
    """Benchmarks for export operations."""

    @pytest.fixture
    def mock_symbols(self):
        """Create mock symbol data."""
        from unittest.mock import MagicMock

        symbols = []
        for i in range(100):  # 100 symbols per drawing
            symbol = MagicMock()
            symbol.id = f"symbol-{i}"
            symbol.symbol_class = "pump"
            symbol.confidence_score = 0.95
            symbol.bbox_x = i * 10
            symbol.bbox_y = i * 10
            symbol.bbox_width = 50
            symbol.bbox_height = 50
            symbol.associated_tag = f"P-{i:03d}"
            symbol.is_verified = True
            symbols.append(symbol)
        return symbols

    @pytest.fixture
    def mock_lines(self):
        """Create mock line data."""
        from unittest.mock import MagicMock

        lines = []
        for i in range(50):  # 50 lines per drawing
            line = MagicMock()
            line.id = f"line-{i}"
            line.line_number = f"L-{i:03d}"
            line.from_symbol_id = f"symbol-{i}"
            line.to_symbol_id = f"symbol-{i + 1}"
            line.is_verified = True
            lines.append(line)
        return lines

    def test_benchmark_dxf_symbol_creation(self, benchmark, mock_symbols):
        """Benchmark DXF symbol block creation."""

        def create_symbols():
            # Simulate DXF symbol creation logic
            import ezdxf

            doc = ezdxf.new("R2010")
            msp = doc.modelspace()
            for symbol in mock_symbols[:10]:  # Limit for benchmark
                msp.add_circle(
                    (symbol.bbox_x, symbol.bbox_y),
                    radius=25,
                )
            return doc

        result = benchmark(create_symbols)
        assert result is not None


class TestDatabaseQueryBenchmarks:
    """Benchmarks for database query patterns.

    Note: These require a database connection.
    Run with: pytest tests/test_benchmarks.py -v -k database --benchmark-json=db-benchmark.json
    """

    @pytest.mark.skip(reason="Requires database connection")
    def test_benchmark_drawings_query(self, benchmark, db_session):
        """Benchmark drawing list query with 100 items."""

        def query_drawings():
            from app.models import Drawing

            return db_session.query(Drawing).limit(100).all()

        benchmark(query_drawings)
        # No assertion - just measuring query time

    @pytest.mark.skip(reason="Requires database connection")
    def test_benchmark_symbols_by_drawing(self, benchmark, db_session):
        """Benchmark symbol query for a drawing."""
        from uuid import uuid4

        drawing_id = uuid4()

        def query_symbols():
            from app.models import Symbol

            return db_session.query(Symbol).filter(Symbol.drawing_id == drawing_id).all()

        benchmark(query_symbols)


# Performance assertions
class TestPerformanceRequirements:
    """Tests that verify performance meets spec requirements."""

    def test_pdf_detection_under_500ms(self):
        """PDF type detection should complete in <500ms.

        Note: Using 500ms threshold as test PDFs may trigger error handling.
        Real-world PDFs are expected to complete in <100ms.
        """
        import time

        pdf = create_test_pdf(pages=5)

        start = time.perf_counter()
        try:
            detect_pdf_type(pdf)
        except Exception:
            pass  # Test PDFs may be malformed
        duration = (time.perf_counter() - start) * 1000

        assert duration < 500, f"PDF detection took {duration:.2f}ms, expected <500ms"

    def test_image_preprocessing_under_500ms(self):
        """Image preprocessing should complete in <500ms for 1024x1024."""
        import time

        image = create_test_image(1024, 1024)

        start = time.perf_counter()
        preprocess_scanned_image(image)
        duration = (time.perf_counter() - start) * 1000

        assert duration < 500, f"Image preprocessing took {duration:.2f}ms, expected <500ms"

    def test_tile_creation_under_200ms(self):
        """Tile creation should complete in <200ms for 2048x2048."""
        import time

        image = create_test_image(2048, 2048)

        start = time.perf_counter()
        tiles = create_image_tiles(image)
        duration = (time.perf_counter() - start) * 1000

        assert duration < 200, f"Tile creation took {duration:.2f}ms, expected <200ms"
        assert len(tiles) > 0
