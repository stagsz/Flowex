import { create } from "zustand"
import { persist } from "zustand/middleware"

export type CloudProvider = "onedrive" | "sharepoint" | "google_drive"

export interface CloudConnection {
  id: string
  provider: CloudProvider
  accountEmail: string
  accountName: string | null
  siteName: string | null
  connectedAt: string
  lastUsedAt: string | null
}

export interface CloudFile {
  id: string
  name: string
  path: string
  size: number
  mimeType: string
  modifiedAt: string
  thumbnailUrl?: string
}

export interface CloudFolder {
  id: string
  name: string
  path: string
  childCount: number
}

export interface BrowseResult {
  currentFolder: CloudFolder | null
  folders: CloudFolder[]
  files: CloudFile[]
}

// Last accessed folder info to remember user's browsing position
export interface LastAccessedFolder {
  folderId: string
  folderName: string
  folderPath: string
  accessedAt: string
}

interface CloudState {
  connections: CloudConnection[]
  isLoading: boolean
  error: string | null
  currentConnection: CloudConnection | null
  browseResult: BrowseResult | null
  selectedFiles: CloudFile[]
  folderHistory: CloudFolder[]
  // Persisted: map of connectionId -> last accessed folder
  lastAccessedFolders: Record<string, LastAccessedFolder>

  // Actions
  fetchConnections: () => Promise<void>
  connect: (provider: string) => Promise<void>
  disconnect: (connectionId: string) => Promise<void>
  browse: (connectionId: string, folderId?: string) => Promise<void>
  search: (connectionId: string, query: string, fileType?: string) => Promise<CloudFile[]>
  selectFile: (file: CloudFile) => void
  deselectFile: (fileId: string) => void
  clearSelection: () => void
  setCurrentConnection: (connection: CloudConnection | null) => void
  goBack: () => void
  importFiles: (connectionId: string, fileIds: string[], projectId: string) => Promise<string>
  exportFiles: (connectionId: string, drawingId: string, folderId: string, files: string[]) => Promise<string>
  createFolder: (connectionId: string, parentId: string, name: string) => Promise<CloudFolder>
  getLastAccessedFolder: (connectionId: string) => LastAccessedFolder | null
}

const API_BASE = "/api/v1/cloud"

export const useCloudStore = create<CloudState>()(
  persist(
    (set, get) => ({
  connections: [],
  isLoading: false,
  error: null,
  currentConnection: null,
  browseResult: null,
  selectedFiles: [],
  folderHistory: [],
  lastAccessedFolders: {},

  fetchConnections: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/connections`, {
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to fetch connections")
      const connections = await response.json()
      set({ connections, isLoading: false })
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  connect: async (provider: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/connections/${provider}/connect`, {
        method: "POST",
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to initiate connection")
      const { auth_url } = await response.json()
      // Redirect to OAuth provider
      window.location.href = auth_url
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  disconnect: async (connectionId: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/connections/${connectionId}`, {
        method: "DELETE",
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to disconnect")
      set((state) => ({
        connections: state.connections.filter((c) => c.id !== connectionId),
        isLoading: false,
        currentConnection:
          state.currentConnection?.id === connectionId ? null : state.currentConnection,
      }))
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  browse: async (connectionId: string, folderId?: string) => {
    set({ isLoading: true, error: null })
    try {
      const url = new URL(`${API_BASE}/connections/${connectionId}/browse`, window.location.origin)
      if (folderId) url.searchParams.set("folder_id", folderId)

      const response = await fetch(url.toString(), {
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to browse folder")
      const result: BrowseResult = await response.json()

      // Update folder history and save last accessed folder
      const currentFolder = result.currentFolder
      if (currentFolder) {
        set((state) => {
          const history = [...state.folderHistory]
          // If navigating back, don't add to history
          if (!folderId || !history.some((f) => f.id === currentFolder.id)) {
            if (folderId) {
              history.push(currentFolder)
            } else {
              // Reset history when going to root
              return { browseResult: result, isLoading: false, folderHistory: [] }
            }
          }
          // Save last accessed folder for this connection
          const lastAccessedFolders = {
            ...state.lastAccessedFolders,
            [connectionId]: {
              folderId: currentFolder.id,
              folderName: currentFolder.name,
              folderPath: currentFolder.path,
              accessedAt: new Date().toISOString(),
            },
          }
          return { browseResult: result, isLoading: false, folderHistory: history, lastAccessedFolders }
        })
      } else {
        // At root, clear last accessed folder
        set((state) => {
          const { [connectionId]: _, ...restFolders } = state.lastAccessedFolders
          return { browseResult: result, isLoading: false, lastAccessedFolders: restFolders }
        })
      }
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  search: async (connectionId: string, query: string, fileType?: string) => {
    set({ isLoading: true, error: null })
    try {
      const url = new URL(`${API_BASE}/connections/${connectionId}/search`, window.location.origin)
      url.searchParams.set("query", query)
      if (fileType) url.searchParams.set("file_type", fileType)

      const response = await fetch(url.toString(), {
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to search files")
      const files: CloudFile[] = await response.json()
      set({ isLoading: false })
      return files
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
      return []
    }
  },

  selectFile: (file: CloudFile) => {
    set((state) => ({
      selectedFiles: [...state.selectedFiles, file],
    }))
  },

  deselectFile: (fileId: string) => {
    set((state) => ({
      selectedFiles: state.selectedFiles.filter((f) => f.id !== fileId),
    }))
  },

  clearSelection: () => {
    set({ selectedFiles: [] })
  },

  setCurrentConnection: (connection: CloudConnection | null) => {
    set({ currentConnection: connection, browseResult: null, folderHistory: [], selectedFiles: [] })
  },

  goBack: () => {
    const { folderHistory, currentConnection } = get()
    if (folderHistory.length <= 1) {
      // Go to root
      if (currentConnection) {
        get().browse(currentConnection.id)
      }
      set({ folderHistory: [] })
    } else {
      // Go to previous folder
      const newHistory = folderHistory.slice(0, -1)
      const previousFolder = newHistory[newHistory.length - 1]
      set({ folderHistory: newHistory })
      if (currentConnection && previousFolder) {
        get().browse(currentConnection.id, previousFolder.id)
      }
    }
  },

  importFiles: async (connectionId: string, fileIds: string[], projectId: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/connections/${connectionId}/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ file_ids: fileIds, project_id: projectId }),
      })
      if (!response.ok) throw new Error("Failed to start import")
      const { job_id } = await response.json()
      set({ isLoading: false, selectedFiles: [] })
      return job_id
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
      throw error
    }
  },

  exportFiles: async (
    connectionId: string,
    drawingId: string,
    folderId: string,
    files: string[]
  ) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/connections/${connectionId}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ drawing_id: drawingId, folder_id: folderId, files }),
      })
      if (!response.ok) throw new Error("Failed to start export")
      const { job_id } = await response.json()
      set({ isLoading: false })
      return job_id
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
      throw error
    }
  },

  createFolder: async (connectionId: string, parentId: string, name: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/connections/${connectionId}/folders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ parent_id: parentId, name }),
      })
      if (!response.ok) throw new Error("Failed to create folder")
      const folder: CloudFolder = await response.json()
      // Refresh browse results
      await get().browse(connectionId, parentId)
      set({ isLoading: false })
      return folder
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
      throw error
    }
  },

  getLastAccessedFolder: (connectionId: string) => {
    return get().lastAccessedFolders[connectionId] || null
  },
}),
    {
      name: "flowex-cloud-storage",
      // Only persist the lastAccessedFolders map
      partialize: (state) => ({
        lastAccessedFolders: state.lastAccessedFolders,
      }),
    }
  )
)
