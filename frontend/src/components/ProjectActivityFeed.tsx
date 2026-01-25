import { useState, useEffect, useCallback } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import {
  Upload,
  CheckCircle,
  Download,
  Loader2,
  Activity,
  User,
  FileImage,
  Pencil,
  Trash2,
  Flag,
  Link as LinkIcon,
} from "lucide-react"
import { Link } from "react-router-dom"

interface ActivityItem {
  id: string
  user_name: string | null
  action: string
  entity_type: string | null
  entity_name: string | null
  timestamp: string
}

interface ProjectActivityFeedProps {
  projectId: string
  limit?: number
  showHeader?: boolean
  showViewAll?: boolean
}

// Map action types to icons
function getActionIcon(action: string) {
  switch (action) {
    case "uploaded":
      return <Upload className="h-4 w-4 text-blue-500" />
    case "completed_validation":
    case "verified_symbol":
    case "verified_line":
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case "exported":
    case "exported_dxf":
    case "exported_data_list":
      return <Download className="h-4 w-4 text-purple-500" />
    case "started_processing":
    case "completed_processing":
      return <Activity className="h-4 w-4 text-yellow-500" />
    case "created_symbol":
    case "created_line":
      return <FileImage className="h-4 w-4 text-blue-500" />
    case "updated_symbol":
    case "updated_line":
      return <Pencil className="h-4 w-4 text-orange-500" />
    case "deleted_symbol":
    case "deleted_line":
      return <Trash2 className="h-4 w-4 text-red-500" />
    case "flagged_symbol":
    case "flagged_line":
      return <Flag className="h-4 w-4 text-orange-500" />
    case "connected_cloud":
      return <LinkIcon className="h-4 w-4 text-blue-500" />
    default:
      return <Activity className="h-4 w-4 text-muted-foreground" />
  }
}

// Format action for display
function formatAction(action: string): string {
  // Convert snake_case to readable text
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

// Format relative time
function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export function ProjectActivityFeed({
  projectId,
  limit = 10,
  showHeader = true,
  showViewAll = false,
}: ProjectActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchActivities = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get(
        `/api/v1/projects/${projectId}/activity?limit=${limit}`
      )
      if (response.ok) {
        const data = await response.json()
        setActivities(data.items || [])
      } else {
        setError("Failed to load activity")
      }
    } catch {
      setError("Failed to load activity")
    } finally {
      setLoading(false)
    }
  }, [projectId, limit])

  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  if (loading) {
    return (
      <Card>
        {showHeader && (
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Loading activity...</CardDescription>
          </CardHeader>
        )}
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        {showHeader && (
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Project activity feed</CardDescription>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <Activity className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button
              variant="link"
              size="sm"
              onClick={() => fetchActivities()}
              className="mt-2"
            >
              Try again
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (activities.length === 0) {
    return (
      <Card>
        {showHeader && (
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Project activity feed</CardDescription>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <Activity className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No activity yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Activity will appear here when team members work on drawings
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      {showHeader && (
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Project activity feed</CardDescription>
        </CardHeader>
      )}
      <CardContent>
        <div className="space-y-4">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className="flex items-start gap-3"
            >
              <div className="flex-shrink-0 mt-0.5">
                {getActionIcon(activity.action)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm">
                  <span className="font-medium">
                    {activity.user_name || "System"}
                  </span>{" "}
                  <span className="text-muted-foreground">
                    {formatAction(activity.action).toLowerCase()}
                  </span>
                  {activity.entity_name && (
                    <>
                      {" "}
                      <span className="font-medium">{activity.entity_name}</span>
                    </>
                  )}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {formatRelativeTime(activity.timestamp)}
                </p>
              </div>
            </div>
          ))}
        </div>
        {showViewAll && (
          <Button variant="link" className="mt-4 p-0" asChild>
            <Link to={`/admin/audit-logs`}>View all activity</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

// Export a wrapper component for use without a project context
// This fetches activity from the first available project
interface DashboardActivityFeedProps {
  limit?: number
}

export function DashboardActivityFeed({ limit = 5 }: DashboardActivityFeedProps) {
  const [projectId, setProjectId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [noProjects, setNoProjects] = useState(false)

  useEffect(() => {
    async function fetchFirstProject() {
      try {
        const response = await api.get("/api/v1/projects/")
        if (response.ok) {
          const projects = await response.json()
          if (projects.length > 0) {
            // Use the most recently updated project
            const sorted = [...projects].sort((a: { updated_at?: string }, b: { updated_at?: string }) => {
              const dateA = new Date(a.updated_at || 0)
              const dateB = new Date(b.updated_at || 0)
              return dateB.getTime() - dateA.getTime()
            })
            setProjectId(sorted[0].id)
          } else {
            setNoProjects(true)
          }
        }
      } catch {
        setNoProjects(true)
      } finally {
        setLoading(false)
      }
    }
    fetchFirstProject()
  }, [])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (noProjects || !projectId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Project activity feed</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <User className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No projects yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Create a project to see activity
            </p>
            <Button variant="link" size="sm" className="mt-2" asChild>
              <Link to="/projects">Create project</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <ProjectActivityFeed
      projectId={projectId}
      limit={limit}
      showViewAll={true}
    />
  )
}
