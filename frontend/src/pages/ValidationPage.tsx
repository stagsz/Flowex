import { useState, useEffect, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { Document, Page, pdfjs } from "react-pdf"
import "react-pdf/dist/Page/AnnotationLayer.css"
import "react-pdf/dist/Page/TextLayer.css"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  ArrowLeft,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Download,
  Save,
  Undo,
  Redo,
  Search,
  CheckCircle,
  AlertTriangle,
  Filter,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface DetectedSymbol {
  id: string
  type: "equipment" | "instrument" | "valve" | "other"
  tag: string
  symbolClass: string
  confidence: number
  x: number
  y: number
  width: number
  height: number
  validated: boolean
}

interface SymbolSummary {
  total_symbols: number
  verified_symbols: number
  low_confidence_symbols: number
  total_texts: number
  verified_texts: number
}

export function ValidationPage() {
  const { drawingId } = useParams()
  const [zoom, setZoom] = useState(100)
  const [rotation, setRotation] = useState(0) // Default 0° - P&IDs are typically A1/A3 landscape
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [filterType, setFilterType] = useState("all")
  const [showLowConfidence] = useState(true)
  const [numPages, setNumPages] = useState<number | null>(null)
  const [pageNumber] = useState(1)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(true)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [symbols, setSymbols] = useState<DetectedSymbol[]>([])
  const [symbolsLoading, setSymbolsLoading] = useState(true)
  const [summary, setSummary] = useState<SymbolSummary | null>(null)
  const [editingTag, setEditingTag] = useState<string>("")

  // Drawing info from API
  const [drawing, setDrawing] = useState({
    id: drawingId,
    name: "Loading...",
    projectName: "",
  })

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // Fetch drawing details and PDF URL
  useEffect(() => {
    async function fetchDrawing() {
      try {
        setPdfLoading(true)
        setPdfError(null)

        const response = await fetch(`${apiUrl}/api/v1/drawings/${drawingId}`)
        if (response.ok) {
          const data = await response.json()
          setDrawing({
            id: data.id,
            name: data.original_filename,
            projectName: `Project ${data.project_id.slice(0, 8)}...`,
          })
          if (data.download_url) {
            setPdfUrl(data.download_url)
          } else {
            setPdfError("No PDF URL available for this drawing")
          }
        } else if (response.status === 401) {
          setPdfError("Authentication required. Please log in.")
        } else if (response.status === 404) {
          setPdfError("Drawing not found")
        } else {
          setPdfError("Could not load drawing")
        }
      } catch {
        setPdfError("Failed to connect to API")
      } finally {
        setPdfLoading(false)
      }
    }

    if (drawingId) {
      fetchDrawing()
    }
  }, [drawingId, apiUrl])

  // Fetch symbols and text annotations
  useEffect(() => {
    async function fetchSymbols() {
      try {
        setSymbolsLoading(true)

        const response = await fetch(`${apiUrl}/api/v1/drawings/${drawingId}/symbols`)
        if (response.ok) {
          const data = await response.json()

          // Transform API response to DetectedSymbol format
          const transformedSymbols: DetectedSymbol[] = data.symbols.map((s: {
            id: string
            category: string
            tag_number: string | null
            symbol_class: string
            confidence: number | null
            bbox_x: number
            bbox_y: number
            bbox_width: number
            bbox_height: number
            is_verified: boolean
          }) => ({
            id: s.id,
            type: s.category as "equipment" | "instrument" | "valve" | "other",
            tag: s.tag_number || s.symbol_class,
            symbolClass: s.symbol_class,
            confidence: s.confidence || 0,
            x: s.bbox_x,
            y: s.bbox_y,
            width: s.bbox_width,
            height: s.bbox_height,
            validated: s.is_verified,
          }))

          setSymbols(transformedSymbols)
          setSummary(data.summary)
        }
      } catch (err) {
        console.error("Failed to fetch symbols:", err)
      } finally {
        setSymbolsLoading(false)
      }
    }

    if (drawingId) {
      fetchSymbols()
    }
  }, [drawingId, apiUrl])

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages)
    setPdfLoading(false)
  }

  function onDocumentLoadError(error: Error) {
    setPdfError(`Failed to load PDF: ${error.message}`)
    setPdfLoading(false)
  }

  // Verify a symbol
  const verifySymbol = useCallback(async (symbolId: string) => {
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/drawings/${drawingId}/symbols/${symbolId}/verify`,
        { method: "POST" }
      )
      if (response.ok) {
        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, validated: true } : s)
        )
      }
    } catch (err) {
      console.error("Failed to verify symbol:", err)
    }
  }, [apiUrl, drawingId])

  // Update symbol tag
  const updateSymbolTag = useCallback(async (symbolId: string, newTag: string) => {
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/drawings/${drawingId}/symbols/${symbolId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tag_number: newTag }),
        }
      )
      if (response.ok) {
        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, tag: newTag } : s)
        )
      }
    } catch (err) {
      console.error("Failed to update symbol:", err)
    }
  }, [apiUrl, drawingId])

  // Delete symbol (soft delete)
  const deleteSymbol = useCallback(async (symbolId: string) => {
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/drawings/${drawingId}/symbols/${symbolId}`,
        { method: "DELETE" }
      )
      if (response.ok) {
        setSymbols(prev => prev.filter(s => s.id !== symbolId))
        setSelectedSymbol(null)
      }
    } catch (err) {
      console.error("Failed to delete symbol:", err)
    }
  }, [apiUrl, drawingId])

  const filteredSymbols = symbols.filter((symbol) => {
    const matchesSearch = symbol.tag.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === "all" || symbol.type === filterType
    const matchesConfidence = showLowConfidence || symbol.confidence >= 0.85
    return matchesSearch && matchesType && matchesConfidence
  })

  const validatedCount = summary?.verified_symbols ?? symbols.filter((s) => s.validated).length
  const lowConfidenceCount = summary?.low_confidence_symbols ?? symbols.filter((s) => s.confidence < 0.85).length
  const totalSymbols = summary?.total_symbols ?? symbols.length
  const validationProgress = totalSymbols > 0 ? (validatedCount / totalSymbols) * 100 : 0

  const typeColors: Record<string, string> = {
    equipment: "bg-blue-500",
    instrument: "bg-green-500",
    valve: "bg-orange-500",
    other: "bg-purple-500",
  }

  // Set editing tag when symbol is selected
  useEffect(() => {
    if (selectedSymbol) {
      const symbol = symbols.find(s => s.id === selectedSymbol)
      setEditingTag(symbol?.tag || "")
    }
  }, [selectedSymbol, symbols])

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to={`/drawings/${drawingId}`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-xl font-semibold">{drawing.name}</h1>
            <p className="text-sm text-muted-foreground">{drawing.projectName}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Undo className="h-4 w-4 mr-1" />
            Undo
          </Button>
          <Button variant="outline" size="sm">
            <Redo className="h-4 w-4 mr-1" />
            Redo
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
          <Button size="sm">
            <Save className="h-4 w-4 mr-1" />
            Save
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex gap-4 pt-4 overflow-hidden">
        {/* Left panel - Original PDF */}
        <div className="flex-1 flex flex-col border rounded-lg overflow-hidden">
          <div className="flex items-center justify-between p-2 border-b bg-muted/50">
            <span className="text-sm font-medium">Original P&ID</span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" onClick={() => setZoom(Math.max(25, zoom - 25))}>
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-sm w-12 text-center">{zoom}%</span>
              <Button variant="ghost" size="icon" onClick={() => setZoom(Math.min(200, zoom + 25))}>
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => setRotation((r) => (r + 90) % 360)} title={`Rotate (${rotation}°)`}>
                <RotateCw className="h-4 w-4" />
              </Button>
              <span className="text-xs text-muted-foreground w-8">{rotation}°</span>
            </div>
          </div>
          <div className="flex-1 overflow-auto bg-muted/20 p-4 flex items-center justify-center">
            <div
              className="bg-white shadow-lg relative transition-transform duration-300"
              style={{
                transform: `rotate(${rotation}deg)`,
                transformOrigin: 'center center',
              }}
            >
              {/* PDF Viewer */}
              {pdfLoading && (
                <div className="flex items-center justify-center p-20">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-muted-foreground">Loading PDF...</span>
                </div>
              )}

              {pdfError && !pdfUrl && (
                <div className="flex flex-col items-center justify-center p-20 text-muted-foreground">
                  <AlertTriangle className="h-12 w-12 mb-4 text-yellow-500" />
                  <p className="text-center">{pdfError}</p>
                  <p className="text-sm mt-2">Drawing ID: {drawingId}</p>
                </div>
              )}

              {pdfUrl && (
                <Document
                  file={pdfUrl}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={onDocumentLoadError}
                  loading={
                    <div className="flex items-center justify-center p-20">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  }
                >
                  <Page
                    pageNumber={pageNumber}
                    scale={zoom / 100}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                  />
                </Document>
              )}

              {numPages && numPages > 1 && (
                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-black/50 text-white px-2 py-1 rounded text-xs">
                  Page {pageNumber} of {numPages}
                </div>
              )}

              {/* Highlight selected symbol */}
              {selectedSymbol && pdfUrl && (
                <div
                  className="absolute border-2 border-primary bg-primary/10 pointer-events-none"
                  style={{
                    left: `${(symbols.find((s) => s.id === selectedSymbol)?.x || 0) * (zoom / 100)}px`,
                    top: `${(symbols.find((s) => s.id === selectedSymbol)?.y || 0) * (zoom / 100)}px`,
                    width: `${(symbols.find((s) => s.id === selectedSymbol)?.width || 0) * (zoom / 100)}px`,
                    height: `${(symbols.find((s) => s.id === selectedSymbol)?.height || 0) * (zoom / 100)}px`,
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Right panel - Extracted data */}
        <div className="w-96 flex flex-col border rounded-lg overflow-hidden">
          <div className="p-2 border-b bg-muted/50">
            <span className="text-sm font-medium">Extracted Components</span>
          </div>

          {/* Validation progress */}
          <div className="p-3 border-b">
            <div className="flex items-center justify-between text-sm mb-1">
              <span>Validation Progress</span>
              <span>{validatedCount}/{totalSymbols}</span>
            </div>
            <Progress value={validationProgress} className="h-2" />
            {lowConfidenceCount > 0 && (
              <p className="text-xs text-yellow-600 mt-1 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {lowConfidenceCount} items need review
              </p>
            )}
          </div>

          {/* Search and filters */}
          <div className="p-3 border-b space-y-2">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-8"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <div className="flex gap-1 flex-wrap">
                {["all", "equipment", "instrument", "valve", "other"].map((type) => (
                  <Button
                    key={type}
                    variant={filterType === type ? "secondary" : "ghost"}
                    size="sm"
                    className="h-6 text-xs"
                    onClick={() => setFilterType(type)}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Symbol list */}
          <div className="flex-1 overflow-auto">
            {symbolsLoading ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading symbols...</span>
              </div>
            ) : symbols.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-muted-foreground">
                <AlertTriangle className="h-8 w-8 mb-2" />
                <p>No symbols detected</p>
                <p className="text-xs mt-1">Process the drawing to detect symbols</p>
              </div>
            ) : filteredSymbols.length === 0 ? (
              <div className="flex items-center justify-center p-8 text-muted-foreground">
                <p>No symbols match the current filter</p>
              </div>
            ) : null}
            {filteredSymbols.map((symbol) => (
              <div
                key={symbol.id}
                onClick={() => setSelectedSymbol(symbol.id)}
                className={cn(
                  "p-3 border-b cursor-pointer transition-colors",
                  selectedSymbol === symbol.id
                    ? "bg-primary/5 border-l-2 border-l-primary"
                    : "hover:bg-muted/50"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={cn("w-2 h-2 rounded-full", typeColors[symbol.type])} />
                    <span className="font-medium">{symbol.tag}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {symbol.validated ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : symbol.confidence < 0.85 ? (
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    ) : null}
                    <span
                      className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        symbol.confidence >= 0.9
                          ? "bg-green-100 text-green-700"
                          : symbol.confidence >= 0.85
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                      )}
                    >
                      {Math.round(symbol.confidence * 100)}%
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                  <span className="capitalize">{symbol.type}</span>
                  <span>({symbol.x}, {symbol.y})</span>
                </div>
              </div>
            ))}
          </div>

          {/* Selected symbol editor */}
          {selectedSymbol && (
            <div className="p-3 border-t bg-muted/50">
              <h4 className="font-medium mb-2">Edit Component</h4>
              <div className="space-y-2">
                <div>
                  <label className="text-xs text-muted-foreground">Tag</label>
                  <Input
                    value={editingTag}
                    onChange={(e) => setEditingTag(e.target.value)}
                    onBlur={() => {
                      const symbol = symbols.find(s => s.id === selectedSymbol)
                      if (symbol && editingTag !== symbol.tag) {
                        updateSymbolTag(selectedSymbol, editingTag)
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        const symbol = symbols.find(s => s.id === selectedSymbol)
                        if (symbol && editingTag !== symbol.tag) {
                          updateSymbolTag(selectedSymbol, editingTag)
                        }
                      }
                    }}
                    className="h-8"
                  />
                </div>
                <div className="text-xs text-muted-foreground mb-2">
                  Class: {symbols.find(s => s.id === selectedSymbol)?.symbolClass}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => deleteSymbol(selectedSymbol)}
                  >
                    Delete
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => verifySymbol(selectedSymbol)}
                    disabled={symbols.find(s => s.id === selectedSymbol)?.validated}
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    {symbols.find(s => s.id === selectedSymbol)?.validated ? "Validated" : "Validate"}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
