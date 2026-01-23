import { useCallback, useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAuthStore } from "@/stores/authStore"
import { api } from "@/lib/api"
import {
  Bug,
  Lightbulb,
  MessageSquare,
  Gauge,
  Star,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  ExternalLink,
} from "lucide-react"

interface FeedbackStats {
  total_feedback: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  by_priority: Record<string, number>
  average_satisfaction: number | null
  recent_feedback_count: number
}

interface FeedbackItem {
  id: string
  feedback_type: string
  priority: string
  status: string
  title: string
  description: string
  satisfaction_rating: number | null
  page_url: string | null
  created_at: string
  user: {
    id: string
    name: string
    email: string
  }
}

interface FeedbackListResponse {
  items: FeedbackItem[]
  total: number
  page: number
  page_size: number
}

const typeIcons: Record<string, React.ReactNode> = {
  bug: <Bug className="h-4 w-4" />,
  feature_request: <Lightbulb className="h-4 w-4" />,
  usability: <MessageSquare className="h-4 w-4" />,
  performance: <Gauge className="h-4 w-4" />,
  general: <Star className="h-4 w-4" />,
}

const typeColors: Record<string, string> = {
  bug: "bg-red-100 text-red-800",
  feature_request: "bg-purple-100 text-purple-800",
  usability: "bg-blue-100 text-blue-800",
  performance: "bg-orange-100 text-orange-800",
  general: "bg-gray-100 text-gray-800",
}

const priorityColors: Record<string, string> = {
  critical: "bg-red-500 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-green-500 text-white",
}

const statusColors: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  acknowledged: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-purple-100 text-purple-800",
  resolved: "bg-green-100 text-green-800",
  wont_fix: "bg-gray-100 text-gray-800",
}

export function BetaAdminPage() {
  const { user } = useAuthStore()
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [feedback, setFeedback] = useState<FeedbackItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  // Check if user has admin access
  const isAdmin = user && (user.role === "admin" || user.role === "owner")

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Fetch stats and feedback in parallel
      const [statsRes, feedbackRes] = await Promise.all([
        api.get("/api/v1/feedback/stats"),
        api.get(`/api/v1/feedback?page=1&page_size=50${typeFilter !== "all" ? `&feedback_type=${typeFilter}` : ""}${statusFilter !== "all" ? `&status=${statusFilter}` : ""}`),
      ])

      if (!statsRes.ok) {
        throw new Error("Failed to fetch feedback stats")
      }
      if (!feedbackRes.ok) {
        throw new Error("Failed to fetch feedback list")
      }

      const statsData: FeedbackStats = await statsRes.json()
      const feedbackData: FeedbackListResponse = await feedbackRes.json()

      setStats(statsData)
      setFeedback(feedbackData.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data")
    } finally {
      setIsLoading(false)
    }
  }, [typeFilter, statusFilter])

  useEffect(() => {
    // Only fetch data if user is an admin
    if (!isAdmin) return
    fetchData()
  }, [isAdmin, fetchData])

  // Only admins can access this page - return after hooks are called
  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  const updateFeedbackStatus = async (feedbackId: string, newStatus: string) => {
    setUpdatingId(feedbackId)
    try {
      const res = await api.patch(`/api/v1/feedback/${feedbackId}/status`, {
        status: newStatus,
      })
      if (!res.ok) {
        throw new Error("Failed to update status")
      }
      // Refresh data
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status")
    } finally {
      setUpdatingId(null)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (isLoading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Beta Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor pilot customer feedback and beta testing progress
          </p>
        </div>
        <Button onClick={fetchData} variant="outline" disabled={isLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Stats Overview */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Feedback</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_feedback}</div>
              <p className="text-xs text-muted-foreground">
                {stats.recent_feedback_count} in last 7 days
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Satisfaction</CardTitle>
              <Star className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.average_satisfaction
                  ? `${stats.average_satisfaction.toFixed(1)}/5`
                  : "N/A"}
              </div>
              <div className="flex gap-1 mt-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Star
                    key={i}
                    className={`h-3 w-3 ${
                      stats.average_satisfaction && i <= Math.round(stats.average_satisfaction)
                        ? "text-yellow-500 fill-yellow-500"
                        : "text-gray-300"
                    }`}
                  />
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Open Issues</CardTitle>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(stats.by_status.new || 0) + (stats.by_status.acknowledged || 0) + (stats.by_status.in_progress || 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                {stats.by_status.new || 0} new, {stats.by_status.in_progress || 0} in progress
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resolved</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.by_status.resolved || 0}</div>
              <p className="text-xs text-muted-foreground">
                {stats.total_feedback > 0
                  ? `${Math.round(((stats.by_status.resolved || 0) / stats.total_feedback) * 100)}% resolution rate`
                  : "No feedback yet"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Breakdown Cards */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">By Type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(stats.by_type).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {typeIcons[type]}
                    <span className="text-sm capitalize">{type.replace("_", " ")}</span>
                  </div>
                  <Badge variant="secondary">{count}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">By Priority</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(stats.by_priority).map(([priority, count]) => (
                <div key={priority} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{priority}</span>
                  <Badge className={priorityColors[priority]}>{count}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">By Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(stats.by_status).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{status.replace("_", " ")}</span>
                  <Badge className={statusColors[status]}>{count}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Feedback List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Feedback</CardTitle>
              <CardDescription>
                Review and manage pilot customer feedback
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Filter by type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="bug">Bug</SelectItem>
                  <SelectItem value="feature_request">Feature Request</SelectItem>
                  <SelectItem value="usability">Usability</SelectItem>
                  <SelectItem value="performance">Performance</SelectItem>
                  <SelectItem value="general">General</SelectItem>
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="new">New</SelectItem>
                  <SelectItem value="acknowledged">Acknowledged</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="wont_fix">Won't Fix</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {feedback.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No feedback found</p>
              <p className="text-sm">Feedback from pilot customers will appear here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {feedback.map((item) => (
                <div
                  key={item.id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Badge className={typeColors[item.feedback_type]}>
                        {typeIcons[item.feedback_type]}
                        <span className="ml-1 capitalize">
                          {item.feedback_type.replace("_", " ")}
                        </span>
                      </Badge>
                      <Badge className={priorityColors[item.priority]}>
                        {item.priority}
                      </Badge>
                      <Badge className={statusColors[item.status]}>
                        {item.status.replace("_", " ")}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatDate(item.created_at)}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium">{item.title}</h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      {item.description}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>From: {item.user?.name || "Unknown"}</span>
                      {item.satisfaction_rating && (
                        <span className="flex items-center gap-1">
                          <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                          {item.satisfaction_rating}/5
                        </span>
                      )}
                      {item.page_url && (
                        <a
                          href={item.page_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 hover:text-primary"
                        >
                          <ExternalLink className="h-3 w-3" />
                          View Page
                        </a>
                      )}
                    </div>

                    <Select
                      value={item.status}
                      onValueChange={(value) => updateFeedbackStatus(item.id, value)}
                      disabled={updatingId === item.id}
                    >
                      <SelectTrigger className="w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="new">New</SelectItem>
                        <SelectItem value="acknowledged">Acknowledged</SelectItem>
                        <SelectItem value="in_progress">In Progress</SelectItem>
                        <SelectItem value="resolved">Resolved</SelectItem>
                        <SelectItem value="wont_fix">Won't Fix</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Beta Testing Resources */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Beta Testing Resources
          </CardTitle>
          <CardDescription>
            Quick links for managing the beta program
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-2">
          <Button variant="outline" className="justify-start" asChild>
            <a
              href="https://flowex-production-30eb.up.railway.app/docs"
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              API Documentation
            </a>
          </Button>
          <Button variant="outline" className="justify-start" asChild>
            <a
              href="https://pkagkffjhvtbovxzaytx.supabase.co"
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Supabase Dashboard
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
