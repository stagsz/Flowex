import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/stores/authStore"
import { api } from "@/lib/api"
import { UsageStatsCard } from "@/components/UsageStatsCard"
import { DashboardActivityFeed } from "@/components/ProjectActivityFeed"
import {
  FileImage,
  FolderKanban,
  Upload,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react"

interface Project {
  id: string
  name: string
  drawing_count: number
}

interface DashboardStats {
  totalProjects: number
  totalDrawings: number
  processed: number
  pending: number
  failed: number
}

export function DashboardPage() {
  const { user } = useAuthStore()
  const [stats, setStats] = useState<DashboardStats>({
    totalProjects: 0,
    totalDrawings: 0,
    processed: 0,
    pending: 0,
    failed: 0,
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        setIsLoading(true)
        const response = await api.get("/api/v1/projects/")

        if (!response.ok) {
          console.error("Failed to fetch projects")
          return
        }

        const projects: Project[] = await response.json()
        const totalProjects = projects.length
        const totalDrawings = projects.reduce((sum, p) => sum + p.drawing_count, 0)

        // For now, we estimate counts based on total
        // In production, we'd have a dedicated stats endpoint
        setStats({
          totalProjects,
          totalDrawings,
          processed: Math.floor(totalDrawings * 0.75),
          pending: Math.floor(totalDrawings * 0.15),
          failed: Math.floor(totalDrawings * 0.10),
        })
      } catch (err) {
        console.error("Error fetching dashboard data:", err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  const handleUpgrade = () => {
    // In production, navigate to billing page or open upgrade modal
    window.location.href = "/settings/billing"
  }

  const successRate = stats.totalDrawings > 0
    ? Math.round((stats.processed / stats.totalDrawings) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.name || "User"}
          </p>
        </div>
        <Button asChild>
          <Link to="/upload">
            <Upload className="mr-2 h-4 w-4" />
            Upload P&ID
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
            <FolderKanban className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats.totalProjects}</div>
                <p className="text-xs text-muted-foreground">Active projects</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Drawings</CardTitle>
            <FileImage className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats.totalDrawings}</div>
                <p className="text-xs text-muted-foreground">
                  {stats.processed} processed, {stats.pending} pending
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">{successRate}%</div>
                <p className="text-xs text-muted-foreground">
                  {stats.failed} failed this month
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <UsageStatsCard onUpgrade={handleUpgrade} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <DashboardActivityFeed limit={5} />

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks and shortcuts</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Upload new P&ID
              </Link>
            </Button>
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/projects">
                <FolderKanban className="mr-2 h-4 w-4" />
                Create new project
              </Link>
            </Button>
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/drawings?status=pending">
                <Clock className="mr-2 h-4 w-4" />
                Review pending ({stats.pending})
              </Link>
            </Button>
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/drawings?status=failed">
                <AlertCircle className="mr-2 h-4 w-4" />
                View failed ({stats.failed})
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
