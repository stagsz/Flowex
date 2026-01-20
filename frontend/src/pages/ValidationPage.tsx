import { useState, useEffect, useCallback, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import { Document, Page, pdfjs } from "react-pdf"
import "react-pdf/dist/Page/AnnotationLayer.css"
import "react-pdf/dist/Page/TextLayer.css"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Checkbox } from "@/components/ui/checkbox"
import {
  ArrowLeft,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Download,
  Undo,
  Redo,
  Search,
  CheckCircle,
  CheckCircle2,
  AlertTriangle,
  Filter,
  Loader2,
  Keyboard,
  Cloud,
  CloudOff,
  Check,
  Square,
  CheckSquare,
  Flag,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

// Save status types
type SaveStatus = "idle" | "saving" | "saved" | "error"

// Undo/Redo action types
interface EditAction {
  type: "verify" | "delete" | "update_tag" | "bulk_verify" | "flag" | "bulk_flag"
  symbolId: string
  previousState: DetectedSymbol | null
  newState: DetectedSymbol | null
  // For bulk operations
  symbolIds?: string[]
  previousStates?: DetectedSymbol[]
}

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
  flagged: boolean
}

interface SymbolSummary {
  total_symbols: number
  verified_symbols: number
  flagged_symbols: number
  low_confidence_symbols: number
  total_texts: number
  verified_texts: number
}

// Toast notification component
function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 2000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className="fixed bottom-4 right-4 z-50 bg-foreground text-background px-4 py-2 rounded-md shadow-lg animate-in slide-in-from-bottom-2 fade-in duration-200">
      {message}
    </div>
  )
}

// Save status indicator component
function SaveStatusIndicator({
  status,
  lastSavedAt,
  formatLastSaved
}: {
  status: SaveStatus
  lastSavedAt: Date | null
  formatLastSaved: (date: Date | null) => string
}) {
  if (status === "idle" && !lastSavedAt) {
    return null
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      {status === "saving" && (
        <>
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          <span className="text-muted-foreground">Saving...</span>
        </>
      )}
      {status === "saved" && (
        <>
          <Check className="h-4 w-4 text-green-500" />
          <span className="text-green-600">Saved</span>
        </>
      )}
      {status === "error" && (
        <>
          <CloudOff className="h-4 w-4 text-red-500" />
          <span className="text-red-600">Save failed</span>
        </>
      )}
      {status === "idle" && lastSavedAt && (
        <>
          <Cloud className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">Saved {formatLastSaved(lastSavedAt)}</span>
        </>
      )}
    </div>
  )
}

// Keyboard shortcuts help dialog
function KeyboardShortcutsHelp({ onClose }: { onClose: () => void }) {
  const shortcuts = [
    { key: "V", action: "Verify selected item(s)" },
    { key: "F", action: "Flag selected item(s) for review" },
    { key: "Ctrl + A", action: "Select all items" },
    { key: "Delete / Backspace", action: "Delete selected item" },
    { key: "Ctrl + Z", action: "Undo last action" },
    { key: "Ctrl + Y", action: "Redo last action" },
    { key: "Ctrl + S", action: "Show save status (auto-saved)" },
    { key: "+ / =", action: "Zoom in" },
    { key: "- / _", action: "Zoom out" },
    { key: "Tab", action: "Select next item" },
    { key: "Shift + Tab", action: "Select previous item" },
    { key: "Space", action: "Toggle checkbox selection" },
    { key: "Escape", action: "Clear selection / Close help" },
    { key: "?", action: "Show this help" },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-background rounded-lg shadow-xl p-6 max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            Keyboard Shortcuts
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}>×</Button>
        </div>
        <div className="space-y-2">
          {shortcuts.map(({ key, action }) => (
            <div key={key} className="flex items-center justify-between py-1 border-b border-border/50 last:border-0">
              <kbd className="px-2 py-1 bg-muted rounded text-sm font-mono">{key}</kbd>
              <span className="text-sm text-muted-foreground">{action}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function ValidationPage() {
  const { drawingId } = useParams()
  const [zoom, setZoom] = useState(50) // Start smaller for large P&ID drawings
  const [rotation, setRotation] = useState(0) // Default 0° - P&IDs are typically A1/A3 landscape
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [selectedSymbolIds, setSelectedSymbolIds] = useState<Set<string>>(new Set())
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

  // Undo/Redo state
  const [undoStack, setUndoStack] = useState<EditAction[]>([])
  const [redoStack, setRedoStack] = useState<EditAction[]>([])
  const maxUndoLevels = 20

  // Toast notification state
  const [toast, setToast] = useState<string | null>(null)
  const showToast = useCallback((message: string) => setToast(message), [])

  // Mark save as started (show "Saving..." indicator)
  const markSaving = useCallback(() => {
    setSaveStatus("saving")
    // Clear any existing timeout to reset the "saved" duration
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
  }, [])

  // Mark save as completed (show "Saved" then fade to idle)
  const markSaved = useCallback(() => {
    setSaveStatus("saved")
    setLastSavedAt(new Date())
    // Reset to idle after 3 seconds
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    saveTimeoutRef.current = setTimeout(() => {
      setSaveStatus("idle")
    }, 3000)
  }, [])

  // Mark save as failed
  const markSaveError = useCallback(() => {
    setSaveStatus("error")
    // Reset to idle after 5 seconds
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    saveTimeoutRef.current = setTimeout(() => {
      setSaveStatus("idle")
    }, 5000)
  }, [])

  // Keyboard shortcuts help
  const [showHelp, setShowHelp] = useState(false)

  // Auto-save status tracking
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle")
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const autoSaveIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Ref for focus management
  const containerRef = useRef<HTMLDivElement>(null)

  // Drawing info from API
  const [drawing, setDrawing] = useState({
    id: drawingId,
    name: "Loading...",
    projectName: "",
  })

  // Fetch drawing details and PDF URL
  useEffect(() => {
    async function fetchDrawing() {
      try {
        setPdfLoading(true)
        setPdfError(null)

        const response = await api.get(`/api/v1/drawings/${drawingId}`)
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
  }, [drawingId])

  // Fetch symbols and text annotations
  useEffect(() => {
    async function fetchSymbols() {
      try {
        setSymbolsLoading(true)

        const response = await api.get(`/api/v1/drawings/${drawingId}/symbols`)
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
            is_flagged: boolean
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
            flagged: s.is_flagged,
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
  }, [drawingId])

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages)
    setPdfLoading(false)
  }

  function onDocumentLoadError(error: Error) {
    setPdfError(`Failed to load PDF: ${error.message}`)
    setPdfLoading(false)
  }

  // Push action to undo stack
  const pushToUndoStack = useCallback((action: EditAction) => {
    setUndoStack(prev => {
      const newStack = [...prev, action]
      // Keep only last N actions
      return newStack.slice(-maxUndoLevels)
    })
    // Clear redo stack on new action
    setRedoStack([])
  }, [maxUndoLevels])

  // Verify a symbol
  const verifySymbol = useCallback(async (symbolId: string, skipUndo = false) => {
    const symbol = symbols.find(s => s.id === symbolId)
    if (!symbol || symbol.validated) return

    markSaving()
    try {
      const response = await api.post(
        `/api/v1/drawings/${drawingId}/symbols/${symbolId}/verify`
      )
      if (response.ok) {
        const previousState = { ...symbol }
        const newState = { ...symbol, validated: true }

        if (!skipUndo) {
          pushToUndoStack({
            type: "verify",
            symbolId,
            previousState,
            newState,
          })
        }

        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, validated: true } : s)
        )
        markSaved()
        showToast(`Verified: ${symbol.tag}`)
      } else {
        markSaveError()
        showToast("Failed to verify symbol")
      }
    } catch (err) {
      console.error("Failed to verify symbol:", err)
      markSaveError()
      showToast("Failed to verify symbol")
    }
  }, [drawingId, symbols, pushToUndoStack, showToast, markSaving, markSaved, markSaveError])

  // Bulk verify multiple symbols
  const bulkVerifySymbols = useCallback(async (symbolIds: string[]) => {
    // Filter to only unverified symbols
    const unverifiedIds = symbolIds.filter(id => {
      const symbol = symbols.find(s => s.id === id)
      return symbol && !symbol.validated
    })

    if (unverifiedIds.length === 0) {
      showToast("All selected items are already verified")
      return
    }

    markSaving()
    try {
      const response = await api.post(
        `/api/v1/drawings/${drawingId}/symbols/bulk-verify`,
        { symbol_ids: unverifiedIds }
      )
      if (response.ok) {
        const data = await response.json()

        // Store previous states for undo
        const previousStates = unverifiedIds
          .map(id => symbols.find(s => s.id === id))
          .filter((s): s is DetectedSymbol => s !== undefined)

        // Push bulk action to undo stack
        pushToUndoStack({
          type: "bulk_verify",
          symbolId: "", // Not used for bulk
          previousState: null,
          newState: null,
          symbolIds: data.verified_ids,
          previousStates,
        })

        // Update local state
        setSymbols(prev =>
          prev.map(s => data.verified_ids.includes(s.id) ? { ...s, validated: true } : s)
        )

        markSaved()
        showToast(`Verified ${data.verified_count} item${data.verified_count !== 1 ? 's' : ''}`)

        // Clear selection after bulk verify
        setSelectedSymbolIds(new Set())
      } else {
        markSaveError()
        showToast("Failed to verify symbols")
      }
    } catch (err) {
      console.error("Failed to bulk verify symbols:", err)
      markSaveError()
      showToast("Failed to verify symbols")
    }
  }, [drawingId, symbols, pushToUndoStack, showToast, markSaving, markSaved, markSaveError])

  // Bulk unverify symbols (for undo)
  const bulkUnverifySymbols = useCallback(async (symbolIds: string[]) => {
    markSaving()
    try {
      // Unverify each symbol via PATCH
      for (const symbolId of symbolIds) {
        await api.patch(
          `/api/v1/drawings/${drawingId}/symbols/${symbolId}`,
          { is_verified: false }
        )
      }
      setSymbols(prev =>
        prev.map(s => symbolIds.includes(s.id) ? { ...s, validated: false } : s)
      )
      markSaved()
    } catch (err) {
      console.error("Failed to unverify symbols:", err)
      markSaveError()
    }
  }, [drawingId, markSaving, markSaved, markSaveError])

  // Flag a symbol for review
  const flagSymbol = useCallback(async (symbolId: string, skipUndo = false) => {
    const symbol = symbols.find(s => s.id === symbolId)
    if (!symbol || symbol.flagged) return

    markSaving()
    try {
      const response = await api.post(
        `/api/v1/drawings/${drawingId}/symbols/${symbolId}/flag`
      )
      if (response.ok) {
        const previousState = { ...symbol }
        const newState = { ...symbol, flagged: true }

        if (!skipUndo) {
          pushToUndoStack({
            type: "flag",
            symbolId,
            previousState,
            newState,
          })
        }

        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, flagged: true } : s)
        )
        markSaved()
        showToast(`Flagged: ${symbol.tag}`)
      } else {
        markSaveError()
        showToast("Failed to flag symbol")
      }
    } catch (err) {
      console.error("Failed to flag symbol:", err)
      markSaveError()
      showToast("Failed to flag symbol")
    }
  }, [drawingId, symbols, pushToUndoStack, showToast, markSaving, markSaved, markSaveError])

  // Unflag a symbol (for undo)
  const unflagSymbol = useCallback(async (symbolId: string) => {
    markSaving()
    try {
      const response = await api.post(
        `/api/v1/drawings/${drawingId}/symbols/${symbolId}/unflag`
      )
      if (response.ok) {
        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, flagged: false } : s)
        )
        markSaved()
      } else {
        markSaveError()
      }
    } catch (err) {
      console.error("Failed to unflag symbol:", err)
      markSaveError()
    }
  }, [drawingId, markSaving, markSaved, markSaveError])

  // Bulk flag multiple symbols
  const bulkFlagSymbols = useCallback(async (symbolIds: string[]) => {
    // Filter to only unflagged symbols
    const unflaggedIds = symbolIds.filter(id => {
      const symbol = symbols.find(s => s.id === id)
      return symbol && !symbol.flagged
    })

    if (unflaggedIds.length === 0) {
      showToast("All selected items are already flagged")
      return
    }

    markSaving()
    try {
      const response = await api.post(
        `/api/v1/drawings/${drawingId}/symbols/bulk-flag`,
        { symbol_ids: unflaggedIds }
      )
      if (response.ok) {
        const data = await response.json()

        // Store previous states for undo
        const previousStates = unflaggedIds
          .map(id => symbols.find(s => s.id === id))
          .filter((s): s is DetectedSymbol => s !== undefined)

        // Push bulk action to undo stack
        pushToUndoStack({
          type: "bulk_flag",
          symbolId: "", // Not used for bulk
          previousState: null,
          newState: null,
          symbolIds: data.flagged_ids,
          previousStates,
        })

        // Update local state
        setSymbols(prev =>
          prev.map(s => data.flagged_ids.includes(s.id) ? { ...s, flagged: true } : s)
        )

        markSaved()
        showToast(`Flagged ${data.flagged_count} item${data.flagged_count !== 1 ? 's' : ''} for review`)

        // Clear selection after bulk flag
        setSelectedSymbolIds(new Set())
      } else {
        markSaveError()
        showToast("Failed to flag symbols")
      }
    } catch (err) {
      console.error("Failed to bulk flag symbols:", err)
      markSaveError()
      showToast("Failed to flag symbols")
    }
  }, [drawingId, symbols, pushToUndoStack, showToast, markSaving, markSaved, markSaveError])

  // Bulk unflag symbols (for undo)
  const bulkUnflagSymbols = useCallback(async (symbolIds: string[]) => {
    markSaving()
    try {
      await api.post(
        `/api/v1/drawings/${drawingId}/symbols/bulk-unflag`,
        { symbol_ids: symbolIds }
      )
      setSymbols(prev =>
        prev.map(s => symbolIds.includes(s.id) ? { ...s, flagged: false } : s)
      )
      markSaved()
    } catch (err) {
      console.error("Failed to unflag symbols:", err)
      markSaveError()
    }
  }, [drawingId, markSaving, markSaved, markSaveError])

  // Toggle selection of a symbol (for checkbox click)
  const toggleSymbolSelection = useCallback((symbolId: string) => {
    setSelectedSymbolIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(symbolId)) {
        newSet.delete(symbolId)
      } else {
        newSet.add(symbolId)
      }
      return newSet
    })
  }, [])

  // Select all filtered symbols - takes the current list as parameter
  const selectAllSymbols = useCallback((symbolList: DetectedSymbol[]) => {
    setSelectedSymbolIds(new Set(symbolList.map(s => s.id)))
  }, [])

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedSymbolIds(new Set())
    setSelectedSymbol(null)
  }, [])

  // Unverify a symbol (for undo)
  const unverifySymbol = useCallback(async (symbolId: string) => {
    markSaving()
    try {
      const response = await api.patch(
        `/api/v1/drawings/${drawingId}/symbols/${symbolId}`,
        { is_verified: false }
      )
      if (response.ok) {
        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, validated: false } : s)
        )
        markSaved()
      } else {
        markSaveError()
      }
    } catch (err) {
      console.error("Failed to unverify symbol:", err)
      markSaveError()
    }
  }, [drawingId, markSaving, markSaved, markSaveError])

  // Update symbol tag
  const updateSymbolTag = useCallback(async (symbolId: string, newTag: string, skipUndo = false) => {
    const symbol = symbols.find(s => s.id === symbolId)
    if (!symbol || symbol.tag === newTag) return

    markSaving()
    try {
      const response = await api.patch(
        `/api/v1/drawings/${drawingId}/symbols/${symbolId}`,
        { tag_number: newTag }
      )
      if (response.ok) {
        if (!skipUndo) {
          pushToUndoStack({
            type: "update_tag",
            symbolId,
            previousState: { ...symbol },
            newState: { ...symbol, tag: newTag },
          })
        }

        setSymbols(prev =>
          prev.map(s => s.id === symbolId ? { ...s, tag: newTag } : s)
        )
        markSaved()
      } else {
        markSaveError()
        showToast("Failed to update tag")
      }
    } catch (err) {
      console.error("Failed to update symbol:", err)
      markSaveError()
      showToast("Failed to update tag")
    }
  }, [drawingId, symbols, pushToUndoStack, showToast, markSaving, markSaved, markSaveError])

  // Delete symbol (soft delete)
  const deleteSymbol = useCallback(async (symbolId: string, skipUndo = false) => {
    const symbol = symbols.find(s => s.id === symbolId)
    if (!symbol) return

    markSaving()
    try {
      const response = await api.delete(
        `/api/v1/drawings/${drawingId}/symbols/${symbolId}`
      )
      if (response.ok) {
        if (!skipUndo) {
          pushToUndoStack({
            type: "delete",
            symbolId,
            previousState: { ...symbol },
            newState: null,
          })
        }

        setSymbols(prev => prev.filter(s => s.id !== symbolId))
        setSelectedSymbol(null)
        markSaved()
        showToast(`Deleted: ${symbol.tag}`)
      } else {
        markSaveError()
        showToast("Failed to delete symbol")
      }
    } catch (err) {
      console.error("Failed to delete symbol:", err)
      markSaveError()
      showToast("Failed to delete symbol")
    }
  }, [drawingId, symbols, pushToUndoStack, showToast, markSaving, markSaved, markSaveError])

  // Restore a deleted symbol (for undo)
  const restoreSymbol = useCallback(async (symbol: DetectedSymbol) => {
    markSaving()
    try {
      // Re-create the symbol via API
      const response = await api.post(
        `/api/v1/drawings/${drawingId}/symbols`,
        {
          symbol_class: symbol.symbolClass,
          category: symbol.type,
          tag_number: symbol.tag,
          bbox_x: symbol.x,
          bbox_y: symbol.y,
          bbox_width: symbol.width,
          bbox_height: symbol.height,
          confidence: symbol.confidence,
          is_verified: symbol.validated,
        }
      )
      if (response.ok) {
        const data = await response.json()
        // Add symbol back with new ID from API
        setSymbols(prev => [...prev, {
          ...symbol,
          id: data.id || symbol.id,
        }])
        markSaved()
      } else {
        markSaveError()
        showToast("Failed to restore symbol")
      }
    } catch (err) {
      console.error("Failed to restore symbol:", err)
      markSaveError()
      showToast("Failed to restore symbol")
    }
  }, [drawingId, showToast, markSaving, markSaved, markSaveError])

  // Undo last action
  const undo = useCallback(async () => {
    if (undoStack.length === 0) {
      showToast("Nothing to undo")
      return
    }

    const action = undoStack[undoStack.length - 1]
    setUndoStack(prev => prev.slice(0, -1))

    switch (action.type) {
      case "verify":
        if (action.previousState) {
          await unverifySymbol(action.symbolId)
          showToast("Undone: verification")
        }
        break
      case "bulk_verify":
        if (action.symbolIds && action.symbolIds.length > 0) {
          await bulkUnverifySymbols(action.symbolIds)
          showToast(`Undone: bulk verification (${action.symbolIds.length} items)`)
        }
        break
      case "delete":
        if (action.previousState) {
          await restoreSymbol(action.previousState)
          showToast("Undone: delete")
        }
        break
      case "update_tag":
        if (action.previousState) {
          await updateSymbolTag(action.symbolId, action.previousState.tag, true)
          showToast("Undone: tag change")
        }
        break
      case "flag":
        if (action.previousState) {
          await unflagSymbol(action.symbolId)
          showToast("Undone: flag")
        }
        break
      case "bulk_flag":
        if (action.symbolIds && action.symbolIds.length > 0) {
          await bulkUnflagSymbols(action.symbolIds)
          showToast(`Undone: bulk flag (${action.symbolIds.length} items)`)
        }
        break
    }

    // Push to redo stack
    setRedoStack(prev => [...prev, action])
  }, [undoStack, unverifySymbol, bulkUnverifySymbols, unflagSymbol, bulkUnflagSymbols, restoreSymbol, updateSymbolTag, showToast])

  // Redo last undone action
  const redo = useCallback(async () => {
    if (redoStack.length === 0) {
      showToast("Nothing to redo")
      return
    }

    const action = redoStack[redoStack.length - 1]
    setRedoStack(prev => prev.slice(0, -1))

    switch (action.type) {
      case "verify":
        await verifySymbol(action.symbolId, true)
        showToast("Redone: verification")
        break
      case "bulk_verify":
        if (action.symbolIds && action.symbolIds.length > 0) {
          // Re-verify all symbols in the bulk action
          await api.post(
            `/api/v1/drawings/${drawingId}/symbols/bulk-verify`,
            { symbol_ids: action.symbolIds }
          )
          setSymbols(prev =>
            prev.map(s => action.symbolIds?.includes(s.id) ? { ...s, validated: true } : s)
          )
          showToast(`Redone: bulk verification (${action.symbolIds.length} items)`)
        }
        break
      case "delete":
        await deleteSymbol(action.symbolId, true)
        showToast("Redone: delete")
        break
      case "update_tag":
        if (action.newState) {
          await updateSymbolTag(action.symbolId, action.newState.tag, true)
          showToast("Redone: tag change")
        }
        break
      case "flag":
        await flagSymbol(action.symbolId, true)
        showToast("Redone: flag")
        break
      case "bulk_flag":
        if (action.symbolIds && action.symbolIds.length > 0) {
          // Re-flag all symbols in the bulk action
          await api.post(
            `/api/v1/drawings/${drawingId}/symbols/bulk-flag`,
            { symbol_ids: action.symbolIds }
          )
          setSymbols(prev =>
            prev.map(s => action.symbolIds?.includes(s.id) ? { ...s, flagged: true } : s)
          )
          showToast(`Redone: bulk flag (${action.symbolIds.length} items)`)
        }
        break
    }

    // Push back to undo stack
    setUndoStack(prev => [...prev, action])
  }, [drawingId, redoStack, verifySymbol, flagSymbol, deleteSymbol, updateSymbolTag, showToast])

  const filteredSymbols = symbols.filter((symbol) => {
    const matchesSearch = symbol.tag.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === "all" || symbol.type === filterType
    const matchesConfidence = showLowConfidence || symbol.confidence >= 0.85
    return matchesSearch && matchesType && matchesConfidence
  })

  const validatedCount = summary?.verified_symbols ?? symbols.filter((s) => s.validated).length
  const flaggedCount = summary?.flagged_symbols ?? symbols.filter((s) => s.flagged).length
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

  // Navigate to next/previous symbol in filtered list
  const selectNextSymbol = useCallback(() => {
    if (filteredSymbols.length === 0) return
    const currentIndex = selectedSymbol
      ? filteredSymbols.findIndex(s => s.id === selectedSymbol)
      : -1
    const nextIndex = (currentIndex + 1) % filteredSymbols.length
    setSelectedSymbol(filteredSymbols[nextIndex].id)
  }, [filteredSymbols, selectedSymbol])

  const selectPrevSymbol = useCallback(() => {
    if (filteredSymbols.length === 0) return
    const currentIndex = selectedSymbol
      ? filteredSymbols.findIndex(s => s.id === selectedSymbol)
      : 0
    const prevIndex = currentIndex <= 0 ? filteredSymbols.length - 1 : currentIndex - 1
    setSelectedSymbol(filteredSymbols[prevIndex].id)
  }, [filteredSymbols, selectedSymbol])

  // Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle shortcuts when typing in input fields
      const target = e.target as HTMLElement
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        // Allow Escape to blur input
        if (e.key === "Escape") {
          target.blur()
        }
        return
      }

      // Help dialog
      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        setShowHelp(true)
        return
      }

      // Close help or clear selection
      if (e.key === "Escape") {
        e.preventDefault()
        if (showHelp) {
          setShowHelp(false)
        } else if (selectedSymbolIds.size > 0) {
          clearSelection()
        } else {
          setSelectedSymbol(null)
        }
        return
      }

      // Ctrl/Cmd shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case "z":
            e.preventDefault()
            undo()
            return
          case "y":
            e.preventDefault()
            redo()
            return
          case "a":
            e.preventDefault()
            selectAllSymbols(filteredSymbols)
            showToast(`Selected ${filteredSymbols.length} item${filteredSymbols.length !== 1 ? 's' : ''}`)
            return
          case "s":
            e.preventDefault()
            // Changes are auto-saved, just show the status
            if (lastSavedAt) {
              showToast(`All changes saved (last save: ${formatLastSaved(lastSavedAt)})`)
            } else {
              showToast("All changes are automatically saved")
            }
            return
        }
      }

      // Single key shortcuts (when not in input)
      switch (e.key.toLowerCase()) {
        case "v":
          e.preventDefault()
          // If multiple items are selected (checkbox selection), bulk verify
          if (selectedSymbolIds.size > 0) {
            bulkVerifySymbols(Array.from(selectedSymbolIds))
          } else if (selectedSymbol) {
            // Otherwise verify single selected item
            verifySymbol(selectedSymbol)
          }
          break
        case "f":
          e.preventDefault()
          // If multiple items are selected (checkbox selection), bulk flag
          if (selectedSymbolIds.size > 0) {
            bulkFlagSymbols(Array.from(selectedSymbolIds))
          } else if (selectedSymbol) {
            // Otherwise flag single selected item
            flagSymbol(selectedSymbol)
          }
          break
        case " ":
          // Space toggles checkbox selection of focused item
          if (selectedSymbol) {
            e.preventDefault()
            toggleSymbolSelection(selectedSymbol)
          }
          break
        case "delete":
        case "backspace":
          if (selectedSymbol) {
            e.preventDefault()
            deleteSymbol(selectedSymbol)
          }
          break
        case "+":
        case "=":
          e.preventDefault()
          setZoom(prev => Math.min(200, prev + 10))
          break
        case "-":
        case "_":
          e.preventDefault()
          setZoom(prev => Math.max(10, prev - 10))
          break
        case "tab":
          e.preventDefault()
          if (e.shiftKey) {
            selectPrevSymbol()
          } else {
            selectNextSymbol()
          }
          break
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [
    selectedSymbol,
    selectedSymbolIds,
    filteredSymbols,
    showHelp,
    undo,
    redo,
    verifySymbol,
    bulkVerifySymbols,
    flagSymbol,
    bulkFlagSymbols,
    deleteSymbol,
    selectNextSymbol,
    selectPrevSymbol,
    selectAllSymbols,
    clearSelection,
    toggleSymbolSelection,
    showToast,
    lastSavedAt,
    formatLastSaved,
  ])

  // Focus container for keyboard events
  useEffect(() => {
    containerRef.current?.focus()
  }, [])

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current)
      }
    }
  }, [])

  // Format relative time for last saved display
  const formatLastSaved = useCallback((date: Date | null): string => {
    if (!date) return ""
    const now = new Date()
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diffSeconds < 5) return "just now"
    if (diffSeconds < 60) return `${diffSeconds}s ago`
    const diffMinutes = Math.floor(diffSeconds / 60)
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    return date.toLocaleTimeString()
  }, [])

  return (
    <div
      ref={containerRef}
      className="h-[calc(100vh-8rem)] flex flex-col outline-none"
      tabIndex={-1}
    >
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

        <div className="flex items-center gap-4">
          {/* Save status indicator */}
          <SaveStatusIndicator
            status={saveStatus}
            lastSavedAt={lastSavedAt}
            formatLastSaved={formatLastSaved}
          />

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={undo}
              disabled={undoStack.length === 0}
              title="Undo (Ctrl+Z)"
            >
              <Undo className="h-4 w-4 mr-1" />
              Undo
              {undoStack.length > 0 && (
                <span className="ml-1 text-xs text-muted-foreground">({undoStack.length})</span>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={redo}
              disabled={redoStack.length === 0}
              title="Redo (Ctrl+Y)"
            >
              <Redo className="h-4 w-4 mr-1" />
              Redo
              {redoStack.length > 0 && (
                <span className="ml-1 text-xs text-muted-foreground">({redoStack.length})</span>
              )}
            </Button>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowHelp(true)}
              title="Keyboard shortcuts (?)"
            >
              <Keyboard className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex gap-4 pt-4 overflow-hidden">
        {/* Left panel - Original PDF */}
        <div className="flex-1 flex flex-col border rounded-lg overflow-hidden">
          <div className="flex items-center justify-between p-2 border-b bg-muted/50">
            <span className="text-sm font-medium">Original P&ID</span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" className="text-xs px-2" onClick={() => setZoom(25)}>
                Fit
              </Button>
              <Button variant="ghost" size="icon" onClick={() => setZoom(Math.max(10, zoom - 10))}>
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-sm w-12 text-center">{zoom}%</span>
              <Button variant="ghost" size="icon" onClick={() => setZoom(Math.min(200, zoom + 10))}>
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
            <div className="flex flex-col gap-1 mt-1">
              {flaggedCount > 0 && (
                <p className="text-xs text-orange-600 flex items-center gap-1">
                  <Flag className="h-3 w-3" />
                  {flaggedCount} flagged for review
                </p>
              )}
              {lowConfidenceCount > 0 && (
                <p className="text-xs text-yellow-600 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  {lowConfidenceCount} low confidence
                </p>
              )}
            </div>
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

          {/* Bulk action bar */}
          <div className="p-2 border-b bg-muted/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Checkbox
                id="select-all"
                checked={
                  filteredSymbols.length > 0 &&
                  filteredSymbols.every(s => selectedSymbolIds.has(s.id))
                }
                onCheckedChange={(checked) => {
                  if (checked) {
                    selectAllSymbols(filteredSymbols)
                  } else {
                    clearSelection()
                  }
                }}
              />
              <label
                htmlFor="select-all"
                className="text-xs text-muted-foreground cursor-pointer select-none"
              >
                {selectedSymbolIds.size > 0
                  ? `${selectedSymbolIds.size} selected`
                  : "Select all"}
              </label>
            </div>
            {selectedSymbolIds.size > 0 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={clearSelection}
                >
                  Clear
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => bulkFlagSymbols(Array.from(selectedSymbolIds))}
                  disabled={
                    Array.from(selectedSymbolIds).every(id => {
                      const s = symbols.find(sym => sym.id === id)
                      return s?.flagged
                    })
                  }
                >
                  <Flag className="h-3 w-3 mr-1" />
                  Flag ({selectedSymbolIds.size})
                </Button>
                <Button
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => bulkVerifySymbols(Array.from(selectedSymbolIds))}
                  disabled={
                    Array.from(selectedSymbolIds).every(id => {
                      const s = symbols.find(sym => sym.id === id)
                      return s?.validated
                    })
                  }
                >
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Verify ({selectedSymbolIds.size})
                </Button>
              </div>
            )}
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
                    : selectedSymbolIds.has(symbol.id)
                    ? "bg-primary/10"
                    : "hover:bg-muted/50"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={selectedSymbolIds.has(symbol.id)}
                      onCheckedChange={() => toggleSymbolSelection(symbol.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="h-4 w-4"
                    />
                    <div className={cn("w-2 h-2 rounded-full", typeColors[symbol.type])} />
                    <span className="font-medium">{symbol.tag}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {symbol.flagged && (
                      <Flag className="h-4 w-4 text-orange-500" title="Flagged for review" />
                    )}
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
                <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground ml-6">
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
                    title="Delete (Delete/Backspace)"
                  >
                    Delete
                  </Button>
                  <Button
                    variant={symbols.find(s => s.id === selectedSymbol)?.flagged ? "secondary" : "outline"}
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      const sym = symbols.find(s => s.id === selectedSymbol)
                      if (sym?.flagged) {
                        // Unflag via PATCH
                        api.patch(`/api/v1/drawings/${drawingId}/symbols/${selectedSymbol}`, { is_flagged: false })
                          .then(() => {
                            setSymbols(prev => prev.map(s => s.id === selectedSymbol ? { ...s, flagged: false } : s))
                            showToast(`Unflagged: ${sym.tag}`)
                          })
                      } else {
                        flagSymbol(selectedSymbol)
                      }
                    }}
                    title="Flag for review (F)"
                  >
                    <Flag className="h-4 w-4 mr-1" />
                    {symbols.find(s => s.id === selectedSymbol)?.flagged ? "Unflag" : "Flag"}
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => verifySymbol(selectedSymbol)}
                    disabled={symbols.find(s => s.id === selectedSymbol)?.validated}
                    title="Verify (V)"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    {symbols.find(s => s.id === selectedSymbol)?.validated ? "Verified" : "Verify"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground text-center mt-2">
                  Press ? for keyboard shortcuts
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toast notification */}
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      {/* Keyboard shortcuts help */}
      {showHelp && <KeyboardShortcutsHelp onClose={() => setShowHelp(false)} />}
    </div>
  )
}
