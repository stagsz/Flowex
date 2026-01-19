import io

import pytest
from PIL import Image

from app.services.pdf_processing import (
    create_image_tiles,
    preprocess_scanned_image,
)


class TestImageTiling:
    """Tests for image tiling functionality."""

    def test_create_tiles_small_image(self):
        """Test tiling on an image smaller than tile size."""
        # Create a small test image
        img = Image.new("RGB", (500, 500), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        tiles = create_image_tiles(image_bytes, tile_size=1024, overlap=64)

        # Small image should result in a single tile
        assert len(tiles) == 1
        assert tiles[0]["x"] == 0
        assert tiles[0]["y"] == 0
        assert tiles[0]["width"] == 500
        assert tiles[0]["height"] == 500

    def test_create_tiles_large_image(self):
        """Test tiling on an image larger than tile size."""
        # Create a large test image
        img = Image.new("RGB", (2000, 2000), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        tiles = create_image_tiles(image_bytes, tile_size=1024, overlap=64)

        # Should create multiple tiles
        assert len(tiles) > 1

        # Verify tiles have correct structure
        for tile in tiles:
            assert "bytes" in tile
            assert "x" in tile
            assert "y" in tile
            assert "width" in tile
            assert "height" in tile
            assert tile["width"] <= 1024
            assert tile["height"] <= 1024

    def test_tiles_have_overlap(self):
        """Test that tiles overlap correctly."""
        img = Image.new("RGB", (2000, 1000), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        tile_size = 1024
        overlap = 64
        tiles = create_image_tiles(image_bytes, tile_size=tile_size, overlap=overlap)

        # Find tiles in the same row
        row_tiles = [t for t in tiles if t["y"] == 0]
        assert len(row_tiles) >= 2

        # Second tile should start before first tile ends (overlap)
        if len(row_tiles) >= 2:
            first_tile_end = row_tiles[0]["x"] + row_tiles[0]["width"]
            second_tile_start = row_tiles[1]["x"]
            # The overlap should be tile_size - step, where step = tile_size - overlap
            expected_start = tile_size - overlap
            assert second_tile_start == expected_start


class TestImagePreprocessing:
    """Tests for image preprocessing functionality."""

    def test_preprocess_converts_to_grayscale(self):
        """Test that preprocessing converts image to grayscale."""
        # Create a color test image
        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result_bytes = preprocess_scanned_image(image_bytes)

        # Load result and check mode
        result_img = Image.open(io.BytesIO(result_bytes))
        assert result_img.mode == "L"  # Grayscale

    def test_preprocess_maintains_dimensions(self):
        """Test that preprocessing maintains image dimensions."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result_bytes = preprocess_scanned_image(image_bytes)

        result_img = Image.open(io.BytesIO(result_bytes))
        assert result_img.size == (800, 600)

    def test_preprocess_returns_valid_png(self):
        """Test that preprocessing returns valid PNG bytes."""
        img = Image.new("RGB", (100, 100), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result_bytes = preprocess_scanned_image(image_bytes)

        # Should be able to open as PNG
        result_img = Image.open(io.BytesIO(result_bytes))
        assert result_img.format == "PNG"
