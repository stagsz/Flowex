import { Link } from "react-router-dom"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { useAuthStore } from "@/stores/authStore"
import {
  FileImage,
  FolderKanban,
  Upload,
  CheckCircle,
  Clock,
  AlertCircle,
} from "lucide-react"

export function DashboardPage() {
  const { user } = useAuthStore()

  // Mock data - would come from API
  const stats = {
    totalProjects: 12,
    totalDrawings: 48,
    processed: 42,
    pending: 4,
    failed: 2,
    monthlyUsage: 35,
    monthlyLimit: 50,
  }

  const recentDrawings = [
    {
      id: "1",
      name: "P&ID-001-Rev3.pdf",
      project: "Refinery Unit A",
      status: "completed",
      processedAt: "2 hours ago",
    },
    {
      id: "2",
      name: "P&ID-002-Rev1.pdf",
      project: "Refinery Unit A",
      status: "processing",
      processedAt: "Processing...",
    },
    {
      id: "3",
      name: "PFD-Main-Process.pdf",
      project: "Chemical Plant B",
      status: "completed",
      processedAt: "Yesterday",
    },
    {
      id: "4",
      name: "P&ID-Utilities.pdf",
      project: "Chemical Plant B",
      status: "failed",
      processedAt: "Failed",
    },
  ]

  const statusIcon = {
    completed: <CheckCircle className="h-4 w-4 text-green-500" />,
    processing: <Clock className="h-4 w-4 text-yellow-500 animate-pulse" />,
    failed: <AlertCircle className="h-4 w-4 text-red-500" />,
  }

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
            <div className="text-2xl font-bold">{stats.totalProjects}</div>
            <p className="text-xs text-muted-foreground">Active projects</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Drawings</CardTitle>
            <FileImage className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDrawings}</div>
            <p className="text-xs text-muted-foreground">
              {stats.processed} processed, {stats.pending} pending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round((stats.processed / stats.totalDrawings) * 100)}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.failed} failed this month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Usage</CardTitle>
            <FileImage className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.monthlyUsage}/{stats.monthlyLimit}
            </div>
            <Progress
              value={(stats.monthlyUsage / stats.monthlyLimit) * 100}
              className="mt-2"
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Drawings</CardTitle>
            <CardDescription>
              Your most recently uploaded drawings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentDrawings.map((drawing) => (
                <div
                  key={drawing.id}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    {statusIcon[drawing.status as keyof typeof statusIcon]}
                    <div>
                      <p className="text-sm font-medium">{drawing.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {drawing.project}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {drawing.processedAt}
                  </span>
                </div>
              ))}
            </div>
            <Button variant="link" className="mt-4 p-0" asChild>
              <Link to="/drawings">View all drawings</Link>
            </Button>
          </CardContent>
        </Card>

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
              <Link to="/projects/new">
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
