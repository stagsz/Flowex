# Spec: AutoCAD Export

## Job to be Done
Export validated P&ID as intelligent, editable AutoCAD drawings (DWG/DXF) with proper layers and symbol blocks.

## Functional Requirements

### Export Formats
| ID | Requirement | Priority |
|----|-------------|----------|
| EXP-01 | Export as DWG format (AutoCAD 2018+ compatible) | Must-Have |
| EXP-02 | Export as DXF format (universal exchange) | Must-Have |
| EXP-03 | Proper layer organization per element type | Must-Have |
| EXP-04 | Symbol blocks with editable attributes | Must-Have |
| EXP-05 | Correct line weights and styles | Must-Have |
| EXP-06 | Preserve original scale and dimensions | Must-Have |
| EXP-07 | Include title block | Must-Have |
| EXP-08 | Support A0-A4 paper sizes | Must-Have |
| EXP-09 | Configurable export settings | Should-Have |

### Layer Structure
```
Layer Name              Color       Line Type       Usage
───────────────────────────────────────────────────────────────
EQUIPMENT              Cyan (4)    Continuous      Equipment symbols
INSTRUMENTS            Magenta (6) Continuous      Instrument symbols
VALVES                 Green (3)   Continuous      Valve symbols
PIPING-PROCESS         White (7)   Continuous      Process piping
PIPING-UTILITY         Yellow (2)  Dashed          Utility piping
PIPING-INSTRUMENT      Blue (5)    Dashed2         Instrument lines
TEXT-TAGS              White (7)   Continuous      Equipment/tag labels
TEXT-LABELS            White (7)   Continuous      General labels
TEXT-NOTES             Gray (8)    Continuous      Annotations
TITLE-BLOCK            White (7)   Continuous      Title block
BORDER                 White (7)   Continuous      Drawing border
```

### Symbol Blocks
```
Block Structure:
├── Block Name: PUMP_CENTRIFUGAL
│   ├── Geometry (lines, arcs, etc.)
│   ├── Attributes:
│   │   ├── TAG: "P-101"
│   │   ├── DESCRIPTION: "Feed Pump"
│   │   ├── TYPE: "Centrifugal"
│   │   └── SPEC: "API 610"
│   └── Connection Points (defined as attributes)

Example Block Definition:
{
  "name": "PUMP_CENTRIFUGAL",
  "basePoint": [0, 0],
  "geometry": [
    {"type": "circle", "center": [0, 0], "radius": 20},
    {"type": "line", "start": [-20, 0], "end": [20, 0]},
    {"type": "arc", "center": [25, 0], "radius": 5, "startAngle": 90, "endAngle": 270}
  ],
  "attributes": [
    {"tag": "TAG", "prompt": "Tag Number", "default": "", "position": [0, -30]},
    {"tag": "DESC", "prompt": "Description", "default": "", "position": [0, -40]}
  ],
  "connectionPoints": [
    {"name": "INLET", "position": [-20, 0]},
    {"name": "OUTLET", "position": [30, 0]}
  ]
}
```

## Export Pipeline

```
Validated Drawing Data
         │
         ▼
┌────────────────────────┐
│ 1. Initialize Drawing  │
│    - Set units (mm)    │
│    - Set limits        │
│    - Create layers     │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 2. Create Symbol Blocks│
│    - Load ISO 10628    │
│    - Add custom blocks │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 3. Place Symbols       │
│    - Insert blocks     │
│    - Set attributes    │
│    - Apply rotation    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 4. Draw Lines          │
│    - Process lines     │
│    - Utility lines     │
│    - Instrument lines  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 5. Add Text            │
│    - Tags              │
│    - Labels            │
│    - Annotations       │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 6. Title Block         │
│    - Drawing info      │
│    - Revision          │
│    - Border            │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 7. Save File           │
│    - DWG or DXF        │
│    - Compress          │
└───────────┬────────────┘
            │
            ▼
Output: .dwg or .dxf file
```

## Technical Implementation

### Using ezdxf (Python)
```python
import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment

def create_pid_drawing(drawing_data: DrawingData) -> str:
    """
    Create AutoCAD DXF file from validated drawing data.
    """
    # Create new drawing
    doc = ezdxf.new('R2018')  # AutoCAD 2018 format
    doc.units = units.MM
    
    # Create layers
    create_layers(doc)
    
    # Get modelspace
    msp = doc.modelspace()
    
    # Create and insert symbol blocks
    for symbol in drawing_data.symbols:
        block = get_or_create_block(doc, symbol.symbol_class)
        msp.add_blockref(
            block.name,
            insert=(symbol.bbox.x, symbol.bbox.y),
            dxfattribs={
                'layer': get_layer_for_symbol(symbol),
                'rotation': symbol.rotation
            }
        )
        # Set block attributes
        set_block_attributes(msp, symbol)
    
    # Draw lines
    for line in drawing_data.lines:
        msp.add_lwpolyline(
            line.path_points,
            dxfattribs={
                'layer': get_layer_for_line(line),
                'lineweight': get_lineweight(line)
            }
        )
    
    # Add text
    for text in drawing_data.text:
        msp.add_text(
            text.text_content,
            dxfattribs={
                'layer': 'TEXT-TAGS',
                'height': 2.5,
                'rotation': text.rotation
            }
        ).set_placement(
            (text.bbox.x, text.bbox.y),
            align=TextEntityAlignment.MIDDLE_CENTER
        )
    
    # Add title block
    add_title_block(doc, msp, drawing_data.title_block)
    
    # Save
    output_path = f"/tmp/{drawing_data.id}.dxf"
    doc.saveas(output_path)
    
    return output_path
```

### Layer Creation
```python
def create_layers(doc):
    layers = [
        ('EQUIPMENT', 4, 'Continuous'),      # Cyan
        ('INSTRUMENTS', 6, 'Continuous'),    # Magenta
        ('VALVES', 3, 'Continuous'),         # Green
        ('PIPING-PROCESS', 7, 'Continuous'), # White
        ('PIPING-UTILITY', 2, 'DASHED'),     # Yellow
        ('PIPING-INSTRUMENT', 5, 'DASHED2'), # Blue
        ('TEXT-TAGS', 7, 'Continuous'),
        ('TEXT-LABELS', 7, 'Continuous'),
        ('TITLE-BLOCK', 7, 'Continuous'),
        ('BORDER', 7, 'Continuous'),
    ]
    
    for name, color, linetype in layers:
        doc.layers.add(name, color=color, linetype=linetype)
```

## API Endpoints

### Generate Export
```
POST /api/v1/drawings/{id}/export
Content-Type: application/json

Request:
{
  "format": "dwg",
  "options": {
    "paperSize": "A1",
    "scale": "1:50",
    "includeConnections": true
  }
}

Response: 202 Accepted
{
  "jobId": "uuid",
  "status": "processing"
}
```

### Download Export
```
GET /api/v1/drawings/{id}/export/{jobId}/download

Response: 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="P&ID-001_RevA.dwg"
```

### Export Options
```typescript
interface ExportOptions {
  format: 'dwg' | 'dxf';
  paperSize: 'A0' | 'A1' | 'A2' | 'A3' | 'A4';
  scale: string;                    // e.g., "1:50"
  includeConnections: boolean;      // Draw connection points
  includeAnnotations: boolean;      // Include notes
  layerMapping?: LayerMapping;      // Custom layer names
  blockStyle?: 'iso10628' | 'custom';
}
```

## Acceptance Criteria

1. Exported DWG opens correctly in AutoCAD 2018+
2. Exported DXF opens correctly in AutoCAD and other CAD software
3. Symbols are editable blocks with attributes
4. Attributes (tags, descriptions) can be edited in AutoCAD
5. Layers are correctly organized and named
6. Line types and weights are correct
7. Text is editable (not exploded)
8. Scale matches original drawing
9. Title block contains correct metadata
10. File size is reasonable (<10MB for typical P&ID)

## Symbol Library

### ISO 10628 Block Library
- 50 standard symbol blocks (see ai-symbol-detection.md)
- Each block includes connection points
- Blocks are parametric where applicable

### Custom Block Support
- Admin can request new block additions
- Blocks added to library for organization
- Versioned block library

## Error Handling

| Error | Action |
|-------|--------|
| Unknown symbol type | Use generic block, log warning |
| Missing attributes | Export with empty attributes |
| Invalid geometry | Skip element, log error |
| File generation failure | Retry, then report error |
| File too large | Compress or split |

## Quality Validation

Before download, verify:
1. All symbols are placed
2. All lines are drawn
3. All text is present
4. Layer count matches expected
5. File is valid DWG/DXF
