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
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  FolderKanban,
  Plus,
  Search,
  FileImage,
  MoreVertical,
  Loader2,
  Pencil,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { api } from "@/lib/api"

interface Project {
  id: string
  name: string
  description: string
  drawingCount: number
  createdAt: string
  updatedAt: string
  isArchived: boolean
}

export function ProjectsPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")
  const [newProjectDescription, setNewProjectDescription] = useState("")
  const [error, setError] = useState<string | null>(null)

  // Edit project state
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [editProjectName, setEditProjectName] = useState("")
  const [editProjectDescription, setEditProjectDescription] = useState("")
  const [isUpdating, setIsUpdating] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Fetch projects from API
  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await api.get("/api/v1/projects/")
        if (response.ok) {
          const data = await response.json()
          setProjects(
            data.map((p: {
              id: string
              name: string
              description?: string
              drawing_count?: number
              is_archived?: boolean
              created_at?: string
              updated_at?: string
            }) => ({
              id: p.id,
              name: p.name,
              description: p.description || "",
              drawingCount: p.drawing_count || 0,
              createdAt: p.created_at ? new Date(p.created_at).toLocaleDateString() : "",
              updatedAt: p.updated_at ? new Date(p.updated_at).toLocaleDateString() : "",
              isArchived: p.is_archived || false,
            }))
          )
        }
      } catch {
        // API unavailable, show empty state
        setProjects([])
      } finally {
        setLoading(false)
      }
    }
    fetchProjects()
  }, [])

  const createProject = async () => {
    if (!newProjectName.trim() || isCreating) return

    setIsCreating(true)
    setError(null)
    try {
      const response = await api.post("/api/v1/projects/", {
        name: newProjectName.trim(),
        description: newProjectDescription.trim(),
      })
      if (response.ok) {
        const data = await response.json()
        const newProject: Project = {
          id: data.id,
          name: data.name,
          description: data.description || "",
          drawingCount: 0,
          createdAt: new Date().toLocaleDateString(),
          updatedAt: new Date().toLocaleDateString(),
          isArchived: false,
        }
        setProjects((prev) => [newProject, ...prev])
        setNewProjectName("")
        setNewProjectDescription("")
        setIsDialogOpen(false)
      } else {
        // Handle API error responses
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.detail || `Error: ${response.status} ${response.statusText}`
        setError(errorMessage)
        console.error("Failed to create project:", errorMessage)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Network error - please check your connection"
      setError(errorMessage)
      console.error("Failed to create project:", err)
    } finally {
      setIsCreating(false)
    }
  }

  const deleteProject = async (projectId: string) => {
    try {
      const response = await api.delete(`/api/v1/projects/${projectId}`)
      if (response.ok) {
        setProjects((prev) => prev.filter((p) => p.id !== projectId))
      }
    } catch {
      // Handle error silently
    }
  }

  const openEditDialog = (project: Project) => {
    setEditingProject(project)
    setEditProjectName(project.name)
    setEditProjectDescription(project.description)
    setEditError(null)
    setIsEditDialogOpen(true)
  }

  const updateProject = async () => {
    if (!editingProject || !editProjectName.trim() || isUpdating) return

    setIsUpdating(true)
    setEditError(null)
    try {
      const response = await api.patch(`/api/v1/projects/${editingProject.id}`, {
        name: editProjectName.trim(),
        description: editProjectDescription.trim(),
      })
      if (response.ok) {
        const data = await response.json()
        setProjects((prev) =>
          prev.map((p) =>
            p.id === editingProject.id
              ? {
                  ...p,
                  name: data.name,
                  description: data.description || "",
                  updatedAt: new Date().toLocaleDateString(),
                }
              : p
          )
        )
        setIsEditDialogOpen(false)
        setEditingProject(null)
      } else {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.detail || `Error: ${response.status} ${response.statusText}`
        setEditError(errorMessage)
        console.error("Failed to update project:", errorMessage)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Network error - please check your connection"
      setEditError(errorMessage)
      console.error("Failed to update project:", err)
    } finally {
      setIsUpdating(false)
    }
  }

  const filteredProjects = projects.filter(
    (project) =>
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">
            Manage your P&ID digitization projects
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open)
          if (!open) setError(null)
        }}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Create a new project to organize your P&ID drawings.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="project-name">Project Name</Label>
                <Input
                  id="project-name"
                  name="project-name"
                  autoComplete="off"
                  placeholder="e.g., Refinery Unit A"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createProject()}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="project-description">Description (optional)</Label>
                <Textarea
                  id="project-description"
                  name="project-description"
                  autoComplete="off"
                  placeholder="Brief description of the project..."
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                />
              </div>
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={createProject}
                disabled={isCreating || !newProjectName.trim()}
              >
                {isCreating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  "Create Project"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {filteredProjects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderKanban className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">No projects found</h3>
            <p className="text-muted-foreground text-center max-w-sm mt-1">
              {searchQuery
                ? "Try a different search term"
                : "Get started by creating your first project"}
            </p>
            {!searchQuery && (
              <Button className="mt-4" onClick={() => setIsDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Project
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredProjects.map((project) => (
            <Card key={project.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <div className="space-y-1">
                  <CardTitle className="text-lg">
                    <Link
                      to={`/drawings?project=${project.id}`}
                      className="hover:underline"
                    >
                      {project.name}
                    </Link>
                  </CardTitle>
                  <CardDescription>{project.description}</CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem asChild>
                      <Link to={`/drawings?project=${project.id}`}>View Drawings</Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to={`/upload?project=${project.id}`}>Upload Drawings</Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => openEditDialog(project)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="text-destructive"
                      onClick={() => deleteProject(project.id)}
                    >
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <FileImage className="h-4 w-4" />
                    <span>{project.drawingCount} drawings</span>
                  </div>
                  {project.updatedAt && <span>Updated {project.updatedAt}</span>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Project Dialog */}
      <Dialog
        open={isEditDialogOpen}
        onOpenChange={(open) => {
          setIsEditDialogOpen(open)
          if (!open) {
            setEditingProject(null)
            setEditError(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Project</DialogTitle>
            <DialogDescription>
              Update the project name and description.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-project-name">Project Name</Label>
              <Input
                id="edit-project-name"
                name="edit-project-name"
                autoComplete="off"
                placeholder="e.g., Refinery Unit A"
                value={editProjectName}
                onChange={(e) => setEditProjectName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && updateProject()}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-project-description">Description (optional)</Label>
              <Textarea
                id="edit-project-description"
                name="edit-project-description"
                autoComplete="off"
                placeholder="Brief description of the project..."
                value={editProjectDescription}
                onChange={(e) => setEditProjectDescription(e.target.value)}
              />
            </div>
          </div>
          {editError && <p className="text-sm text-destructive">{editError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={updateProject}
              disabled={isUpdating || !editProjectName.trim()}
            >
              {isUpdating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
