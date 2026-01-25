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
import { Input } from "@/components/ui/input"
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
  Shield,
  RefreshCw,
  Clock,
  User,
  FileText,
  Download,
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  Activity,
} from "lucide-react"

interface AuditLogItem {
  id: string
  user_id: string | null
  user_email: string | null
  user_name: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  ip_address: string | null
  metadata: Record<string, string> | null
  timestamp: string
}

interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
}

// Action categories for better UI organization
const actionCategories: Record<string, { label: string; color: string }> = {
  login: { label: "Auth", color: "bg-blue-100 text-blue-800" },
  logout: { label: "Auth", color: "bg-blue-100 text-blue-800" },
  token_refresh: { label: "Auth", color: "bg-blue-100 text-blue-800" },
  user_invite: { label: "Users", color: "bg-purple-100 text-purple-800" },
  user_role_update: { label: "Users", color: "bg-purple-100 text-purple-800" },
  user_remove: { label: "Users", color: "bg-purple-100 text-purple-800" },
  invite_revoke: { label: "Users", color: "bg-purple-100 text-purple-800" },
  invite_accept: { label: "Users", color: "bg-purple-100 text-purple-800" },
  project_create: { label: "Projects", color: "bg-green-100 text-green-800" },
  project_update: { label: "Projects", color: "bg-green-100 text-green-800" },
  project_delete: { label: "Projects", color: "bg-green-100 text-green-800" },
  drawing_upload: { label: "Drawings", color: "bg-orange-100 text-orange-800" },
  drawing_process: { label: "Drawings", color: "bg-orange-100 text-orange-800" },
  drawing_delete: { label: "Drawings", color: "bg-orange-100 text-orange-800" },
  symbol_create: { label: "Symbols", color: "bg-yellow-100 text-yellow-800" },
  symbol_update: { label: "Symbols", color: "bg-yellow-100 text-yellow-800" },
  symbol_delete: { label: "Symbols", color: "bg-yellow-100 text-yellow-800" },
  symbol_verify: { label: "Symbols", color: "bg-yellow-100 text-yellow-800" },
  symbol_bulk_verify: { label: "Symbols", color: "bg-yellow-100 text-yellow-800" },
  symbol_flag: { label: "Symbols", color: "bg-yellow-100 text-yellow-800" },
  line_create: { label: "Lines", color: "bg-teal-100 text-teal-800" },
  line_update: { label: "Lines", color: "bg-teal-100 text-teal-800" },
  line_delete: { label: "Lines", color: "bg-teal-100 text-teal-800" },
  line_verify: { label: "Lines", color: "bg-teal-100 text-teal-800" },
  line_bulk_verify: { label: "Lines", color: "bg-teal-100 text-teal-800" },
  export_dxf: { label: "Exports", color: "bg-indigo-100 text-indigo-800" },
  export_list: { label: "Exports", color: "bg-indigo-100 text-indigo-800" },
  export_report: { label: "Exports", color: "bg-indigo-100 text-indigo-800" },
  export_checklist: { label: "Exports", color: "bg-indigo-100 text-indigo-800" },
  cloud_connect: { label: "Cloud", color: "bg-cyan-100 text-cyan-800" },
  cloud_disconnect: { label: "Cloud", color: "bg-cyan-100 text-cyan-800" },
  cloud_import: { label: "Cloud", color: "bg-cyan-100 text-cyan-800" },
  cloud_export: { label: "Cloud", color: "bg-cyan-100 text-cyan-800" },
  data_export_request: { label: "GDPR", color: "bg-red-100 text-red-800" },
  account_deletion_request: { label: "GDPR", color: "bg-red-100 text-red-800" },
}

// Available action types for filtering
const actionTypes = [
  { value: "login", label: "Login" },
  { value: "logout", label: "Logout" },
  { value: "user_invite", label: "User Invite" },
  { value: "user_role_update", label: "Role Update" },
  { value: "user_remove", label: "User Remove" },
  { value: "project_create", label: "Project Create" },
  { value: "project_update", label: "Project Update" },
  { value: "project_delete", label: "Project Delete" },
  { value: "drawing_upload", label: "Drawing Upload" },
  { value: "drawing_process", label: "Drawing Process" },
  { value: "drawing_delete", label: "Drawing Delete" },
  { value: "symbol_verify", label: "Symbol Verify" },
  { value: "symbol_bulk_verify", label: "Bulk Verify" },
  { value: "export_dxf", label: "Export DXF" },
  { value: "export_list", label: "Export List" },
  { value: "cloud_connect", label: "Cloud Connect" },
  { value: "cloud_import", label: "Cloud Import" },
  { value: "data_export_request", label: "Data Export" },
  { value: "account_deletion_request", label: "Account Delete" },
]

export function AuditLogsPage() {
  const { user } = useAuthStore()
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(25)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [actionFilter, setActionFilter] = useState<string>("all")
  const [userSearch, setUserSearch] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  // Check if user has admin access
  const isAdmin = user && (user.role === "admin" || user.role === "owner")

  const fetchLogs = useCallback(async () => {
    if (!user?.organizationId) return

    setIsLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      })

      if (actionFilter !== "all") {
        params.append("action", actionFilter)
      }
      if (startDate) {
        params.append("start_date", new Date(startDate).toISOString())
      }
      if (endDate) {
        // Add end of day for end date
        const endDateTime = new Date(endDate)
        endDateTime.setHours(23, 59, 59, 999)
        params.append("end_date", endDateTime.toISOString())
      }

      const res = await api.get(
        `/api/v1/organizations/${user.organizationId}/audit-logs?${params}`
      )

      if (!res.ok) {
        if (res.status === 403) {
          throw new Error("Access denied. Admin privileges required.")
        }
        throw new Error("Failed to fetch audit logs")
      }

      const data: AuditLogListResponse = await res.json()

      // Filter by user email/name client-side if search is provided
      let filteredItems = data.items
      if (userSearch) {
        const search = userSearch.toLowerCase()
        filteredItems = data.items.filter(
          (log) =>
            log.user_email?.toLowerCase().includes(search) ||
            log.user_name?.toLowerCase().includes(search)
        )
      }

      setLogs(filteredItems)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs")
    } finally {
      setIsLoading(false)
    }
  }, [user?.organizationId, page, pageSize, actionFilter, startDate, endDate, userSearch])

  useEffect(() => {
    if (!isAdmin) return
    fetchLogs()
  }, [isAdmin, fetchLogs])

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [actionFilter, startDate, endDate, userSearch])

  // Only admins can access this page
  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const formatAction = (action: string) => {
    return action
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  }

  const totalPages = Math.ceil(total / pageSize)

  const exportToCSV = () => {
    const headers = [
      "Timestamp",
      "User",
      "Email",
      "Action",
      "Entity Type",
      "Entity ID",
      "IP Address",
      "Metadata",
    ]
    const rows = logs.map((log) => [
      log.timestamp,
      log.user_name || "System",
      log.user_email || "",
      log.action,
      log.entity_type || "",
      log.entity_id || "",
      log.ip_address || "",
      log.metadata ? JSON.stringify(log.metadata) : "",
    ])

    const csvContent = [
      headers.join(","),
      ...rows.map((row) =>
        row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
      ),
    ].join("\n")

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const link = document.createElement("a")
    link.href = URL.createObjectURL(blob)
    link.download = `audit-logs-${new Date().toISOString().split("T")[0]}.csv`
    link.click()
  }

  const clearFilters = () => {
    setActionFilter("all")
    setUserSearch("")
    setStartDate("")
    setEndDate("")
    setPage(1)
  }

  const hasActiveFilters =
    actionFilter !== "all" || userSearch || startDate || endDate

  if (isLoading && logs.length === 0) {
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
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Shield className="h-8 w-8" />
            Audit Logs
          </h1>
          <p className="text-muted-foreground">
            Track and review user activity across your organization
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={exportToCSV} variant="outline" disabled={logs.length === 0}>
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
          <Button onClick={fetchLogs} variant="outline" disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-2">
              <label className="text-sm font-medium">Action Type</label>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  {actionTypes.map((action) => (
                    <SelectItem key={action.value} value={action.value}>
                      {action.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">User Search</label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or email"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Start Date</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">End Date</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

            <div className="flex items-end">
              <Button
                variant="ghost"
                onClick={clearFilters}
                disabled={!hasActiveFilters}
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Activity Log
              </CardTitle>
              <CardDescription>
                {total.toLocaleString()} total entries
                {hasActiveFilters && " (filtered)"}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No audit logs found</p>
              <p className="text-sm">
                {hasActiveFilters
                  ? "Try adjusting your filters"
                  : "Activity will be recorded here"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Table Header */}
              <div className="hidden md:grid md:grid-cols-12 gap-4 px-4 py-2 text-sm font-medium text-muted-foreground border-b">
                <div className="col-span-2">Timestamp</div>
                <div className="col-span-2">User</div>
                <div className="col-span-2">Action</div>
                <div className="col-span-2">Entity</div>
                <div className="col-span-2">IP Address</div>
                <div className="col-span-2">Details</div>
              </div>

              {/* Log Entries */}
              {logs.map((log) => {
                const category = actionCategories[log.action] || {
                  label: "Other",
                  color: "bg-gray-100 text-gray-800",
                }

                return (
                  <div
                    key={log.id}
                    className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-4 py-3 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    {/* Timestamp */}
                    <div className="md:col-span-2 flex items-center gap-2 text-sm">
                      <Clock className="h-4 w-4 text-muted-foreground md:hidden" />
                      <span className="font-mono text-muted-foreground">
                        {formatDate(log.timestamp)}
                      </span>
                    </div>

                    {/* User */}
                    <div className="md:col-span-2 flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <div className="truncate">
                        <div className="font-medium truncate">
                          {log.user_name || "System"}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {log.user_email || ""}
                        </div>
                      </div>
                    </div>

                    {/* Action */}
                    <div className="md:col-span-2 flex items-center gap-2">
                      <Badge className={category.color}>{category.label}</Badge>
                      <span className="text-sm">{formatAction(log.action)}</span>
                    </div>

                    {/* Entity */}
                    <div className="md:col-span-2 text-sm">
                      {log.entity_type && (
                        <div>
                          <span className="text-muted-foreground capitalize">
                            {log.entity_type}
                          </span>
                          {log.entity_id && (
                            <div className="text-xs text-muted-foreground font-mono truncate">
                              {log.entity_id.slice(0, 8)}...
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* IP Address */}
                    <div className="md:col-span-2 text-sm font-mono text-muted-foreground">
                      {log.ip_address || "-"}
                    </div>

                    {/* Metadata */}
                    <div className="md:col-span-2 text-sm">
                      {log.metadata && Object.keys(log.metadata).length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          {Object.entries(log.metadata)
                            .slice(0, 2)
                            .map(([key, value]) => (
                              <div key={key} className="truncate">
                                <span className="font-medium">{key}:</span> {value}
                              </div>
                            ))}
                          {Object.keys(log.metadata).length > 2 && (
                            <span className="text-muted-foreground">
                              +{Object.keys(log.metadata).length - 2} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * pageSize + 1} to{" "}
                {Math.min(page * pageSize, total)} of {total} entries
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1 || isLoading}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground px-2">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages || isLoading}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
