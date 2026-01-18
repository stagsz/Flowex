# Spec: Upload & PDF Processing

## Job to be Done
Users need to upload PDF P&ID files (vector and scanned) for AI processing.

## Functional Requirements

### File Upload
| ID | Requirement | Priority |
|----|-------------|----------|
| UP-01 | Support PDF file upload (single and batch) | Must-Have |
| UP-02 | Support vector PDF files (CAD-exported) | Must-Have |
| UP-03 | Support scanned/raster PDF files | Must-Have |
| UP-04 | Maximum file size: 50MB per file | Must-Have |
| UP-05 | Maximum batch upload: 10 files at once | Must-Have |
| UP-06 | Drag-and-drop upload interface | Must-Have |
| UP-07 | Upload progress indicator with percentage | Must-Have |
| UP-08 | Automatic file type detection (vector vs scanned) | Must-Have |
| UP-09 | File validation before processing (type, size, corruption) | Must-Have |
| UP-10 | Chunked upload for large files (resume on failure) | Should-Have |

### PDF Processing Pipeline
| ID | Requirement | Priority |
|----|-------------|----------|
| PP-01 | Convert PDF pages to images (300 DPI minimum) | Must-Have |
| PP-02 | Detect if PDF is vector or raster | Must-Have |
| PP-03 | For scanned PDFs: deskew correction | Must-Have |
| PP-04 | For scanned PDFs: noise reduction | Must-Have |
| PP-05 | For scanned PDFs: binarization | Must-Have |
| PP-06 | Tile large drawings into 1024x1024 segments for AI | Must-Have |
| PP-07 | Queue processing jobs (background worker) | Must-Have |
| PP-08 | Track processing status per drawing | Must-Have |

### Storage
| ID | Requirement | Priority |
|----|-------------|----------|
| ST-01 | Store original files in encrypted blob storage | Must-Have |
| ST-02 | Generate unique file IDs (UUID) | Must-Have |
| ST-03 | EU data residency (eu-west-1 or similar) | Must-Have |
| ST-04 | Virus scanning before storage | Should-Have |
| ST-05 | Automatic cleanup of orphaned files | Should-Have |

## Data Model

```typescript
interface Drawing {
  id: string;                    // UUID
  projectId: string;             // FK to Project
  organizationId: string;        // FK to Organization
  originalFilename: string;
  storagePath: string;           // S3/Blob path
  fileSizeBytes: number;
  fileType: 'pdf_vector' | 'pdf_scanned';
  drawingNumber?: string;        // Extracted from title block
  revision?: string;
  title?: string;
  status: DrawingStatus;
  processingStartedAt?: Date;
  processingCompletedAt?: Date;
  errorMessage?: string;
  createdBy: string;             // FK to User
  createdAt: Date;
  updatedAt: Date;
}

type DrawingStatus = 
  | 'uploaded'      // File received, awaiting processing
  | 'processing'    // AI extraction in progress
  | 'review'        // Ready for user validation
  | 'complete'      // Validated and exported
  | 'error';        // Processing failed
```

## API Endpoints

### Upload Drawing
```
POST /api/v1/drawings/upload
Content-Type: multipart/form-data

Request:
  - file: File (PDF)
  - projectId: string

Response: 201 Created
{
  "id": "uuid",
  "status": "uploaded",
  "originalFilename": "P&ID-001.pdf",
  "fileSizeBytes": 2458624
}
```

### Get Drawing Status
```
GET /api/v1/drawings/{id}

Response: 200 OK
{
  "id": "uuid",
  "status": "processing",
  "progress": 45,
  "estimatedTimeRemaining": 120
}
```

### List Drawings
```
GET /api/v1/projects/{projectId}/drawings
Query: ?status=review&page=1&limit=20

Response: 200 OK
{
  "items": [...],
  "total": 48,
  "page": 1,
  "limit": 20
}
```

## Acceptance Criteria

1. User can drag-and-drop PDF files into upload zone
2. User can select files from file browser
3. System validates file type and size before processing
4. User receives clear error messages for invalid files
5. Upload progress shows percentage complete
6. User can cancel in-progress uploads
7. System correctly detects vector vs scanned PDFs
8. Processing queue handles multiple concurrent uploads
9. Files are stored encrypted with EU residency

## Technical Notes

- Use `pdf2image` or `PyMuPDF` for PDF to image conversion
- Consider `poppler` for high-quality PDF rendering
- Implement retry logic for failed processing jobs
- Use Redis or RabbitMQ for job queue
- Set appropriate timeouts for large file processing

## Error Handling

| Error | User Message | Action |
|-------|--------------|--------|
| File too large | "File exceeds 50MB limit" | Reject upload |
| Invalid file type | "Only PDF files are supported" | Reject upload |
| Corrupted PDF | "Unable to read PDF file" | Reject upload |
| Processing timeout | "Processing took too long" | Allow retry |
| Storage failure | "Unable to save file" | Retry or fail gracefully |