# Flowex Beta Testing Guide

**Version:** 1.0
**Last Updated:** 2026-01-21
**Status:** Ready for Beta Testing

---

## Overview

This document provides comprehensive guidance for beta testing Flowex with pilot customers. The goal is to validate the platform's functionality, usability, and reliability before general availability.

### Production Environment

| Service | URL |
|---------|-----|
| **Frontend** | https://frontend-xi-seven-28.vercel.app |
| **Backend API** | https://flowex-production-30eb.up.railway.app |
| **API Documentation** | https://flowex-production-30eb.up.railway.app/docs |
| **Database/Auth** | Supabase (pkagkffjhvtbovxzaytx.supabase.co) |

---

## Beta Testing Objectives

### Primary Goals

1. **Validate Core Workflow**: Ensure end-to-end P&ID digitization works reliably
2. **Assess AI Accuracy**: Measure symbol detection and OCR accuracy on real customer data
3. **Evaluate UX**: Gather feedback on the validation interface usability
4. **Identify Bugs**: Find and fix critical issues before GA
5. **Performance Testing**: Ensure the platform handles real-world workloads

### Success Criteria

| Metric | Target |
|--------|--------|
| Symbol detection accuracy | >90% on vector PDFs, >85% on scanned |
| OCR text extraction accuracy | >95% on vector PDFs, >85% on scanned |
| Processing time per P&ID | <60 seconds |
| Dashboard load time | <3 seconds |
| Critical bug count | 0 at GA |
| User satisfaction rating | >4.0/5.0 |

---

## Beta Testing Checklist

### 1. Authentication & Access

- [ ] **SSO Login (Microsoft)**: Successfully authenticate via Microsoft SSO
- [ ] **SSO Login (Google)**: Successfully authenticate via Google SSO
- [ ] **Session Persistence**: Verify session persists across browser refreshes
- [ ] **Logout**: Confirm logout clears session and redirects to login
- [ ] **Token Refresh**: Verify automatic token refresh works (24-hour expiry)
- [ ] **Role-Based Access**: Verify admin/member/viewer permissions work correctly

### 2. Dashboard & Navigation

- [ ] **Dashboard Load**: Dashboard loads in <3 seconds with stats displayed
- [ ] **Project List**: All projects visible and filterable
- [ ] **Drawing List**: All drawings visible with correct status
- [ ] **Navigation**: Sidebar navigation works correctly
- [ ] **Responsive Layout**: UI adapts to different screen sizes

### 3. File Upload & Processing

- [ ] **Drag-and-Drop Upload**: Files upload via drag-and-drop
- [ ] **Click Upload**: Files upload via file picker
- [ ] **File Validation**: Invalid files (wrong type, too large) rejected with clear errors
- [ ] **Upload Progress**: Progress indicator shows during upload
- [ ] **Processing Status**: Status updates correctly (uploaded → processing → review)
- [ ] **Vector PDF Detection**: Vector PDFs identified correctly
- [ ] **Scanned PDF Detection**: Scanned PDFs identified correctly
- [ ] **Large File Handling**: Files up to 50MB process successfully

### 4. AI Symbol Detection

- [ ] **Equipment Detection**: Pumps, tanks, vessels identified correctly
- [ ] **Instrument Detection**: Flow transmitters, pressure gauges, etc. identified
- [ ] **Valve Detection**: Control valves, check valves, etc. identified
- [ ] **Line Detection**: Process lines detected with connections
- [ ] **Confidence Scores**: Low-confidence items flagged appropriately
- [ ] **ISO 10628 Compliance**: All 50 symbol classes recognized

### 5. OCR Text Extraction

- [ ] **Equipment Tags**: Tags like P-101, TK-201 extracted correctly
- [ ] **Instrument Tags**: Tags like FT-101, PI-301 extracted correctly
- [ ] **Line Numbers**: Line designations extracted correctly
- [ ] **Title Block**: Drawing number, revision, date extracted
- [ ] **Rotated Text**: 90°, 180°, 270° rotated text handled
- [ ] **Tag-Symbol Association**: Tags correctly linked to symbols

### 6. Validation Interface

- [ ] **Side-by-Side View**: Original PDF and extracted data shown together
- [ ] **Zoom/Pan Sync**: PDF viewer and component list stay synchronized
- [ ] **Component List**: Filterable by Equipment, Instrument, Valve, Line
- [ ] **Search**: Can search for specific tags
- [ ] **Select Component**: Clicking component highlights it on PDF
- [ ] **Edit Component**: Can modify tag, classification, position
- [ ] **Delete Component**: Can remove incorrectly detected items
- [ ] **Add Component**: Can manually add missing symbols
- [ ] **Verify Component**: Can mark items as verified
- [ ] **Flag for Review**: Can flag items for human review
- [ ] **Bulk Selection**: Can select multiple items and verify/flag in bulk
- [ ] **Keyboard Shortcuts**: V (verify), F (flag), Delete, Ctrl+Z/Y (undo/redo)
- [ ] **Full-Screen Mode**: Can toggle full-screen for detailed comparison
- [ ] **Auto-Save**: Changes save automatically with visual indicator
- [ ] **Progress Tracking**: Completion percentage updates correctly

### 7. Export Features

- [ ] **DXF Export**: Generates valid DXF file that opens in AutoCAD
- [ ] **Layer Organization**: DXF has correct layers (Equipment, Instruments, etc.)
- [ ] **Symbol Blocks**: ISO 10628 symbols render correctly
- [ ] **Equipment List Export**: Excel/CSV/PDF formats work
- [ ] **Line List Export**: Excel/CSV/PDF formats work
- [ ] **Instrument List Export**: Excel/CSV/PDF formats work
- [ ] **Valve List Export**: Excel/CSV/PDF formats work
- [ ] **MTO Export**: Material Take-Off generates correctly
- [ ] **Comparison Report**: Summary report generates with statistics
- [ ] **Validation Checklist**: Can export PDF checklist with status

### 8. Cloud Storage Integration

- [ ] **OneDrive Connection**: Can connect to OneDrive account
- [ ] **SharePoint Connection**: Can connect to SharePoint sites
- [ ] **Google Drive Connection**: Can connect to Google Drive
- [ ] **Browse Files**: Can browse cloud folders
- [ ] **Import Files**: Can import PDFs from cloud storage
- [ ] **Export Files**: Can export results to cloud storage
- [ ] **Token Refresh**: Cloud connections stay valid over time

### 9. GDPR Compliance

- [ ] **Data Export**: Can download all personal data (Article 15)
- [ ] **Account Deletion**: Can request account deletion (Article 17)
- [ ] **Data in EU**: Confirm data stored in EU region (eu-west-1)

### 10. Performance & Reliability

- [ ] **Concurrent Users**: Multiple users can work simultaneously
- [ ] **Large P&IDs**: A3/A1 size drawings process correctly
- [ ] **Error Recovery**: System recovers gracefully from errors
- [ ] **Network Issues**: Handles poor network conditions
- [ ] **Browser Compatibility**: Works in Chrome, Firefox, Edge, Safari

---

## Feedback Collection

### In-App Feedback Widget

Users can submit feedback directly from the application using the Feedback button in the header:

1. Click the **Feedback** button (speech bubble icon)
2. Select feedback type: Bug, Feature Request, Usability, Performance, or General
3. Provide a title and detailed description
4. Set priority level (Low, Medium, High, Critical)
5. Optionally rate overall satisfaction (1-5 stars)
6. Submit

### Feedback API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/feedback` | POST | Submit feedback |
| `/api/v1/feedback` | GET | List feedback (admin) |
| `/api/v1/feedback/stats` | GET | Feedback statistics (admin) |
| `/api/v1/feedback/{id}` | GET | Get specific feedback |
| `/api/v1/feedback/{id}/status` | PATCH | Update status (admin) |

---

## Known Limitations (Beta)

1. **Training Data**: AI models trained on synthetic data; accuracy may vary on real P&IDs
2. **Language Support**: OCR optimized for English text only
3. **DWG Export**: Currently DXF only; DWG requires additional tooling
4. **Concurrent Editing**: No real-time collaboration on same drawing
5. **Mobile Support**: Validation interface optimized for desktop

---

## Bug Reporting Guidelines

When reporting bugs, please include:

1. **Steps to Reproduce**: Exact steps to trigger the issue
2. **Expected Behavior**: What should happen
3. **Actual Behavior**: What actually happens
4. **Screenshots/Videos**: Visual evidence if applicable
5. **Browser/OS**: e.g., Chrome 120, Windows 11
6. **File Info**: Drawing size, type (vector/scanned)
7. **Error Messages**: Any error messages shown

Use the in-app feedback widget with type "Bug Report" or email support@flowex.io.

---

## Contact Information

| Role | Contact |
|------|---------|
| Technical Support | support@flowex.io |
| Product Feedback | feedback@flowex.io |
| Security Issues | security@flowex.io |

---

## Appendix A: Test P&ID Recommendations

For comprehensive testing, please test with:

1. **Small Vector P&ID**: A4 size, <20 symbols, clean CAD output
2. **Large Vector P&ID**: A1 size, >100 symbols, complex piping
3. **Clean Scanned P&ID**: A3 size, good quality scan (300+ DPI)
4. **Poor Quality Scan**: Low resolution, tilted, or faded
5. **Mixed Content**: P&ID with notes, tables, legends

---

## Appendix B: Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| `V` | Verify selected item(s) |
| `F` | Flag selected item(s) for review |
| `A` | Add new symbol (click-to-place mode) |
| `Delete` | Delete selected item(s) |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+A` | Select all items |
| `Space` | Toggle selection |
| `Tab` | Navigate to next item |
| `G` | Toggle full-screen mode |
| `Escape` | Exit mode / deselect |
| `?` | Show keyboard shortcuts help |
| `+` / `-` | Zoom in / out |

---

*Thank you for participating in the Flowex beta program!*
