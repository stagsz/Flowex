# Spec: AI Symbol Detection

## Job to be Done
Automatically detect and classify P&ID symbols from uploaded drawings using computer vision.

## Functional Requirements

### Symbol Detection
| ID | Requirement | Priority |
|----|-------------|----------|
| SD-01 | Detect equipment symbols (vessels, pumps, tanks, heat exchangers) | Must-Have |
| SD-02 | Detect instrument symbols (transmitters, controllers, indicators) | Must-Have |
| SD-03 | Detect valve symbols (gate, globe, ball, check, control) | Must-Have |
| SD-04 | Detect piping elements (lines, reducers, flanges) | Must-Have |
| SD-05 | Classify symbols according to ISO 10628 standard | Must-Have |
| SD-06 | Detect symbol orientation (0°, 90°, 180°, 270°) | Must-Have |
| SD-07 | Detect symbol connection points (nozzles, ports) | Must-Have |
| SD-08 | Output confidence score per detection | Must-Have |
| SD-09 | Handle overlapping symbols | Should-Have |
| SD-10 | Support hybrid custom symbol library (admin request) | Must-Have |

### Line Detection
| ID | Requirement | Priority |
|----|-------------|----------|
| LD-01 | Detect process lines | Must-Have |
| LD-02 | Detect utility lines | Must-Have |
| LD-03 | Detect instrument lines | Must-Have |
| LD-04 | Classify line types by style (solid, dashed, etc.) | Must-Have |
| LD-05 | Detect line endpoints and connections | Must-Have |
| LD-06 | Build connectivity graph | Must-Have |

### Performance Requirements
| ID | Requirement | Target |
|----|-------------|--------|
| PERF-01 | Symbol detection accuracy (ISO 10628) | >90% |
| PERF-02 | Processing time per P&ID | <60 seconds |
| PERF-03 | False positive rate | <5% |
| PERF-04 | Batch processing throughput | 10 P&IDs concurrent |

## Symbol Categories (ISO 10628)

### Equipment Symbols (15 classes)
```
01. Vessel_Vertical
02. Vessel_Horizontal
03. Tank_Atmospheric
04. Column_Distillation
05. Heat_Exchanger_Shell_Tube
06. Heat_Exchanger_Plate
07. Pump_Centrifugal
08. Pump_Positive_Displacement
09. Compressor_Centrifugal
10. Compressor_Reciprocating
11. Filter
12. Reactor
13. Furnace
14. Blower
15. Agitator
```

### Instrument Symbols (15 classes)
```
16. Transmitter_Pressure
17. Transmitter_Temperature
18. Transmitter_Flow
19. Transmitter_Level
20. Controller_Generic
21. Indicator_Generic
22. Alarm_High
23. Alarm_Low
24. Switch_Generic
25. Control_Valve_Globe
26. Control_Valve_Butterfly
27. Orifice_Plate
28. Thermowell
29. Sample_Point
30. Relief_Valve_Instrument
```

### Valve Symbols (15 classes)
```
31. Valve_Gate
32. Valve_Globe
33. Valve_Ball
34. Valve_Butterfly
35. Valve_Check
36. Valve_Relief_PSV
37. Valve_Control
38. Valve_Three_Way
39. Valve_Diaphragm
40. Valve_Plug
41. Valve_Needle
42. Valve_Manual_Generic
43. Actuator_Pneumatic
44. Actuator_Electric
45. Actuator_Hydraulic
```

### Other Symbols (5 classes)
```
46. Reducer
47. Flange
48. Spectacle_Blind
49. Strainer
50. Steam_Trap
```

## Data Model

```typescript
interface DetectedSymbol {
  id: string;
  drawingId: string;
  symbolClass: string;           // e.g., "Pump_Centrifugal"
  category: 'equipment' | 'instrument' | 'valve' | 'other';
  bbox: BoundingBox;
  rotation: 0 | 90 | 180 | 270;
  confidence: number;            // 0.0 - 1.0
  connectionPoints: Point[];     // Nozzle/port locations
  isVerified: boolean;
  isFlagged: boolean;            // Low confidence or needs review
  createdAt: Date;
  updatedAt: Date;
}

interface BoundingBox {
  x: number;      // Top-left X
  y: number;      // Top-left Y
  width: number;
  height: number;
}

interface Point {
  x: number;
  y: number;
}

interface DetectedLine {
  id: string;
  drawingId: string;
  lineType: 'process' | 'utility' | 'instrument';
  pathPoints: Point[];           // Array of coordinates
  fromSymbolId?: string;         // Connected symbol
  toSymbolId?: string;           // Connected symbol
  confidence: number;
}
```

## CNN Model Architecture

### Specification
| Component | Value |
|-----------|-------|
| Backbone | ResNet-50 (pretrained ImageNet) |
| Neck | Feature Pyramid Network (FPN) |
| Head | Object Detection (class + bbox) |
| Input Size | 1024 x 1024 pixels |
| Output | Bounding boxes, class labels, confidence |
| Classes | 50 symbol classes |
| Framework | PyTorch 2.x |

### Training Strategy
| Phase | Data Source | Epochs | Learning Rate |
|-------|-------------|--------|---------------|
| Phase 1 | Synthetic P&IDs (10,000 images) | 50 | 1e-3 |
| Phase 2 | Real labeled P&IDs (500 images) | 30 | 1e-4 |
| Phase 3 | Customer feedback fine-tuning | Ongoing | 1e-5 |

### Inference Pipeline
```
Input Image (1024x1024)
    │
    ▼
┌─────────────────┐
│  ResNet-50      │ ← Feature extraction
│  Backbone       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FPN Neck       │ ← Multi-scale features
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Detection Head │ ← Predict boxes + classes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NMS            │ ← Filter overlapping
└────────┬────────┘
         │
         ▼
Output: List of (bbox, class, confidence)
```

## Acceptance Criteria

1. Model achieves >90% mAP on ISO 10628 symbol test set
2. Detects symbols at all four orientations correctly
3. Returns confidence scores for all detections
4. Flags low-confidence detections (<0.7) for review
5. Processes a typical P&ID in under 60 seconds
6. Handles both vector and scanned input images
7. Connection points are identified for equipment symbols
8. Line connectivity graph is correctly constructed

## Training Data Requirements

### Synthetic Data Generation
- Generate P&IDs programmatically with known labels
- Vary: symbol types, positions, rotations, scales
- Add: noise, blur, rotation for scanned simulation
- Target: 10,000 synthetic images for Phase 1

### Real Data Labeling
- Annotate 500 real P&IDs manually
- Use labeling tool (CVAT, Label Studio, or similar)
- Include edge cases: poor quality, unusual symbols
- Cross-validate with multiple annotators

## API Endpoints

### Trigger Symbol Detection
```
POST /api/v1/drawings/{id}/process
Content-Type: application/json

Request:
{
  "stages": ["symbols", "lines", "associations"]
}

Response: 202 Accepted
{
  "jobId": "uuid",
  "status": "queued"
}
```

### Get Detection Results
```
GET /api/v1/drawings/{id}/symbols
Query: ?category=equipment&minConfidence=0.7

Response: 200 OK
{
  "items": [
    {
      "id": "uuid",
      "symbolClass": "Pump_Centrifugal",
      "category": "equipment",
      "bbox": {"x": 245.5, "y": 380.2, "width": 60, "height": 45},
      "rotation": 0,
      "confidence": 0.94
    }
  ],
  "total": 24
}
```

## Error Handling

| Error | Action |
|-------|--------|
| Image too small | Reject with minimum resolution message |
| Model timeout | Retry with increased timeout |
| GPU out of memory | Fall back to CPU or queue |
| Unknown symbol | Flag for review, don't crash |
