# Spec: AI OCR Text Extraction

## Job to be Done
Extract text from P&IDs including equipment tags, instrument tags, line numbers, and annotations using Tesseract OCR.

## Functional Requirements

### Text Extraction
| ID | Requirement | Priority |
|----|-------------|----------|
| OCR-01 | Extract equipment tags (e.g., P-101, V-201, E-301) | Must-Have |
| OCR-02 | Extract instrument tags (e.g., FT-101, PIC-201, LT-301) | Must-Have |
| OCR-03 | Extract line numbers (e.g., 6"-P-101-A1) | Must-Have |
| OCR-04 | Extract valve tags | Must-Have |
| OCR-05 | Extract text labels and descriptions | Must-Have |
| OCR-06 | Extract title block information | Must-Have |
| OCR-07 | Handle rotated text (0°, 90°, 180°, 270°) | Must-Have |
| OCR-08 | Support common engineering fonts (Arial, ISOCPEUR, RomanS) | Must-Have |
| OCR-09 | Handle low-quality scanned documents | Must-Have |
| OCR-10 | Post-process with tag format validation (regex) | Must-Have |

### Performance Requirements
| ID | Requirement | Target |
|----|-------------|--------|
| PERF-01 | OCR accuracy (vector PDFs) | >95% |
| PERF-02 | OCR accuracy (scanned PDFs) | >85% |
| PERF-03 | Processing time per page | <30 seconds |

## Tag Format Patterns

### Equipment Tags
```regex
Pattern: ^[A-Z]{1,2}-\d{3}[A-Z]?$
Examples: P-101, V-201A, E-301, T-401, C-501
```

### Instrument Tags
```regex
Pattern: ^[A-Z]{2,4}-\d{3}[A-Z]?$
Examples: FT-101, PIC-201, LT-301, TT-401, LSHL-101
```

### Line Numbers
```regex
Pattern: ^\d{1,2}"-[A-Z]-\d{3}-[A-Z]\d$
Examples: 6"-P-101-A1, 2"-U-201-B2, 4"-I-301-C1
```

### Valve Tags
```regex
Pattern: ^(XV|FCV|PCV|TCV|LCV|HV|PSV|RV)-\d{3}[A-Z]?$
Examples: XV-101, FCV-201, PSV-301A
```

## Data Model

```typescript
interface ExtractedText {
  id: string;
  drawingId: string;
  textContent: string;
  textType: TextType;
  bbox: BoundingBox;
  rotation: 0 | 90 | 180 | 270;
  confidence: number;
  linkedSymbolId?: string;       // Associated symbol
  isVerified: boolean;
  createdAt: Date;
}

type TextType = 
  | 'equipment_tag'
  | 'instrument_tag'
  | 'line_number'
  | 'valve_tag'
  | 'label'
  | 'note'
  | 'title_block'
  | 'unknown';

interface TitleBlock {
  drawingNumber?: string;
  revision?: string;
  title?: string;
  projectName?: string;
  date?: string;
  scale?: string;
  drawnBy?: string;
  approvedBy?: string;
}
```

## OCR Pipeline

```
Input: Drawing Image
         │
         ▼
┌────────────────────┐
│ Pre-processing     │
│ - Deskew           │
│ - Denoise          │
│ - Binarization     │
│ - Contrast enhance │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Text Detection     │
│ - Find text regions│
│ - Detect rotation  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Tesseract OCR      │
│ - Per region       │
│ - Handle rotation  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Post-processing    │
│ - Spell check      │
│ - Tag validation   │
│ - Type classify    │
└─────────┬──────────┘
          │
          ▼
Output: List of (bbox, text, type, confidence)
```

## Tesseract Configuration

### Config File (tesseract.config)
```
tessedit_char_whitelist 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-"/.'()
tessedit_pageseg_mode 6
preserve_interword_spaces 1
```

### Language Training
- Base: English (eng)
- Custom training for engineering fonts
- Add engineering-specific dictionary

### Rotation Handling
```python
def extract_rotated_text(image, region, rotation):
    # Rotate region to horizontal
    rotated = rotate_image(image, -rotation)
    # Run OCR
    text = pytesseract.image_to_string(rotated, config=config)
    return text, rotation
```

## Tag-Symbol Association Algorithm

```python
def associate_tags_to_symbols(texts, symbols):
    """
    Associate extracted text tags with detected symbols
    using proximity-based matching.
    """
    associations = []
    
    for text in texts:
        if text.text_type in ['equipment_tag', 'instrument_tag', 'valve_tag']:
            # Find nearest symbol of matching category
            nearest = find_nearest_symbol(
                text.bbox,
                symbols,
                category=get_category_for_tag_type(text.text_type),
                max_distance=100  # pixels
            )
            if nearest:
                associations.append((text.id, nearest.id))
    
    return associations
```

## API Endpoints

### Get Extracted Text
```
GET /api/v1/drawings/{id}/text
Query: ?type=equipment_tag&minConfidence=0.8

Response: 200 OK
{
  "items": [
    {
      "id": "uuid",
      "textContent": "P-101",
      "textType": "equipment_tag",
      "bbox": {"x": 250, "y": 390, "width": 40, "height": 12},
      "rotation": 0,
      "confidence": 0.96,
      "linkedSymbolId": "symbol-uuid"
    }
  ],
  "total": 47
}
```

### Get Title Block
```
GET /api/v1/drawings/{id}/title-block

Response: 200 OK
{
  "drawingNumber": "P&ID-001",
  "revision": "A",
  "title": "Process Area 100 - Feed System",
  "projectName": "WtE Plant Alpha",
  "date": "2025-12-15",
  "drawnBy": "JMS",
  "approvedBy": "KLR"
}
```

## Acceptance Criteria

1. Extracts >95% of text from vector PDFs correctly
2. Extracts >85% of text from scanned PDFs correctly
3. Correctly identifies text rotation
4. Validates tag formats using regex patterns
5. Associates tags with corresponding symbols
6. Extracts complete title block information
7. Handles common engineering fonts
8. Flags low-confidence extractions for review

## Pre-processing for Scanned Images

```python
def preprocess_scanned_image(image):
    # 1. Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Deskew
    angle = detect_skew_angle(gray)
    deskewed = rotate_image(gray, -angle)
    
    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(deskewed)
    
    # 4. Binarization (Otsu's method)
    _, binary = cv2.threshold(
        denoised, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    
    # 5. Morphological cleanup
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return cleaned
```

## Error Handling

| Error | Action |
|-------|--------|
| Unreadable text region | Skip, flag for manual review |
| Invalid tag format | Extract anyway, mark as 'unknown' type |
| OCR timeout | Retry with simpler config |
| Memory exhaustion | Process in smaller chunks |
