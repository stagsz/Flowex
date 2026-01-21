import { useState, useCallback, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  Upload,
  FileUp,
  X,
  CheckCircle,
  AlertCircle,
  File,
  Plus,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

interface UploadFile {
  id: string
  file: File
  progress: number
  status: "pending" | "uploading" | "completed" | "failed"
  error?: string
  drawingId?: string
}

interface Project {
  id: string
  name: string
}

export function UploadPage() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<UploadFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedProject, setSelectedProject] = useState("")
  const [projects, setProjects] = useState<Project[]>([])
  const [, setLoadingProjects] = useState(true)
  const [showCreateProject, setShowCreateProject] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [createProjectError, setCreateProjectError] = useState<string | null>(null)

  // Fetch projects from API
  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await api.get("/api/v1/projects/")
        if (response.ok) {
          const data = await response.json()
          setProjects(data.map((p: { id: string; name: string }) => ({ id: p.id, name: p.name })))
        } else {
          // Fallback to mock data if API unavailable
          setProjects([
            { id: "1", name: "Refinery Unit A" },
            { id: "2", name: "Chemical Plant B" },
            { id: "3", name: "Power Station C" },
          ])
        }
      } catch {
        // Fallback to mock data
        setProjects([
          { id: "1", name: "Refinery Unit A" },
          { id: "2", name: "Chemical Plant B" },
          { id: "3", name: "Power Station C" },
        ])
      } finally {
        setLoadingProjects(false)
      }
    }
    fetchProjects()
  }, [])

  const createProject = async () => {
    if (!newProjectName.trim() || isCreatingProject) return

    setIsCreatingProject(true)
    setCreateProjectError(null)
    try {
      const response = await api.post("/api/v1/projects/", {
        name: newProjectName.trim(),
      })
      if (response.ok) {
        const data = await response.json()
        const newProject = { id: data.id, name: data.name }
        setProjects((prev) => [...prev, newProject])
        setSelectedProject(data.id)
        setNewProjectName("")
        setShowCreateProject(false)
      } else {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.detail || `Error: ${response.status} ${response.statusText}`
        setCreateProjectError(errorMessage)
        console.error("Failed to create project:", errorMessage)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Network error - please check your connection"
      setCreateProjectError(errorMessage)
      console.error("Failed to create project:", err)
    } finally {
      setIsCreatingProject(false)
    }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.type === "application/pdf"
    )

    addFiles(droppedFiles)
  }, [])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        const selectedFiles = Array.from(e.target.files).filter(
          (file) => file.type === "application/pdf"
        )
        addFiles(selectedFiles)
      }
    },
    []
  )

  const addFiles = (newFiles: File[]) => {
    const uploadFiles: UploadFile[] = newFiles.map((file) => ({
      id: Math.random().toString(36).substring(7),
      file,
      progress: 0,
      status: "pending",
    }))
    setFiles((prev) => [...prev, ...uploadFiles])
  }

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const uploadFiles = async () => {
    if (!selectedProject) {
      alert("Please select a project")
      return
    }

    for (const uploadFile of files) {
      if (uploadFile.status !== "pending") continue

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, status: "uploading", progress: 10 } : f
        )
      )

      try {
        // Create FormData for file upload
        const formData = new FormData()
        formData.append("file", uploadFile.file)

        // Upload to backend API (uses authenticated fetch)
        const response = await api.post(
          `/api/v1/drawings/upload/${selectedProject}`,
          formData
        )

        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, progress: 90 } : f
          )
        )

        if (response.ok) {
          const data = await response.json()
          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id
                ? { ...f, status: "completed", progress: 100, drawingId: data.id }
                : f
            )
          )
        } else {
          const errorData = await response.json().catch(() => ({ detail: "Upload failed" }))
          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id
                ? { ...f, status: "failed", error: errorData.detail || "Upload failed" }
                : f
            )
          )
        }
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? { ...f, status: "failed", error: "Network error - is the backend running?" }
              : f
          )
        )
      }
    }
  }

  const allCompleted = files.length > 0 && files.every((f) => f.status === "completed")
  const hasFiles = files.length > 0
  const pendingFiles = files.filter((f) => f.status === "pending").length

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload P&ID</h1>
        <p className="text-muted-foreground">
          Upload PDF files for AI-powered digitization
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Project</CardTitle>
          <CardDescription>
            Choose which project to add the drawings to
          </CardDescription>
        </CardHeader>
        <CardContent>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="">Select a project...</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>

          {!showCreateProject ? (
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => setShowCreateProject(true)}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create New Project
            </Button>
          ) : (
            <div className="mt-3 space-y-2">
              <div className="flex gap-2">
                <Input
                  placeholder="Project name"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createProject()}
                />
                <Button onClick={createProject} disabled={isCreatingProject || !newProjectName.trim()}>
                  {isCreatingProject ? "Creating..." : "Create"}
                </Button>
                <Button variant="ghost" onClick={() => {
                  setShowCreateProject(false)
                  setCreateProjectError(null)
                }}>
                  Cancel
                </Button>
              </div>
              {createProjectError && (
                <p className="text-sm text-destructive">{createProjectError}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Upload Files</CardTitle>
          <CardDescription>
            Drag and drop PDF files or click to browse
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
              isDragOver
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-muted-foreground/50"
            )}
          >
            <FileUp className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-1">
              Drop PDF files here or click to browse
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              Maximum file size: 50MB per file
            </p>
            <Input
              type="file"
              accept=".pdf,application/pdf"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <Button asChild variant="outline">
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="mr-2 h-4 w-4" />
                Browse Files
              </label>
            </Button>
          </div>

          {hasFiles && (
            <div className="mt-6 space-y-3">
              <h4 className="font-medium">Files ({files.length})</h4>
              {files.map((uploadFile) => (
                <div
                  key={uploadFile.id}
                  className="flex items-center gap-3 p-3 rounded-lg border bg-muted/50"
                >
                  <File className="h-8 w-8 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{uploadFile.file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                    {uploadFile.status === "uploading" && (
                      <Progress value={uploadFile.progress} className="mt-2 h-1" />
                    )}
                    {uploadFile.error && (
                      <p className="text-xs text-destructive mt-1">
                        {uploadFile.error}
                      </p>
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    {uploadFile.status === "completed" && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                    {uploadFile.status === "failed" && (
                      <AlertCircle className="h-5 w-5 text-red-500" />
                    )}
                    {uploadFile.status === "pending" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(uploadFile.id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-4">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
        {allCompleted ? (
          <Button onClick={() => navigate("/drawings")}>
            View Drawings
          </Button>
        ) : (
          <Button
            onClick={uploadFiles}
            disabled={pendingFiles === 0 || !selectedProject}
          >
            <Upload className="mr-2 h-4 w-4" />
            Upload {pendingFiles > 0 ? `(${pendingFiles})` : ""}
          </Button>
        )}
      </div>
    </div>
  )
}
