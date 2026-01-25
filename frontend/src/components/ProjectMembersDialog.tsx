import { useCallback, useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { api } from "@/lib/api"
import {
  Users,
  UserPlus,
  RefreshCw,
  MoreVertical,
  Mail,
  Clock,
  UserX,
  UserCog,
  AlertTriangle,
  Crown,
} from "lucide-react"

// Types matching backend API
interface ProjectMember {
  id: string
  user_id: string
  user_email: string
  user_name: string | null
  role: string
  added_at: string
  added_by_name: string | null
}

interface MemberListResponse {
  items: ProjectMember[]
  total: number
  page: number
  page_size: number
}

interface MyMembershipResponse {
  id: string
  user_id: string
  user_email: string
  user_name: string | null
  role: string
  added_at: string
  added_by_name: string | null
}

// Role badges with colors
const roleBadges: Record<
  string,
  { label: string; variant: "default" | "secondary" | "outline" }
> = {
  owner: { label: "Owner", variant: "default" },
  editor: { label: "Editor", variant: "secondary" },
  viewer: { label: "Viewer", variant: "outline" },
}

interface ProjectMembersDialogProps {
  projectId: string
  projectName: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ProjectMembersDialog({
  projectId,
  projectName,
  open,
  onOpenChange,
}: ProjectMembersDialogProps) {
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Current user's membership for permission checks
  const [myMembership, setMyMembership] = useState<MyMembershipResponse | null>(
    null
  )

  // Add member dialog state
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [addEmail, setAddEmail] = useState("")
  const [addRole, setAddRole] = useState<string>("editor")
  const [isAdding, setIsAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  // Role change dialog state
  const [showRoleDialog, setShowRoleDialog] = useState(false)
  const [selectedMember, setSelectedMember] = useState<ProjectMember | null>(
    null
  )
  const [newRole, setNewRole] = useState<string>("")
  const [isUpdatingRole, setIsUpdatingRole] = useState(false)
  const [roleError, setRoleError] = useState<string | null>(null)

  // Remove member dialog state
  const [showRemoveDialog, setShowRemoveDialog] = useState(false)
  const [memberToRemove, setMemberToRemove] = useState<ProjectMember | null>(
    null
  )
  const [isRemoving, setIsRemoving] = useState(false)

  // Check if current user is an owner
  const isOwner = myMembership?.role === "owner"

  const fetchMembers = useCallback(async () => {
    try {
      const res = await api.get(
        `/api/v1/projects/${projectId}/members?page_size=100`
      )
      if (!res.ok) {
        throw new Error("Failed to fetch project members")
      }
      const data: MemberListResponse = await res.json()
      setMembers(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members")
    }
  }, [projectId])

  const fetchMyMembership = useCallback(async () => {
    try {
      const res = await api.get(`/api/v1/projects/${projectId}/members/me`)
      if (res.ok) {
        const data: MyMembershipResponse | null = await res.json()
        setMyMembership(data)
      }
    } catch {
      // Non-member, ignore
    }
  }, [projectId])

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    await Promise.all([fetchMembers(), fetchMyMembership()])
    setIsLoading(false)
  }, [fetchMembers, fetchMyMembership])

  useEffect(() => {
    if (open) {
      fetchData()
    }
  }, [open, fetchData])

  const handleAddMember = async () => {
    if (!addEmail || !projectId) return

    setIsAdding(true)
    setAddError(null)

    try {
      const res = await api.post(`/api/v1/projects/${projectId}/members/by-email`, {
        email: addEmail,
        role: addRole,
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || "Failed to add member")
      }

      // Refresh members list
      await fetchMembers()
      setShowAddDialog(false)
      setAddEmail("")
      setAddRole("editor")
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add member")
    } finally {
      setIsAdding(false)
    }
  }

  const handleRoleChange = async () => {
    if (!selectedMember || !newRole || !projectId) return

    setIsUpdatingRole(true)
    setRoleError(null)

    try {
      const res = await api.patch(
        `/api/v1/projects/${projectId}/members/${selectedMember.id}`,
        { role: newRole }
      )

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || "Failed to update role")
      }

      // Refresh members list and my membership (in case role changed)
      await Promise.all([fetchMembers(), fetchMyMembership()])
      setShowRoleDialog(false)
      setSelectedMember(null)
      setNewRole("")
    } catch (err) {
      setRoleError(err instanceof Error ? err.message : "Failed to update role")
    } finally {
      setIsUpdatingRole(false)
    }
  }

  const handleRemoveMember = async () => {
    if (!memberToRemove || !projectId) return

    setIsRemoving(true)

    try {
      const res = await api.delete(
        `/api/v1/projects/${projectId}/members/${memberToRemove.id}`
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

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const openRoleDialog = (member: ProjectMember) => {
    setSelectedMember(member)
    setNewRole(member.role)
    setRoleError(null)
    setShowRoleDialog(true)
  }

  const openRemoveDialog = (member: ProjectMember) => {
    setMemberToRemove(member)
    setShowRemoveDialog(true)
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Project Members
            </DialogTitle>
            <DialogDescription>
              Manage team members for <strong>{projectName}</strong>
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-4">
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <p className="text-sm text-red-700">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={fetchData}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Retry
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {members.map((member) => {
                  const roleInfo = roleBadges[member.role] || {
                    label: member.role,
                    variant: "outline" as const,
                  }
                  const isCurrentUser = member.user_id === myMembership?.user_id
                  const canModify = isOwner && !isCurrentUser

                  return (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary">
                            {(member.user_name || member.user_email)
                              .charAt(0)
                              .toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              {member.user_name ||
                                member.user_email.split("@")[0]}
                            </span>
                            {isCurrentUser && (
                              <Badge variant="outline" className="text-xs">
                                You
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Mail className="h-3 w-3" />
                            {member.user_email}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <div className="flex items-center gap-1">
                            {member.role === "owner" && (
                              <Crown className="h-3 w-3 text-yellow-600" />
                            )}
                            <Badge variant={roleInfo.variant}>
                              {roleInfo.label}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                            <Clock className="h-3 w-3" />
                            Added {formatDate(member.added_at)}
                          </div>
                        </div>

                        {canModify && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => openRoleDialog(member)}
                              >
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
            )}
          </div>

          <DialogFooter className="border-t pt-4">
            <div className="flex items-center justify-between w-full">
              <span className="text-sm text-muted-foreground">
                {members.length} member{members.length !== 1 ? "s" : ""}
              </span>
              <div className="flex gap-2">
                {isOwner && (
                  <Button onClick={() => setShowAddDialog(true)}>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Add Member
                  </Button>
                )}
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Member Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Project Member</DialogTitle>
            <DialogDescription>
              Add a team member to this project. They must already be a member
              of your organization.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="member-email">Email Address</Label>
              <Input
                id="member-email"
                type="email"
                placeholder="colleague@company.com"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="member-role">Role</Label>
              <Select value={addRole} onValueChange={setAddRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="owner">
                    <div className="flex flex-col">
                      <span>Owner</span>
                      <span className="text-xs text-muted-foreground">
                        Full access including member management
                      </span>
                    </div>
                  </SelectItem>
                  <SelectItem value="editor">
                    <div className="flex flex-col">
                      <span>Editor</span>
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

            {addError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-700">{addError}</p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowAddDialog(false)}
              disabled={isAdding}
            >
              Cancel
            </Button>
            <Button onClick={handleAddMember} disabled={!addEmail || isAdding}>
              {isAdding ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Add Member
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
              Update the role for{" "}
              {selectedMember?.user_name || selectedMember?.user_email}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="new-role">New Role</Label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="owner">Owner</SelectItem>
                  <SelectItem value="editor">Editor</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {roleError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-700">{roleError}</p>
              </div>
            )}
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
              disabled={
                !newRole || newRole === selectedMember?.role || isUpdatingRole
              }
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
              Remove Project Member
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to remove{" "}
              <strong>
                {memberToRemove?.user_name || memberToRemove?.user_email}
              </strong>{" "}
              from this project?
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
              <p className="text-sm text-yellow-800">
                This will revoke their access to this project immediately. They
                can be re-added later if needed.
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
    </>
  )
}
