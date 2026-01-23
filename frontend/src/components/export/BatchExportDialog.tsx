import { useState, useCallback, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Download,
  FileText,
  FileSpreadsheet,
  ClipboardCheck,
  Loader2,
  CheckCircle,
  AlertTriangle,
} from "lucide-react"
import { api } from "@/lib/api"

// Export types
type ExportType = "dxf" | "lists" | "checklist"
type ExportStatus = "idle" | "configuring" | "exporting" | "completed" | "error"

interface BatchExportJob {
  jobId: string
  status: string
  totalDrawings: number
  completedDrawings: number
  failedDrawings: number
  filePath?: string
  errors: string[]
}

interface BatchExportDialogProps {
  drawingIds: string[]
  drawingNames: string[]
  onClose: () => void
  showToast: (message: string) => void
}

export function BatchExportDialog({
  drawingIds,
  drawingNames,
  onClose,
  showToast,
}: BatchExportDialogProps) {
  const [exportType, setExportType] = useState<ExportType>("dxf")
  const [exportStatus, setExportStatus] = useState<ExportStatus>("configuring")
  const [exportJob, setExportJob] = useState<BatchExportJob | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // DXF export options
  const [paperSize, setPaperSize] = useState("A1")
  const [scale, setScale] = useState("1:50")
  const [includeConnections, setIncludeConnections] = useState(true)
  const [includeAnnotations, setIncludeAnnotations] = useState(true)
  const [includeTitleBlock, setIncludeTitleBlock] = useState(true)

  // Data lists export options
  const [listsFormat, setListsFormat] = useState<"xlsx" | "csv" | "pdf">("xlsx")
  const [selectedLists, setSelectedLists] = useState<string[]>(["equipment", "line", "instrument", "valve", "mto"])
  const [includeUnverified, setIncludeUnverified] = useState(false)

  // Validation checklist export options
  const [checklistFormat, setChecklistFormat] = useState<"pdf" | "xlsx" | "csv">("pdf")
  const [checklistIncludeUnverified, setChecklistIncludeUnverified] = useState(true)

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Poll for batch export job status
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await api.get(`/api/v1/exports/batch/${jobId}/status`)
      if (response.ok) {
        const data = await response.json()
        setExportJob({
          jobId: data.job_id,
          status: data.status,
          totalDrawings: data.total_drawings,
          completedDrawings: data.completed_drawings,
          failedDrawings: data.failed_drawings,
          filePath: data.file_path,
          errors: data.errors || [],
        })

        if (data.status === "completed") {
          setExportStatus("completed")
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
        } else if (data.status === "failed") {
          setExportStatus("error")
          setErrorMessage(data.errors?.join(", ") || "Batch export failed")
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
        }
      }
    } catch (err) {
      console.error("Poll status error:", err)
    }
  }, [])

  // Start batch export
  const startExport = useCallback(async () => {
    setExportStatus("exporting")
    setErrorMessage(null)

    try {
      const requestBody: Record<string, unknown> = {
        drawing_ids: drawingIds,
        export_type: exportType,
      }

      if (exportType === "dxf") {
        requestBody.paper_size = paperSize
        requestBody.scale = scale
        requestBody.include_connections = includeConnections
        requestBody.include_annotations = includeAnnotations
        requestBody.include_title_block = includeTitleBlock
      } else if (exportType === "lists") {
        requestBody.lists = selectedLists
        requestBody.format = listsFormat
        requestBody.include_unverified = includeUnverified
      } else if (exportType === "checklist") {
        requestBody.format = checklistFormat
        requestBody.include_unverified = checklistIncludeUnverified
      }

      const response = await api.post("/api/v1/exports/batch", requestBody)

      if (response.ok) {
        const data = await response.json()
        setExportJob({
          jobId: data.job_id,
          status: data.status,
          totalDrawings: data.total_drawings,
          completedDrawings: 0,
          failedDrawings: 0,
          errors: [],
        })

        // Start polling for job status
        pollIntervalRef.current = setInterval(() => {
          pollJobStatus(data.job_id)
        }, 1000)
      } else {
        const errorData = await response.json().catch(() => ({}))
        setExportStatus("error")
        setErrorMessage(errorData.detail || "Failed to start batch export")
      }
    } catch {
      setExportStatus("error")
      setErrorMessage("Failed to connect to server")
    }
  }, [
    drawingIds,
    exportType,
    paperSize,
    scale,
    includeConnections,
    includeAnnotations,
    includeTitleBlock,
    selectedLists,
    listsFormat,
    includeUnverified,
    checklistFormat,
    checklistIncludeUnverified,
    pollJobStatus,
  ])

  // Download completed batch export
  const downloadExport = useCallback(async () => {
    if (!exportJob?.jobId) {
      return
    }

    try {
      const response = await api.get(`/api/v1/exports/jobs/${exportJob.jobId}/download`)

      if (response.ok) {
        const blob = await response.blob()

        if (blob.size === 0) {
          showToast("Downloaded file is empty")
          return
        }

        const url = window.URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `batch_export_${drawingIds.length}_drawings.zip`

        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)

        showToast(`Batch export downloaded (${drawingIds.length} drawings)`)
        onClose()
      } else {
        const errorText = await response.text()
        showToast(`Failed to download export: ${errorText}`)
      }
    } catch (err) {
      console.error("Download error:", err)
      showToast("Failed to download export")
    }
  }, [exportJob, drawingIds.length, showToast, onClose])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  // Toggle list selection
  const toggleList = (list: string) => {
    setSelectedLists((prev) =>
      prev.includes(list)
        ? prev.filter((l) => l !== list)
        : [...prev, list]
    )
  }

  const progressPercent = exportJob
    ? Math.round(
        ((exportJob.completedDrawings + exportJob.failedDrawings) /
          exportJob.totalDrawings) *
          100
      )
    : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-background rounded-lg shadow-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Download className="h-5 w-5" />
            Batch Export ({drawingIds.length} drawings)
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ×
          </Button>
        </div>

        {/* Selected drawings summary */}
        {exportStatus === "configuring" && (
          <div className="mb-4 p-3 rounded-md border bg-muted/50">
            <p className="text-sm font-medium mb-1">Selected Drawings:</p>
            <p className="text-sm text-muted-foreground">
              {drawingNames.length <= 3
                ? drawingNames.join(", ")
                : `${drawingNames.slice(0, 3).join(", ")} and ${drawingNames.length - 3} more`}
            </p>
          </div>
        )}

        {/* Export Type Selection */}
        {exportStatus === "configuring" && (
          <>
            <div className="mb-6">
              <label className="text-sm font-medium mb-2 block">Export Type</label>
              <div className="grid grid-cols-3 gap-2">
                <Button
                  variant={exportType === "dxf" ? "default" : "outline"}
                  className="flex items-center justify-center gap-2 h-16"
                  onClick={() => setExportType("dxf")}
                >
                  <FileText className="h-5 w-5" />
                  <div className="text-left">
                    <div className="font-medium">AutoCAD</div>
                    <div className="text-xs opacity-70">DXF Format</div>
                  </div>
                </Button>
                <Button
                  variant={exportType === "lists" ? "default" : "outline"}
                  className="flex items-center justify-center gap-2 h-16"
                  onClick={() => setExportType("lists")}
                >
                  <FileSpreadsheet className="h-5 w-5" />
                  <div className="text-left">
                    <div className="font-medium">Data Lists</div>
                    <div className="text-xs opacity-70">Excel/CSV/PDF</div>
                  </div>
                </Button>
                <Button
                  variant={exportType === "checklist" ? "default" : "outline"}
                  className="flex items-center justify-center gap-2 h-16"
                  onClick={() => setExportType("checklist")}
                >
                  <ClipboardCheck className="h-5 w-5" />
                  <div className="text-left">
                    <div className="font-medium">Checklist</div>
                    <div className="text-xs opacity-70">Validation PDF</div>
                  </div>
                </Button>
              </div>
            </div>

            {/* DXF Export Options */}
            {exportType === "dxf" && (
              <div className="space-y-4 mb-6">
                <div className="rounded-md border p-3 bg-muted/50">
                  <p className="text-sm text-muted-foreground">
                    Exports all {drawingIds.length} drawings as <strong>DXF format</strong>.
                    All exports will be bundled into a single ZIP file.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-1 block">Paper Size</label>
                    <Select value={paperSize} onValueChange={setPaperSize}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="A0">A0 (1189 × 841 mm)</SelectItem>
                        <SelectItem value="A1">A1 (841 × 594 mm)</SelectItem>
                        <SelectItem value="A2">A2 (594 × 420 mm)</SelectItem>
                        <SelectItem value="A3">A3 (420 × 297 mm)</SelectItem>
                        <SelectItem value="A4">A4 (297 × 210 mm)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-1 block">Scale</label>
                    <Select value={scale} onValueChange={setScale}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1:25">1:25</SelectItem>
                        <SelectItem value="1:50">1:50</SelectItem>
                        <SelectItem value="1:100">1:100</SelectItem>
                        <SelectItem value="1:200">1:200</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium mb-1 block">Options</label>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="batchIncludeConnections"
                      checked={includeConnections}
                      onCheckedChange={(c) => setIncludeConnections(!!c)}
                    />
                    <label htmlFor="batchIncludeConnections" className="text-sm cursor-pointer">
                      Include piping connections
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="batchIncludeAnnotations"
                      checked={includeAnnotations}
                      onCheckedChange={(c) => setIncludeAnnotations(!!c)}
                    />
                    <label htmlFor="batchIncludeAnnotations" className="text-sm cursor-pointer">
                      Include text annotations
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="batchIncludeTitleBlock"
                      checked={includeTitleBlock}
                      onCheckedChange={(c) => setIncludeTitleBlock(!!c)}
                    />
                    <label htmlFor="batchIncludeTitleBlock" className="text-sm cursor-pointer">
                      Include title block
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Data Lists Export Options */}
            {exportType === "lists" && (
              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-sm font-medium mb-1 block">Format</label>
                  <Select value={listsFormat} onValueChange={(v: "xlsx" | "csv" | "pdf") => setListsFormat(v)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
                      <SelectItem value="csv">CSV (.csv)</SelectItem>
                      <SelectItem value="pdf">PDF (.pdf)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">Select Lists</label>
                  <div className="space-y-2">
                    {[
                      { value: "equipment", label: "Equipment List" },
                      { value: "line", label: "Line List" },
                      { value: "instrument", label: "Instrument List" },
                      { value: "valve", label: "Valve List" },
                      { value: "mto", label: "Material Take-Off (MTO)" },
                    ].map((list) => (
                      <div key={list.value} className="flex items-center gap-2">
                        <Checkbox
                          id={`batch-list-${list.value}`}
                          checked={selectedLists.includes(list.value)}
                          onCheckedChange={() => toggleList(list.value)}
                        />
                        <label htmlFor={`batch-list-${list.value}`} className="text-sm cursor-pointer">
                          {list.label}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Checkbox
                    id="batchIncludeUnverified"
                    checked={includeUnverified}
                    onCheckedChange={(c) => setIncludeUnverified(!!c)}
                  />
                  <label htmlFor="batchIncludeUnverified" className="text-sm cursor-pointer">
                    Include unverified items
                  </label>
                </div>
              </div>
            )}

            {/* Validation Checklist Export Options */}
            {exportType === "checklist" && (
              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-sm font-medium mb-1 block">Format</label>
                  <Select value={checklistFormat} onValueChange={(v: "pdf" | "xlsx" | "csv") => setChecklistFormat(v)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pdf">PDF (Printable)</SelectItem>
                      <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
                      <SelectItem value="csv">CSV (.csv)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="rounded-md border p-3 bg-muted/50">
                  <p className="text-sm text-muted-foreground">
                    Exports validation checklists for all {drawingIds.length} drawings,
                    bundled into a single ZIP file.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Checkbox
                    id="batchChecklistIncludeUnverified"
                    checked={checklistIncludeUnverified}
                    onCheckedChange={(c) => setChecklistIncludeUnverified(!!c)}
                  />
                  <label htmlFor="batchChecklistIncludeUnverified" className="text-sm cursor-pointer">
                    Include all items (verified and unverified)
                  </label>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={startExport}
                disabled={exportType === "lists" && selectedLists.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Export {drawingIds.length} Drawings
              </Button>
            </div>
          </>
        )}

        {/* Exporting Status */}
        {exportStatus === "exporting" && (
          <div className="py-8 text-center">
            <Loader2 className="h-10 w-10 animate-spin mx-auto mb-4 text-primary" />
            <p className="font-medium">Generating batch export...</p>
            {exportJob && (
              <>
                <p className="text-sm text-muted-foreground mt-1">
                  Processing {exportJob.completedDrawings + exportJob.failedDrawings} of {exportJob.totalDrawings} drawings
                </p>
                <div className="w-full bg-muted rounded-full h-2 mt-4">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {progressPercent}% complete
                </p>
              </>
            )}
          </div>
        )}

        {/* Completed Status */}
        {exportStatus === "completed" && (
          <div className="py-8 text-center">
            <CheckCircle className="h-10 w-10 mx-auto mb-4 text-green-500" />
            <p className="font-medium">Batch export ready!</p>
            {exportJob && (
              <p className="text-sm text-muted-foreground mt-1">
                Successfully exported {exportJob.completedDrawings} of {exportJob.totalDrawings} drawings
                {exportJob.failedDrawings > 0 && ` (${exportJob.failedDrawings} failed)`}
              </p>
            )}
            {exportJob && exportJob.errors.length > 0 && (
              <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-left">
                <p className="text-xs font-medium text-yellow-800">Warnings:</p>
                <ul className="text-xs text-yellow-700 mt-1">
                  {exportJob.errors.slice(0, 3).map((err, i) => (
                    <li key={i}>• {err}</li>
                  ))}
                  {exportJob.errors.length > 3 && (
                    <li>• and {exportJob.errors.length - 3} more...</li>
                  )}
                </ul>
              </div>
            )}
            <div className="flex justify-center gap-2 mt-6">
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              <Button onClick={downloadExport}>
                <Download className="h-4 w-4 mr-2" />
                Download ZIP
              </Button>
            </div>
          </div>
        )}

        {/* Error Status */}
        {exportStatus === "error" && (
          <div className="py-8 text-center">
            <AlertTriangle className="h-10 w-10 mx-auto mb-4 text-red-500" />
            <p className="font-medium">Batch export failed</p>
            <p className="text-sm text-muted-foreground mt-1">
              {errorMessage || "An unexpected error occurred."}
            </p>
            <div className="flex justify-center gap-2 mt-6">
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              <Button onClick={() => setExportStatus("configuring")}>
                Try Again
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
