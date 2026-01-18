# Spec: Validation Interface

## Job to be Done
Allow users to review, verify, and correct AI extraction results through an intuitive side-by-side interface.

## Functional Requirements

### Side-by-Side Comparison
| ID | Requirement | Priority |
|----|-------------|----------|
| VAL-01 | Display original PDF on left panel | Must-Have |
| VAL-02 | Display extracted drawing on right panel | Must-Have |
| VAL-03 | Synchronized zoom between panels | Must-Have |
| VAL-04 | Synchronized pan between panels | Must-Have |
| VAL-05 | Click on symbol to highlight in both views | Must-Have |
| VAL-06 | List of all extracted components (sortable, filterable) | Must-Have |
| VAL-07 | Visual indicators for items needing review | Must-Have |
| VAL-08 | Full-screen mode for detailed comparison | Must-Have |
| VAL-09 | Keyboard shortcuts for common actions | Should-Have |

### Human-in-the-Loop Editing
| ID | Requirement | Priority |
|----|-------------|----------|
| EDIT-01 | Add missing symbol (click to place) | Must-Have |
| EDIT-02 | Delete incorrect symbol | Must-Have |
| EDIT-03 | Change symbol type/classification | Must-Have |
| EDIT-04 | Edit extracted text/tags | Must-Have |
| EDIT-05 | Add/edit/delete connections between symbols | Must-Have |
| EDIT-06 | Undo/redo functionality (20 levels) | Must-Have |
| EDIT-07 | Auto-save work-in-progress | Must-Have |
| EDIT-08 | Mark item as "verified" | Must-Have |
| EDIT-09 | Mark item as "flagged for review" | Must-Have |
| EDIT-10 | Bulk verification (select multiple) | Should-Have |

### Validation Checklist
| ID | Requirement | Priority |
|----|-------------|----------|
| CHK-01 | Auto-generate checklist of all extracted items | Must-Have |
| CHK-02 | Group by category (equipment, instruments, valves, lines) | Must-Have |
| CHK-03 | Show verification status (verified, pending, flagged) | Must-Have |
| CHK-04 | Allow bulk verification | Must-Have |
| CHK-05 | Optional: require all items verified before export | Must-Have |
| CHK-06 | Print/export checklist as PDF | Must-Have |
| CHK-07 | Progress indicator (% complete) | Must-Have |

## User Interface Design

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOWEX        [Drawing Name] - Validation                         [×Close] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────┐ ┌────────────────────────────────────────┐  │
│  │     ORIGINAL PDF           │ │      EXTRACTED DRAWING                 │  │
│  │                            │ │                                        │  │
│  │   [Zoomable/Pannable       │ │   [Interactive drawing with            │  │
│  │    PDF Viewer]             │ │    highlighted symbols]                │  │
│  │                            │ │                                        │  │
│  │   [🔍+] [🔍-] [Fit] [Full] │ │   [🔍+] [🔍-] [Fit] [Full]            │  │
│  └────────────────────────────┘ └────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  COMPONENTS                                     Progress: 85% ████░░ │   │
│  │  [Equipment] [Instruments] [Valves] [Lines]     [✓ Verify All]       │   │
│  │  ────────────────────────────────────────────────────────────────    │   │
│  │  Status │ Tag      │ Type              │ Description    │ Actions   │   │
│  │  ✓      │ P-101    │ Pump_Centrifugal  │ Feed Pump      │ [✎] [🔍]  │   │
│  │  ⚠      │ V-201    │ Vessel_Vertical   │ [unclear]      │ [✎] [🔍]  │   │
│  │  ○      │ E-301    │ Heat_Exchanger    │ Preheater      │ [✎] [🔍]  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  [← Back]                      [Save]              [Complete & Export →]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Status Icons
| Icon | Status | Meaning |
|------|--------|---------|
| ✓ (green) | Verified | User confirmed correct |
| ○ (gray) | Pending | Not yet reviewed |
| ⚠ (orange) | Flagged | Low confidence or issue |
| ✗ (red) | Error | Problem detected |

## Interaction Patterns

### Symbol Selection
```typescript
// When user clicks a symbol in either panel
function handleSymbolClick(symbolId: string) {
  // 1. Highlight in extracted view
  highlightSymbol(extractedCanvas, symbolId);
  
  // 2. Pan original PDF to corresponding location
  const symbol = getSymbol(symbolId);
  panToLocation(originalPdf, symbol.bbox);
  
  // 3. Highlight region in original PDF
  drawHighlightOverlay(originalPdf, symbol.bbox);
  
  // 4. Scroll component list to show item
  scrollToListItem(symbolId);
  
  // 5. Show edit panel
  showEditPanel(symbolId);
}
```

### Edit Actions
```typescript
interface EditAction {
  type: 'add' | 'delete' | 'modify' | 'verify' | 'flag';
  entityType: 'symbol' | 'line' | 'text';
  entityId: string;
  previousValue?: any;
  newValue?: any;
  timestamp: Date;
  userId: string;
}

// Undo/Redo stack
class EditHistory {
  private undoStack: EditAction[] = [];
  private redoStack: EditAction[] = [];
  
  push(action: EditAction) { /* ... */ }
  undo(): EditAction | null { /* ... */ }
  redo(): EditAction | null { /* ... */ }
}
```

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `V` | Verify selected item |
| `F` | Flag selected item |
| `Delete` | Delete selected item |
| `E` | Edit selected item |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+S` | Save |
| `+` / `-` | Zoom in/out |
| `Arrow keys` | Pan view |
| `Tab` | Next item in list |

## Data Model

```typescript
interface ValidationSession {
  id: string;
  drawingId: string;
  userId: string;
  startedAt: Date;
  lastSavedAt: Date;
  completedAt?: Date;
  editHistory: EditAction[];
  checklistProgress: ChecklistProgress;
}

interface ChecklistProgress {
  totalItems: number;
  verifiedItems: number;
  flaggedItems: number;
  pendingItems: number;
  byCategory: {
    equipment: CategoryProgress;
    instruments: CategoryProgress;
    valves: CategoryProgress;
    lines: CategoryProgress;
  };
}

interface CategoryProgress {
  total: number;
  verified: number;
  flagged: number;
}
```

## API Endpoints

### Start Validation Session
```
POST /api/v1/drawings/{id}/validation/start

Response: 201 Created
{
  "sessionId": "uuid",
  "drawingId": "uuid",
  "checklistProgress": { ... }
}
```

### Save Validation Progress
```
PUT /api/v1/drawings/{id}/validation
Content-Type: application/json

Request:
{
  "actions": [
    {
      "type": "verify",
      "entityType": "symbol",
      "entityId": "uuid"
    }
  ]
}

Response: 200 OK
```

### Update Symbol
```
PATCH /api/v1/symbols/{id}
Content-Type: application/json

Request:
{
  "tagNumber": "P-101A",
  "symbolClass": "Pump_Centrifugal",
  "isVerified": true
}

Response: 200 OK
```

### Add New Symbol
```
POST /api/v1/drawings/{drawingId}/symbols
Content-Type: application/json

Request:
{
  "symbolClass": "Valve_Gate",
  "bbox": {"x": 300, "y": 400, "width": 30, "height": 30},
  "tagNumber": "V-105"
}

Response: 201 Created
```

### Complete Validation
```
POST /api/v1/drawings/{id}/validation/complete

Response: 200 OK
{
  "drawingId": "uuid",
  "status": "complete",
  "validatedAt": "2026-01-18T12:00:00Z",
  "validatedBy": "user-uuid"
}
```

## Acceptance Criteria

1. Users can view original PDF and extracted data side-by-side
2. Zoom and pan are synchronized between both panels
3. Clicking a symbol highlights it in both views
4. Users can add, edit, and delete symbols
5. Users can edit extracted text
6. Undo/redo works for all edit actions
7. Progress auto-saves every 30 seconds
8. Validation checklist shows accurate progress
9. Users can verify items individually or in bulk
10. Export is blocked until checklist complete (if enabled)
11. All keyboard shortcuts work correctly

## Performance Requirements

| Metric | Target |
|--------|--------|
| Initial load time | <3 seconds |
| Pan/zoom responsiveness | 60 FPS |
| Edit action feedback | <100ms |
| Auto-save | Every 30 seconds |
| Undo/redo levels | 20 minimum |

## Accessibility

- Full keyboard navigation
- Screen reader support for component list
- High contrast mode option
- Minimum touch target size: 44x44px
- Focus indicators on all interactive elements
