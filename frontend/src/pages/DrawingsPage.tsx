import { useState, useEffect } from "react"
import { Link, useSearchParams } from "react-router-dom"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
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
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

interface Drawing {
  id: string
  name: string
  projectName: string
  status: "pending" | "processing" | "completed" | "failed"
  progress: number
  symbolsDetected: number
  createdAt: string
  processedAt?: string
}

export function DrawingsPage() {
  const [searchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState(
    searchParams.get("status") || "all"
  )
  const [drawings, setDrawings] = useState<Drawing[]>([])
  const [loading, setLoading] = useState(true)

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // Fetch drawings from API
  useEffect(() => {
    async function fetchDrawings() {
      try {
        // First fetch all projects, then get drawings for each
        const projectsResponse = await fetch(`${apiUrl}/api/projects`)
        if (projectsResponse.ok) {
          const projects = await projectsResponse.json()
          const allDrawings: Drawing[] = []

          for (const project of projects) {
            const drawingsResponse = await fetch(`${apiUrl}/api/drawings/project/${project.id}`)
            if (drawingsResponse.ok) {
              const projectDrawings = await drawingsResponse.json()
              for (const d of projectDrawings) {
                allDrawings.push({
                  id: d.id,
                  name: d.original_filename,
                  projectName: project.name,
                  status: d.status as Drawing["status"],
                  progress: d.status === "completed" ? 100 : d.status === "processing" ? 50 : 0,
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
  }, [apiUrl])

  const statusConfig = {
    pending: {
      icon: Clock,
      label: "Pending",
      className: "text-yellow-500",
    },
    processing: {
      icon: Clock,
      label: "Processing",
      className: "text-blue-500 animate-pulse",
    },
    completed: {
      icon: CheckCircle,
      label: "Completed",
      className: "text-green-500",
    },
    failed: {
      icon: AlertCircle,
      label: "Failed",
      className: "text-red-500",
    },
  }

  const filteredDrawings = drawings.filter((drawing) => {
    const matchesSearch =
      drawing.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      drawing.projectName.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus =
      statusFilter === "all" || drawing.status === statusFilter
    return matchesSearch && matchesStatus
  })

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
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex gap-1">
            {["all", "pending", "processing", "completed", "failed"].map(
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
      </div>

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
          {filteredDrawings.map((drawing) => {
            const StatusIcon = statusConfig[drawing.status].icon
            return (
              <Card key={drawing.id}>
                <CardContent className="flex items-center gap-4 p-4">
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
                    {drawing.status === "processing" && (
                      <Progress value={drawing.progress} className="mt-2 h-1" />
                    )}
                  </div>

                  <div className="hidden md:block text-right">
                    {drawing.status === "completed" && (
                      <p className="text-sm font-medium">
                        {drawing.symbolsDetected} symbols
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {drawing.processedAt || drawing.createdAt}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {drawing.status === "completed" && (
                      <>
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/drawings/${drawing.id}/validate`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button variant="outline" size="sm">
                          <Download className="h-4 w-4" />
                        </Button>
                      </>
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
                        {drawing.status === "completed" && (
                          <DropdownMenuItem asChild>
                            <Link to={`/drawings/${drawing.id}/validate`}>
                              Validate
                            </Link>
                          </DropdownMenuItem>
                        )}
                        {drawing.status === "failed" && (
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
    </div>
  )
}
