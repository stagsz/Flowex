# Spec: Data List Exports

## Job to be Done
Export extracted engineering data as structured lists (Equipment, Line, Instrument, Valve, MTO) in Excel, CSV, and PDF formats.

## Functional Requirements

### Export Types
| ID | Requirement | Priority |
|----|-------------|----------|
| DL-01 | Equipment List export | Must-Have |
| DL-02 | Line List export | Must-Have |
| DL-03 | Instrument List export | Must-Have |
| DL-04 | Valve List export | Must-Have |
| DL-05 | Material Take-Off (MTO) export | Must-Have |
| DL-06 | Combined/All Lists export | Should-Have |
| DL-07 | Comparison Report export | Must-Have |

### Export Formats
| ID | Requirement | Priority |
|----|-------------|----------|
| FMT-01 | Excel (.xlsx) - formatted with headers, filters | Must-Have |
| FMT-02 | CSV (.csv) - for import into other systems | Must-Have |
| FMT-03 | PDF (.pdf) - for printing and sharing | Must-Have |

## Data Structures

### Equipment List
| Field | Description | Type | Required |
|-------|-------------|------|----------|
| Tag Number | Equipment identifier (P-101) | String | Yes |
| Description | Equipment name | String | Yes |
| Type | Equipment category | String | Yes |
| Size/Capacity | Dimensions or capacity | String | No |
| Material | Construction material | String | No |
| Design Pressure | Design pressure rating | String | No |
| Design Temperature | Design temperature rating | String | No |
| Operating Pressure | Operating pressure | String | No |
| Operating Temperature | Operating temperature | String | No |
| Manufacturer | Equipment manufacturer | String | No |
| Model | Equipment model | String | No |
| Drawing Reference | Source P&ID number | String | Yes |
| Sheet Number | P&ID sheet number | String | No |
| Notes | Additional notes | String | No |

### Line List
| Field | Description | Type | Required |
|-------|-------------|------|----------|
| Line Number | Line identifier (6"-P-101-A1) | String | Yes |
| Size | Pipe diameter | String | Yes |
| Spec | Piping specification | String | Yes |
| From | Origin equipment/connection | String | Yes |
| To | Destination equipment/connection | String | Yes |
| Fluid | Process fluid | String | No |
| Design Pressure | Design pressure | String | No |
| Design Temperature | Design temperature | String | No |
| Insulation | Insulation type/thickness | String | No |
| Heat Tracing | Heat tracing type | String | No |
| Material | Pipe material | String | No |
| Drawing Reference | Source P&ID number | String | Yes |
| Notes | Additional notes | String | No |

### Instrument List
| Field | Description | Type | Required |
|-------|-------------|------|----------|
| Tag Number | Instrument identifier (FT-101) | String | Yes |
| Type | Instrument type | String | Yes |
| Description | Instrument description | String | Yes |
| Service | Process variable measured | String | No |
| Range | Measurement range | String | No |
| Units | Engineering units | String | No |
| Output | Signal type (4-20mA, digital) | String | No |
| Location | Field/Panel/DCS | String | No |
| Manufacturer | Instrument manufacturer | String | No |
| Model | Instrument model | String | No |
| Drawing Reference | Source P&ID number | String | Yes |
| Loop Number | Control loop reference | String | No |
| Notes | Additional notes | String | No |

### Valve List
| Field | Description | Type | Required |
|-------|-------------|------|----------|
| Tag Number | Valve identifier | String | Yes |
| Type | Valve type (gate, globe, ball) | String | Yes |
| Size | Valve size | String | Yes |
| Rating | Pressure rating (150#, 300#) | String | No |
| Spec | Piping specification | String | Yes |
| Line Number | Associated line | String | No |
| Body Material | Valve body material | String | No |
| Trim Material | Valve trim material | String | No |
| Actuator | Manual/Pneumatic/Electric | String | No |
| Fail Position | Open/Close/As-Is | String | No |
| Manufacturer | Valve manufacturer | String | No |
| Drawing Reference | Source P&ID number | String | Yes |
| Notes | Additional notes | String | No |

### Material Take-Off (MTO)
| Field | Description | Type | Required |
|-------|-------------|------|----------|
| Item Number | Sequential item number | Integer | Yes |
| Category | Component category | String | Yes |
| Description | Full description | String | Yes |
| Size | Dimensions | String | Yes |
| Material | Material specification | String | No |
| Quantity | Count | Integer | Yes |
| Unit | Unit of measure | String | Yes |
| Spec | Specification reference | String | No |
| Drawing Reference | Source P&ID number | String | Yes |
| Notes | Additional notes | String | No |

## Export Templates

### Excel Format
```
┌───────────────────────────────────────────────────────────────────────┐
│ A               B           C           D           E           F     │
├───────────────────────────────────────────────────────────────────────┤
│ EQUIPMENT LIST                                                        │
│ Project: WtE Plant Alpha     Date: 2026-01-18     Rev: A              │
├───────────────────────────────────────────────────────────────────────┤
│ Tag Number │ Description │ Type        │ Size      │ Drawing    │ ... │
├────────────┼─────────────┼─────────────┼───────────┼────────────┼─────┤
│ P-101      │ Feed Pump   │ Centrifugal │ 100 m³/h  │ P&ID-001   │ ... │
│ P-102      │ Transfer    │ Centrifugal │ 50 m³/h   │ P&ID-001   │ ... │
│ V-201      │ Feed Tank   │ Vertical    │ 50 m³     │ P&ID-002   │ ... │
└───────────────────────────────────────────────────────────────────────┘

Features:
- Header row with filters enabled
- Auto-sized columns
- Freeze first row
- Alternating row colors
- Print area defined
- Page headers for printing
```

### PDF Format
```
┌─────────────────────────────────────────────────────────────────────┐
│                        EQUIPMENT LIST                                │
│                                                                      │
│  Project: WtE Plant Alpha                    Date: 2026-01-18       │
│  Document: EL-001                            Rev: A                  │
│  Prepared by: Flowex                         Page: 1 of 3           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Tag      Description      Type           Size       Drawing        │
│  ────────────────────────────────────────────────────────────────   │
│  P-101    Feed Pump        Centrifugal    100 m³/h   P&ID-001       │
│  P-102    Transfer Pump    Centrifugal    50 m³/h    P&ID-001       │
│  V-201    Feed Tank        Vertical       50 m³      P&ID-002       │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Total Equipment: 24                                                 │
└─────────────────────────────────────────────────────────────────────┘

Features:
- Professional header with project info
- Company logo placeholder
- Page numbers
- Table formatting
- Summary counts
```

## Comparison Report

### Structure
```
EXTRACTION SUMMARY REPORT

1. DRAWING INFORMATION
   Drawing Number: P&ID-001
   Revision: A
   Project: Waste-to-Energy Plant Alpha
   Processed Date: 2026-01-18
   Processed By: anna.muller@epcfirm.eu

2. EXTRACTION STATISTICS
   ┌─────────────────┬───────┬──────────┬─────────┐
   │ Category        │ Count │ Verified │ Flagged │
   ├─────────────────┼───────┼──────────┼─────────┤
   │ Equipment       │    24 │       22 │       2 │
   │ Instruments     │    47 │       45 │       2 │
   │ Valves          │    89 │       87 │       2 │
   │ Lines           │    31 │       31 │       0 │
   ├─────────────────┼───────┼──────────┼─────────┤
   │ TOTAL           │   191 │      185 │       6 │
   └─────────────────┴───────┴──────────┴─────────┘

3. ITEMS FLAGGED FOR REVIEW
   - E-101: Symbol classification uncertain (confidence: 0.68)
   - FT-103: Tag number unclear (OCR confidence: 0.72)
   ...

4. VALIDATION CHECKLIST STATUS
   Completed: 185/191 (97%)

5. EXPORT FILES GENERATED
   - P&ID-001_Rev-A.dwg
   - P&ID-001_Equipment-List.xlsx
   - P&ID-001_Line-List.xlsx
   - P&ID-001_Instrument-List.xlsx
   - P&ID-001_Valve-List.xlsx
   - P&ID-001_MTO.xlsx
```

## API Endpoints

### Generate Data Lists
```
POST /api/v1/drawings/{id}/export/lists
Content-Type: application/json

Request:
{
  "lists": ["equipment", "lines", "instruments", "valves", "mto"],
  "format": "xlsx",
  "includeUnverified": false
}

Response: 202 Accepted
{
  "jobId": "uuid",
  "status": "processing"
}
```

### Download Data List
```
GET /api/v1/drawings/{id}/export/lists/{jobId}

Response: 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="P&ID-001_Equipment-List.xlsx"
```

### Generate Comparison Report
```
POST /api/v1/drawings/{id}/export/report
Content-Type: application/json

Request:
{
  "format": "pdf"
}

Response: 202 Accepted
```

### Batch Export
```
POST /api/v1/projects/{projectId}/export/batch
Content-Type: application/json

Request:
{
  "drawingIds": ["uuid1", "uuid2", "uuid3"],
  "outputs": ["dwg", "equipment_list", "line_list"],
  "format": "xlsx"
}

Response: 202 Accepted
{
  "jobId": "uuid",
  "totalDrawings": 3,
  "status": "processing"
}
```

## Implementation

### Excel Generation (Python)
```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border
from openpyxl.utils import get_column_letter

def generate_equipment_list(drawing_data, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Equipment List"
    
    # Header styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", fill_type="solid")
    
    # Add headers
    headers = ["Tag Number", "Description", "Type", "Size", "Drawing"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    # Add data
    for row, equip in enumerate(drawing_data.equipment, 2):
        ws.cell(row=row, column=1, value=equip.tag_number)
        ws.cell(row=row, column=2, value=equip.description)
        ws.cell(row=row, column=3, value=equip.type)
        ws.cell(row=row, column=4, value=equip.size)
        ws.cell(row=row, column=5, value=drawing_data.drawing_number)
    
    # Auto-fit columns
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].auto_size = True
    
    # Enable filters
    ws.auto_filter.ref = ws.dimensions
    
    # Freeze header row
    ws.freeze_panes = 'A2'
    
    wb.save(output_path)
```

## Acceptance Criteria

1. Equipment list contains all detected equipment with correct tags
2. Line list contains all detected lines with from/to connections
3. Instrument list contains all detected instruments
4. Valve list contains all detected valves
5. MTO aggregates quantities correctly
6. Excel files have proper formatting and filters
7. CSV files use standard delimiters (comma)
8. PDF files are printable with correct pagination
9. All exports include drawing reference
10. Comparison report accurately summarizes extraction

## Error Handling

| Error | Action |
|-------|--------|
| No data for list type | Generate empty file with headers |
| Missing required field | Use placeholder or skip row |
| File generation failure | Retry, then report error |
| Invalid characters | Sanitize before export |
