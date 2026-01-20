# Flowex Workflow Diagrams

This document contains Mermaid diagrams explaining the Flowex symbol detection and processing workflow.

## Full System Workflow

```mermaid
flowchart TD
    subgraph User["User Actions"]
        U1[Create Project] --> U2[Upload PDF]
    end

    subgraph Storage["Storage"]
        U2 --> ST1{Environment}
        ST1 -->|Dev| SUP[Supabase Storage]
        ST1 -->|Prod| S3[AWS S3]
    end

    subgraph Processing["Background Processing"]
        SUP --> CQ[Celery Task Queue]
        S3 --> CQ
        CQ --> PDF[PDF Processing<br/>Convert to Images]
    end

    subgraph ML["ML Detection"]
        PDF --> DET[Symbol Detector<br/>Faster R-CNN]
        PDF --> OCR[OCR Pipeline<br/>Tesseract 5.x]

        DET --> SYM[Detected Symbols<br/>- Equipment<br/>- Instruments<br/>- Valves<br/>- Piping]

        OCR --> TXT[Extracted Text<br/>- Tag Numbers<br/>- Labels<br/>- Annotations]

        SYM --> ASSOC[Tag Associator]
        TXT --> ASSOC
    end

    subgraph Database["Database"]
        ASSOC --> DB[(PostgreSQL<br/>Supabase)]
        DB --> SYM_TBL[Symbols Table]
        DB --> TXT_TBL[Texts Table]
        DB --> DWG_TBL[Drawings Table]
    end

    subgraph Validation["Human Validation"]
        DB --> VAL[Validation Interface<br/>Side-by-Side View]
        VAL --> CORR{Corrections Needed?}
        CORR -->|Yes| EDIT[Edit Symbols/Text]
        EDIT --> DB
        CORR -->|No| APPROVE[Approve]
    end

    subgraph Export["Export"]
        APPROVE --> EXP{Export Format}
        EXP --> DXF[DXF/DWG<br/>AutoCAD Drawing]
        EXP --> DATA[Data Lists]

        DATA --> EQ[Equipment List]
        DATA --> LINE[Line List]
        DATA --> INST[Instrument List]
        DATA --> VALVE[Valve List]
        DATA --> MTO[Material Take-Off]
    end
```

## Simplified Linear Flow

```mermaid
flowchart LR
    A[PDF] --> B[Storage] --> C[Process] --> D[ML Detect] --> E[Validate] --> F[DWG + Data]
```

## Symbol Detection Pipeline

```mermaid
flowchart TB
    subgraph Training["Training Pipeline"]
        direction TB
        A1[Real P&ID Images] --> D1[PIDDataset]
        A2[Synthetic Generator] --> D1
        D1 --> T1[train.py]
        T1 --> M1{Model Choice}
        M1 -->|Full| R1[ResNet50 + FPN<br/>~160MB]
        M1 -->|Mobile| R2[MobileNetV3 + FPN<br/>~35MB]
        R1 --> Q1[Quantization]
        R2 --> Q1
        Q1 --> S1[Saved Models<br/>best_model.pt]
    end

    subgraph Inference["Inference Pipeline"]
        direction TB
        P1[PDF Upload] --> P2[PDF to Image]
        P2 --> I1[InferenceService]

        subgraph Detection["Symbol Detection"]
            I1 --> SD[SymbolDetector<br/>Faster R-CNN]
            SD --> SYM[Detected Symbols<br/>50 ISO 10628 Classes]
        end

        subgraph OCR["Text Extraction"]
            I1 --> OC[OCRPipeline<br/>Tesseract 5.x]
            OC --> TXT[Extracted Text<br/>Tags and Labels]
        end

        SYM --> TA[TagAssociator]
        TXT --> TA
        TA --> AR[AnalysisResult<br/>Symbols + Tags]
    end

    subgraph Output["Output"]
        AR --> V1[Validation UI]
        V1 --> E1[DXF/DWG Export]
        V1 --> E2[Data Lists<br/>Equipment, Instruments, Valves]
    end

    S1 -.->|Load Model| I1
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **Model** | `ml/training/model.py` | Faster R-CNN with ResNet50+FPN |
| **Mobile Model** | `ml/training/model_mobile.py` | Lightweight MobileNetV3 variant |
| **Training** | `ml/training/train.py` | Training loop & checkpoints |
| **Dataset** | `ml/training/dataset.py` | COCO format data loading |
| **Symbol Classes** | `ml/training/symbol_classes.py` | 50 ISO 10628 P&ID symbols |
| **Inference** | `backend/app/ml/inference.py` | Production inference service |
| **OCR** | `backend/app/ml/ocr_pipeline.py` | Tesseract text extraction |
| **Processing** | `backend/app/tasks/processing.py` | Celery background task |

## Data Flow Summary

| Step | Input | Output | Technology |
|------|-------|--------|------------|
| 1. Upload | PDF file | Stored file | Supabase/S3 |
| 2. Process | PDF | Images | Celery + Redis |
| 3. Detect | Images | Symbols (50 classes) | PyTorch, ResNet50+FPN |
| 4. OCR | Images | Text & tags | Tesseract 5.x |
| 5. Validate | Detections | Corrected data | React UI |
| 6. Export | Validated data | DWG + Lists | ezdxf |

## Symbol Categories (ISO 10628)

The system detects 50 symbol classes across 4 categories:

- **Equipment (15)**: Vessels, pumps, compressors, heat exchangers, tanks, etc.
- **Instruments (20)**: Transmitters, controllers, indicators, sensors, etc.
- **Valves (13)**: Gate, globe, ball, check, control valves, etc.
- **Piping (2)**: Lines, connections
