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
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuthStore } from "@/stores/authStore"
import { api } from "@/lib/api"
import {
  Users,
  UserPlus,
  RefreshCw,
  MoreVertical,
  Mail,
  Clock,
  Shield,
  UserX,
  UserCog,
  Copy,
  Check,
  AlertTriangle,
} from "lucide-react"

// Types matching backend API
interface OrganizationMember {
  id: string
  email: string
  name: string | null
  role: string
  is_active: boolean
  created_at: string
}

interface MemberListResponse {
  items: OrganizationMember[]
  total: number
  page: number
  page_size: number
}

interface Invitation {
  id: string
  email: string
  role: string
  status: string
  expires_at: string
  created_at: string
  invited_by_name: string | null
}

interface InviteListResponse {
  items: Invitation[]
  total: number
  page: number
  page_size: number
}

// Role badges with colors
const roleBadges: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  admin: { label: "Admin", variant: "default" },
  member: { label: "Member", variant: "secondary" },
  viewer: { label: "Viewer", variant: "outline" },
}

// Invitation status badges
const statusBadges: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "bg-yellow-100 text-yellow-800" },
  accepted: { label: "Accepted", color: "bg-green-100 text-green-800" },
  expired: { label: "Expired", color: "bg-gray-100 text-gray-800" },
  revoked: { label: "Revoked", color: "bg-red-100 text-red-800" },
}

export function OrganizationMembersPage() {
  const { user } = useAuthStore()
  const [members, setMembers] = useState<OrganizationMember[]>([])
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Invite dialog state
  const [showInviteDialog, setShowInviteDialog] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState<string>("member")
  const [isInviting, setIsInviting] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)

  // Role change dialog state
  const [showRoleDialog, setShowRoleDialog] = useState(false)
  const [selectedMember, setSelectedMember] = useState<OrganizationMember | null>(null)
  const [newRole, setNewRole] = useState<string>("")
  const [isUpdatingRole, setIsUpdatingRole] = useState(false)

  // Remove member dialog state
  const [showRemoveDialog, setShowRemoveDialog] = useState(false)
  const [memberToRemove, setMemberToRemove] = useState<OrganizationMember | null>(null)
  const [isRemoving, setIsRemoving] = useState(false)

  // Copied token state
  const [copiedInviteId, setCopiedInviteId] = useState<string | null>(null)

  // Check if user has admin access
  const isAdmin = user && (user.role === "admin" || user.role === "owner")
  const organizationId = user?.organizationId

  const fetchMembers = useCallback(async () => {
    if (!organizationId) return

    try {
      const res = await api.get(`/api/v1/organizations/${organizationId}/users?page_size=100`)
      if (!res.ok) {
        throw new Error("Failed to fetch members")
      }
      const data: MemberListResponse = await res.json()
      setMembers(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members")
    }
  }, [organizationId])

  const fetchInvitations = useCallback(async () => {
    if (!organizationId || !isAdmin) return

    try {
      const res = await api.get(`/api/v1/organizations/${organizationId}/invites?page_size=100`)
      if (!res.ok) {
        if (res.status === 403) return // Non-admins can't see invites
        throw new Error("Failed to fetch invitations")
      }
      const data: InviteListResponse = await res.json()
      setInvitations(data.items)
    } catch (err) {
      console.error("Failed to fetch invitations:", err)
    }
  }, [organizationId, isAdmin])

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    await Promise.all([fetchMembers(), fetchInvitations()])
    setIsLoading(false)
  }, [fetchMembers, fetchInvitations])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Only admins can access this page
  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  const handleInvite = async () => {
    if (!inviteEmail || !organizationId) return

    setIsInviting(true)
    setInviteError(null)

    try {
      const res = await api.post(`/api/v1/organizations/${organizationId}/invites`, {
        email: inviteEmail,
        role: inviteRole,
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || "Failed to send invitation")
      }

      // Refresh invitations list
      await fetchInvitations()
      setShowInviteDialog(false)
      setInviteEmail("")
      setInviteRole("member")
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : "Failed to send invitation")
    } finally {
      setIsInviting(false)
    }
  }

  const handleRoleChange = async () => {
    if (!selectedMember || !newRole || !organizationId) return

    setIsUpdatingRole(true)

    try {
      const res = await api.patch(
        `/api/v1/organizations/${organizationId}/users/${selectedMember.id}`,
        { role: newRole }
      )

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || "Failed to update role")
      }

      // Refresh members list
      await fetchMembers()
      setShowRoleDialog(false)
      setSelectedMember(null)
      setNewRole("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update role")
    } finally {
      setIsUpdatingRole(false)
    }
  }

  const handleRemoveMember = async () => {
    if (!memberToRemove || !organizationId) return

    setIsRemoving(true)

    try {
      const res = await api.delete(
        `/api/v1/organizations/${organizationId}/users/${memberToRemove.id}`
      )

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || "Failed to remove member")
      }

      // Refresh members list
      await fetchMembers()
      setShowRemoveDialog(false)
      setMemberToRemove(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member")
    } finally {
      setIsRemoving(false)
    }
  }

  const handleRevokeInvite = async (inviteId: string) => {
    if (!organizationId) return

    try {
      const res = await api.delete(`/api/v1/organizations/${organizationId}/invites/${inviteId}`)

      if (!res.ok) {
        throw new Error("Failed to revoke invitation")
      }

      // Refresh invitations list
      await fetchInvitations()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke invitation")
    }
  }

  const copyInviteToken = async (invite: Invitation) => {
    // In a real implementation, the backend would return a token
    // For now, we show the invite ID as a placeholder
    const inviteUrl = `${window.location.origin}/invite/${invite.id}`
    await navigator.clipboard.writeText(inviteUrl)
    setCopiedInviteId(invite.id)
    setTimeout(() => setCopiedInviteId(null), 2000)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const openRoleDialog = (member: OrganizationMember) => {
    setSelectedMember(member)
    setNewRole(member.role)
    setShowRoleDialog(true)
  }

  const openRemoveDialog = (member: OrganizationMember) => {
    setMemberToRemove(member)
    setShowRemoveDialog(true)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  // Filter pending invitations for display
  const pendingInvitations = invitations.filter((i) => i.status === "pending")

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Users className="h-8 w-8" />
            Team Members
          </h1>
          <p className="text-muted-foreground">
            Manage your organization's team members and invitations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowInviteDialog(true)}>
            <UserPlus className="mr-2 h-4 w-4" />
            Invite Member
          </Button>
          <Button onClick={fetchData} variant="outline" disabled={isLoading}>
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

      {/* Members List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Organization Members
          </CardTitle>
          <CardDescription>
            {members.length} member{members.length !== 1 ? "s" : ""} in your organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {members.map((member) => {
              const roleInfo = roleBadges[member.role] || { label: member.role, variant: "outline" as const }
              const isCurrentUser = member.id === user?.id

              return (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <span className="text-sm font-medium text-primary">
                        {(member.name || member.email).charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {member.name || member.email.split("@")[0]}
                        </span>
                        {isCurrentUser && (
                          <Badge variant="outline" className="text-xs">
                            You
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Mail className="h-3 w-3" />
                        {member.email}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <Badge variant={roleInfo.variant}>{roleInfo.label}</Badge>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                        <Clock className="h-3 w-3" />
                        Joined {formatDate(member.created_at)}
                      </div>
                    </div>

                    {!isCurrentUser && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openRoleDialog(member)}>
                            <UserCog className="mr-2 h-4 w-4" />
                            Change Role
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => openRemoveDialog(member)}
                            className="text-red-600"
                          >
                            <UserX className="mr-2 h-4 w-4" />
                            Remove Member
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </div>
              )
            })}

            {members.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No members found</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pending Invitations */}
      {pendingInvitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Pending Invitations
            </CardTitle>
            <CardDescription>
              {pendingInvitations.length} pending invitation
              {pendingInvitations.length !== 1 ? "s" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pendingInvitations.map((invite) => {
                const statusInfo = statusBadges[invite.status] || {
                  label: invite.status,
                  color: "bg-gray-100 text-gray-800",
                }
                const roleInfo = roleBadges[invite.role] || {
                  label: invite.role,
                  variant: "outline" as const,
                }

                return (
                  <div
                    key={invite.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-full bg-yellow-100 flex items-center justify-center">
                        <Mail className="h-5 w-5 text-yellow-600" />
                      </div>
                      <div>
                        <div className="font-medium">{invite.email}</div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>Invited by {invite.invited_by_name || "Admin"}</span>
                          <span>•</span>
                          <span>Expires {formatDate(invite.expires_at)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="flex items-center gap-2">
                          <Badge variant={roleInfo.variant}>{roleInfo.label}</Badge>
                          <Badge className={statusInfo.color}>{statusInfo.label}</Badge>
                        </div>
                      </div>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => copyInviteToken(invite)}>
                            {copiedInviteId === invite.id ? (
                              <>
                                <Check className="mr-2 h-4 w-4" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <Copy className="mr-2 h-4 w-4" />
                                Copy Invite Link
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleRevokeInvite(invite.id)}
                            className="text-red-600"
                          >
                            <UserX className="mr-2 h-4 w-4" />
                            Revoke Invitation
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Invite Member Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Team Member</DialogTitle>
            <DialogDescription>
              Send an invitation to join your organization. They will receive
              access once they accept the invitation.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="colleague@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select value={inviteRole} onValueChange={setInviteRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">
                    <div className="flex flex-col">
                      <span>Admin</span>
                      <span className="text-xs text-muted-foreground">
                        Full access including team management
                      </span>
                    </div>
                  </SelectItem>
                  <SelectItem value="member">
                    <div className="flex flex-col">
                      <span>Member</span>
                      <span className="text-xs text-muted-foreground">
                        Can upload, process, and validate drawings
                      </span>
                    </div>
                  </SelectItem>
                  <SelectItem value="viewer">
                    <div className="flex flex-col">
                      <span>Viewer</span>
                      <span className="text-xs text-muted-foreground">
                        Read-only access to view and export
                      </span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {inviteError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-700">{inviteError}</p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowInviteDialog(false)}
              disabled={isInviting}
            >
              Cancel
            </Button>
            <Button onClick={handleInvite} disabled={!inviteEmail || isInviting}>
              {isInviting ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Send Invitation
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Change Role Dialog */}
      <Dialog open={showRoleDialog} onOpenChange={setShowRoleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Member Role</DialogTitle>
            <DialogDescription>
              Update the role for {selectedMember?.name || selectedMember?.email}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="newRole">New Role</Label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRoleDialog(false)}
              disabled={isUpdatingRole}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRoleChange}
              disabled={!newRole || newRole === selectedMember?.role || isUpdatingRole}
            >
              {isUpdatingRole ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update Role"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove Member Dialog */}
      <Dialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Remove Team Member
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to remove{" "}
              <strong>{memberToRemove?.name || memberToRemove?.email}</strong> from
              your organization?
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
              <p className="text-sm text-yellow-800">
                This action will deactivate the user's account. They will lose
                access to all organization resources immediately.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRemoveDialog(false)}
              disabled={isRemoving}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRemoveMember}
              disabled={isRemoving}
            >
              {isRemoving ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Removing...
                </>
              ) : (
                <>
                  <UserX className="mr-2 h-4 w-4" />
                  Remove Member
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
