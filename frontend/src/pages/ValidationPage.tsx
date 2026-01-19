import { useState } from "react"
import { useParams, Link } from "react-router-dom"
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
} from "lucide-react"
import { cn } from "@/lib/utils"

interface DetectedSymbol {
  id: string
  type: "equipment" | "instrument" | "valve" | "line"
  tag: string
  confidence: number
  x: number
  y: number
  width: number
  height: number
  validated: boolean
}

export function ValidationPage() {
  const { drawingId } = useParams()
  const [zoom, setZoom] = useState(100)
  const [rotation, setRotation] = useState(0) // Default 0° - P&IDs are typically A1/A3 landscape
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [filterType, setFilterType] = useState("all")
  const [showLowConfidence] = useState(true)

  // Mock data - would come from API
  const drawing = {
    id: drawingId,
    name: "P&ID-001-Rev3.pdf",
    projectName: "Refinery Unit A",
    imageUrl: "/placeholder-pid.png",
  }

  const symbols: DetectedSymbol[] = [
    { id: "1", type: "equipment", tag: "V-101", confidence: 0.98, x: 100, y: 150, width: 60, height: 80, validated: true },
    { id: "2", type: "equipment", tag: "P-201", confidence: 0.95, x: 250, y: 200, width: 50, height: 50, validated: true },
    { id: "3", type: "instrument", tag: "PT-101", confidence: 0.92, x: 180, y: 120, width: 30, height: 30, validated: false },
    { id: "4", type: "instrument", tag: "FT-201", confidence: 0.88, x: 300, y: 180, width: 30, height: 30, validated: false },
    { id: "5", type: "valve", tag: "XV-101", confidence: 0.75, x: 150, y: 250, width: 25, height: 25, validated: false },
    { id: "6", type: "valve", tag: "HV-201", confidence: 0.68, x: 280, y: 300, width: 25, height: 25, validated: false },
    { id: "7", type: "line", tag: '6"-P-101-A1', confidence: 0.91, x: 100, y: 100, width: 200, height: 10, validated: false },
    { id: "8", type: "equipment", tag: "E-301", confidence: 0.96, x: 400, y: 150, width: 80, height: 60, validated: false },
  ]

  const filteredSymbols = symbols.filter((symbol) => {
    const matchesSearch = symbol.tag.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === "all" || symbol.type === filterType
    const matchesConfidence = showLowConfidence || symbol.confidence >= 0.85
    return matchesSearch && matchesType && matchesConfidence
  })

  const validatedCount = symbols.filter((s) => s.validated).length
  const lowConfidenceCount = symbols.filter((s) => s.confidence < 0.85).length
  const validationProgress = (validatedCount / symbols.length) * 100

  const typeColors = {
    equipment: "bg-blue-500",
    instrument: "bg-green-500",
    valve: "bg-orange-500",
    line: "bg-purple-500",
  }

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
          <div className="flex-1 overflow-auto bg-muted/20 p-4">
            <div
              className="bg-white shadow-lg mx-auto relative transition-transform duration-300"
              style={{
                // A1/A3 aspect ratio (1.414:1) - landscape by default
                width: `${(rotation % 180 === 0 ? 840 : 594) * (zoom / 100)}px`,
                height: `${(rotation % 180 === 0 ? 594 : 840) * (zoom / 100)}px`,
                transform: `rotate(${rotation}deg)`,
                transformOrigin: 'center center',
              }}
            >
              {/* Placeholder for PDF viewer */}
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                <span>PDF Viewer</span>
              </div>
              {/* Highlight selected symbol */}
              {selectedSymbol && (
                <div
                  className="absolute border-2 border-primary bg-primary/10"
                  style={{
                    left: `${symbols.find((s) => s.id === selectedSymbol)?.x || 0}px`,
                    top: `${symbols.find((s) => s.id === selectedSymbol)?.y || 0}px`,
                    width: `${symbols.find((s) => s.id === selectedSymbol)?.width || 0}px`,
                    height: `${symbols.find((s) => s.id === selectedSymbol)?.height || 0}px`,
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
              <span>{validatedCount}/{symbols.length}</span>
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
                {["all", "equipment", "instrument", "valve", "line"].map((type) => (
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
                    value={symbols.find((s) => s.id === selectedSymbol)?.tag || ""}
                    className="h-8"
                  />
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    Delete
                  </Button>
                  <Button size="sm" className="flex-1">
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Validate
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
