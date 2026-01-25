import { useState, useEffect, useCallback } from "react"
import { Link, useSearchParams } from "react-router-dom"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Checkbox } from "@/components/ui/checkbox"
import {
  FileImage,
  Upload,
  Search,
  Filter,
  CheckCircle,
  Clock,
  AlertCircle,
  Eye,
  Download,
  MoreVertical,
  Loader2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { ExportDialog } from "@/components/export/ExportDialog"
import { BatchExportDialog } from "@/components/export/BatchExportDialog"

interface Drawing {
  id: string
  name: string
  projectName: string
  status: "uploaded" | "processing" | "review" | "complete" | "error"
  progress: number
  symbolsDetected: number
  createdAt: string
  processedAt?: string
}

type SortField = "name" | "date" | "status"

export function DrawingsPage() {
  const [searchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState(
    searchParams.get("status") || "all"
  )
  const [sortBy, setSortBy] = useState<SortField>("date")
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc")
  const [drawings, setDrawings] = useState<Drawing[]>([])
  const [loading, setLoading] = useState(true)
  const [exportDrawing, setExportDrawing] = useState<Drawing | null>(null)
  const [selectedDrawingIds, setSelectedDrawingIds] = useState<Set<string>>(new Set())
  const [showBatchExport, setShowBatchExport] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const showToast = useCallback((message: string) => setToast(message), [])

  // Auto-dismiss toast after 3 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Fetch drawings from API
  useEffect(() => {
    async function fetchDrawings() {
      try {
        // First fetch all projects, then get drawings for each
        const projectsResponse = await api.get("/api/v1/projects/")
        if (projectsResponse.ok) {
          const projects = await projectsResponse.json()
          const allDrawings: Drawing[] = []

          for (const project of projects) {
            const drawingsResponse = await api.get(`/api/v1/drawings/project/${project.id}`)
            if (drawingsResponse.ok) {
              const projectDrawings = await drawingsResponse.json()
              for (const d of projectDrawings) {
                allDrawings.push({
                  id: d.id,
                  name: d.original_filename,
                  projectName: project.name,
                  status: d.status as Drawing["status"],
                  progress: d.progress_percentage ?? 0,  // Use real progress from API
                  symbolsDetected: 0, // Would come from symbols API
                  createdAt: new Date(d.created_at).toLocaleDateString(),
                  processedAt: d.processing_completed_at
                    ? new Date(d.processing_completed_at).toLocaleDateString()
                    : undefined,
                })
              }
            }
          }
          setDrawings(allDrawings)
        } else {
          // Fallback to empty if API unavailable
          setDrawings([])
        }
      } catch {
        // API error - show empty state
        setDrawings([])
      } finally {
        setLoading(false)
      }
    }
    fetchDrawings()
  }, [])

  const statusConfig = {
    uploaded: {
      icon: Clock,
      label: "Uploaded",
      className: "text-yellow-500",
    },
    processing: {
      icon: Clock,
      label: "Processing",
      className: "text-blue-500 animate-pulse",
    },
    review: {
      icon: Eye,
      label: "Review",
      className: "text-orange-500",
    },
    complete: {
      icon: CheckCircle,
      label: "Complete",
      className: "text-green-500",
    },
    error: {
      icon: AlertCircle,
      label: "Error",
      className: "text-red-500",
    },
  }

  // Status order for sorting: uploaded -> processing -> review -> complete -> error
  const statusOrder: Record<Drawing["status"], number> = {
    uploaded: 0,
    processing: 1,
    review: 2,
    complete: 3,
    error: 4,
  }

  const filteredDrawings = drawings
    .filter((drawing) => {
      const matchesSearch =
        drawing.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        drawing.projectName.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus =
        statusFilter === "all" || drawing.status === statusFilter
      return matchesSearch && matchesStatus
    })
    .sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case "name":
          comparison = a.name.localeCompare(b.name)
          break
        case "date":
          // Sort by processedAt first, then createdAt
          const dateA = a.processedAt || a.createdAt
          const dateB = b.processedAt || b.createdAt
          comparison = dateA.localeCompare(dateB)
          break
        case "status":
          comparison = statusOrder[a.status] - statusOrder[b.status]
          break
      }
      return sortDirection === "asc" ? comparison : -comparison
    })

  // Get exportable drawings (complete or review status)
  const exportableDrawings = filteredDrawings.filter(
    (d) => d.status === "complete" || d.status === "review"
  )
  const exportableIds = new Set(exportableDrawings.map((d) => d.id))

  // Selected drawings that are exportable
  const selectedExportableIds = [...selectedDrawingIds].filter((id) =>
    exportableIds.has(id)
  )

  // Check if all exportable drawings are selected
  const allExportableSelected =
    exportableDrawings.length > 0 &&
    exportableDrawings.every((d) => selectedDrawingIds.has(d.id))

  // Toggle selection for a single drawing
  const toggleSelection = (id: string) => {
    setSelectedDrawingIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  // Toggle select all exportable drawings
  const toggleSelectAll = () => {
    if (allExportableSelected) {
      // Deselect all
      setSelectedDrawingIds(new Set())
    } else {
      // Select all exportable drawings
      setSelectedDrawingIds(new Set(exportableDrawings.map((d) => d.id)))
    }
  }

  // Clear selection
  const clearSelection = () => {
    setSelectedDrawingIds(new Set())
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Drawings</h1>
          <p className="text-muted-foreground">
            View and manage your P&ID drawings
          </p>
        </div>
        <Button asChild>
          <Link to="/upload">
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Link>
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search drawings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <div className="flex gap-1">
              {["all", "uploaded", "processing", "review", "complete", "error"].map(
                (status) => (
                  <Button
                    key={status}
                    variant={statusFilter === status ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setStatusFilter(status)}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </Button>
                )
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
            <Select
              value={sortBy}
              onValueChange={(value: SortField) => setSortBy(value)}
            >
              <SelectTrigger className="h-8 w-[100px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="date">Date</SelectItem>
                <SelectItem value="status">Status</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setSortDirection(d => d === "asc" ? "desc" : "asc")}
              title={sortDirection === "asc" ? "Sort ascending" : "Sort descending"}
            >
              {sortDirection === "asc" ? (
                <ArrowUp className="h-4 w-4" />
              ) : (
                <ArrowDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Bulk Action Bar - shown when drawings are selected */}
      {selectedExportableIds.length > 0 && (
        <div className="flex items-center justify-between bg-muted/50 border rounded-lg px-4 py-3">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">
              {selectedExportableIds.length} drawing
              {selectedExportableIds.length === 1 ? "" : "s"} selected
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearSelection}
              className="h-8"
            >
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
          </div>
          <Button
            onClick={() => setShowBatchExport(true)}
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Export All ({selectedExportableIds.length})
          </Button>
        </div>
      )}

      {loading ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
            <h3 className="text-lg font-semibold">Loading drawings...</h3>
          </CardContent>
        </Card>
      ) : filteredDrawings.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileImage className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">No drawings found</h3>
            <p className="text-muted-foreground text-center max-w-sm mt-1">
              {searchQuery || statusFilter !== "all"
                ? "Try a different search or filter"
                : "Upload your first P&ID drawing to get started"}
            </p>
            {!searchQuery && statusFilter === "all" && (
              <Button className="mt-4" asChild>
                <Link to="/upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Drawing
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {/* Select All Header */}
          {exportableDrawings.length > 0 && (
            <div className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground">
              <Checkbox
                checked={allExportableSelected}
                onCheckedChange={toggleSelectAll}
                aria-label="Select all exportable drawings"
              />
              <span>
                {allExportableSelected
                  ? "Deselect all"
                  : `Select all exportable (${exportableDrawings.length})`}
              </span>
            </div>
          )}
          {filteredDrawings.map((drawing) => {
            const StatusIcon = statusConfig[drawing.status].icon
            const isExportable =
              drawing.status === "complete" || drawing.status === "review"
            const isSelected = selectedDrawingIds.has(drawing.id)
            return (
              <Card
                key={drawing.id}
                className={cn(isSelected && "ring-2 ring-primary")}
              >
                <CardContent className="flex items-center gap-4 p-4">
                  {/* Selection checkbox - only for exportable drawings */}
                  <div className="flex-shrink-0">
                    {isExportable ? (
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleSelection(drawing.id)}
                        aria-label={`Select ${drawing.name}`}
                      />
                    ) : (
                      <div className="w-4 h-4" /> // Spacer for alignment
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    <FileImage className="h-8 w-8 text-muted-foreground" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/drawings/${drawing.id}`}
                        className="font-medium hover:underline truncate"
                      >
                        {drawing.name}
                      </Link>
                      <StatusIcon
                        className={cn(
                          "h-4 w-4 flex-shrink-0",
                          statusConfig[drawing.status].className
                        )}
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {drawing.projectName}
                    </p>
                    {(drawing.status === "processing" || drawing.status === "review") && (
                      <div className="mt-2 flex items-center gap-2">
                        <Progress value={drawing.progress} className="h-1 flex-1" />
                        <span className="text-xs text-muted-foreground w-8">
                          {drawing.progress}%
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="hidden md:block text-right">
                    {(drawing.status === "complete" || drawing.status === "review") && (
                      <p className="text-sm font-medium">
                        {drawing.symbolsDetected} symbols
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {drawing.processedAt || drawing.createdAt}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* View button always available */}
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/drawings/${drawing.id}/validate`}>
                        <Eye className="h-4 w-4" />
                      </Link>
                    </Button>
                    {(drawing.status === "complete" || drawing.status === "review") && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setExportDrawing(drawing)}
                        title="Export drawing"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link to={`/drawings/${drawing.id}`}>
                            View Details
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link to={`/drawings/${drawing.id}/validate`}>
                            View / Validate
                          </Link>
                        </DropdownMenuItem>
                        {drawing.status === "error" && (
                          <DropdownMenuItem>Retry Processing</DropdownMenuItem>
                        )}
                        <DropdownMenuItem className="text-destructive">
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Export Dialog */}
      {exportDrawing && (
        <ExportDialog
          drawingId={exportDrawing.id}
          drawingName={exportDrawing.name}
          onClose={() => setExportDrawing(null)}
          showToast={showToast}
        />
      )}

      {/* Batch Export Dialog */}
      {showBatchExport && (
        <BatchExportDialog
          drawingIds={selectedExportableIds}
          onClose={() => setShowBatchExport(false)}
          showToast={showToast}
          onExportComplete={() => {
            setShowBatchExport(false)
            clearSelection()
          }}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 bg-foreground text-background px-4 py-2 rounded-md shadow-lg animate-in fade-in slide-in-from-bottom-4">
          {toast}
          <button
            className="ml-4 text-background/70 hover:text-background"
            onClick={() => setToast(null)}
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}
