import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  CloudConnection,
  CloudFile,
  CloudFolder,
  useCloudStore,
} from "@/stores/cloudStore"

interface CloudFilePickerProps {
  open: boolean
  onClose: () => void
  connection: CloudConnection | null
  onImport: (files: CloudFile[]) => void
  pdfOnly?: boolean
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export function CloudFilePicker({
  open,
  onClose,
  connection,
  onImport,
  pdfOnly = true,
}: CloudFilePickerProps) {
  const {
    browse,
    search,
    browseResult,
    selectedFiles,
    selectFile,
    deselectFile,
    clearSelection,
    isLoading,
    folderHistory,
    goBack,
  } = useCloudStore()

  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<CloudFile[] | null>(null)

  useEffect(() => {
    if (open && connection) {
      browse(connection.id)
      clearSelection()
      setSearchQuery("")
      setSearchResults(null)
    }
  }, [open, connection, browse, clearSelection])

  const handleFolderClick = (folder: CloudFolder) => {
    if (connection) {
      browse(connection.id, folder.id)
      setSearchResults(null)
    }
  }

  const handleFileToggle = (file: CloudFile) => {
    if (selectedFiles.some((f) => f.id === file.id)) {
      deselectFile(file.id)
    } else {
      selectFile(file)
    }
  }

  const handleSearch = async () => {
    if (connection && searchQuery.trim()) {
      const results = await search(
        connection.id,
        searchQuery,
        pdfOnly ? "pdf" : undefined
      )
      setSearchResults(results)
    }
  }

  const handleClearSearch = () => {
    setSearchQuery("")
    setSearchResults(null)
  }

  const handleImport = () => {
    if (selectedFiles.length > 0) {
      onImport(selectedFiles)
      clearSelection()
      onClose()
    }
  }

  const displayFiles = searchResults || browseResult?.files || []
  const displayFolders = searchResults ? [] : browseResult?.folders || []
  const filteredFiles = pdfOnly
    ? displayFiles.filter((f) => f.mimeType === "application/pdf")
    : displayFiles

  const totalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0)

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            Import from{" "}
            {connection?.provider === "google_drive"
              ? "Google Drive"
              : connection?.provider === "sharepoint"
              ? "SharePoint"
              : "OneDrive"}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
            <button
              onClick={() => connection && browse(connection.id)}
              className="hover:text-foreground"
            >
              Root
            </button>
            {folderHistory.map((folder) => (
              <span key={folder.id} className="flex items-center gap-2">
                <span>/</span>
                <button
                  onClick={() =>
                    connection && browse(connection.id, folder.id)
                  }
                  className="hover:text-foreground"
                >
                  {folder.name}
                </button>
              </span>
            ))}
          </div>

          {/* Search */}
          <div className="flex gap-2 mb-3">
            <Input
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={isLoading}>
              Search
            </Button>
            {searchResults && (
              <Button variant="ghost" onClick={handleClearSearch}>
                Clear
              </Button>
            )}
          </div>

          {pdfOnly && (
            <div className="text-xs text-muted-foreground mb-2">
              Showing PDF files only
            </div>
          )}

          {/* File list */}
          <div className="flex-1 overflow-auto border rounded-md">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted">
                  <tr className="border-b">
                    <th className="text-left p-2 w-8">
                      <input
                        type="checkbox"
                        checked={
                          filteredFiles.length > 0 &&
                          filteredFiles.every((f) =>
                            selectedFiles.some((s) => s.id === f.id)
                          )
                        }
                        onChange={(e) => {
                          if (e.target.checked) {
                            filteredFiles.forEach((f) => {
                              if (!selectedFiles.some((s) => s.id === f.id)) {
                                selectFile(f)
                              }
                            })
                          } else {
                            filteredFiles.forEach((f) => deselectFile(f.id))
                          }
                        }}
                      />
                    </th>
                    <th className="text-left p-2">Name</th>
                    <th className="text-left p-2 w-24">Size</th>
                    <th className="text-left p-2 w-32">Modified</th>
                  </tr>
                </thead>
                <tbody>
                  {folderHistory.length > 0 && !searchResults && (
                    <tr
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      onClick={goBack}
                    >
                      <td className="p-2" />
                      <td className="p-2 flex items-center gap-2">
                        <span className="text-lg">📁</span>
                        <span>..</span>
                      </td>
                      <td className="p-2 text-muted-foreground">-</td>
                      <td className="p-2 text-muted-foreground">-</td>
                    </tr>
                  )}
                  {displayFolders.map((folder) => (
                    <tr
                      key={folder.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      onClick={() => handleFolderClick(folder)}
                    >
                      <td className="p-2" />
                      <td className="p-2 flex items-center gap-2">
                        <span className="text-lg">📁</span>
                        <span>{folder.name}</span>
                      </td>
                      <td className="p-2 text-muted-foreground">-</td>
                      <td className="p-2 text-muted-foreground">-</td>
                    </tr>
                  ))}
                  {filteredFiles.map((file) => (
                    <tr
                      key={file.id}
                      className={`border-b hover:bg-muted/50 cursor-pointer ${
                        selectedFiles.some((f) => f.id === file.id)
                          ? "bg-primary/10"
                          : ""
                      }`}
                      onClick={() => handleFileToggle(file)}
                    >
                      <td className="p-2">
                        <input
                          type="checkbox"
                          checked={selectedFiles.some((f) => f.id === file.id)}
                          onChange={() => handleFileToggle(file)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                      <td className="p-2 flex items-center gap-2">
                        <span className="text-lg">📄</span>
                        <span className="truncate max-w-xs">{file.name}</span>
                      </td>
                      <td className="p-2 text-muted-foreground">
                        {formatFileSize(file.size)}
                      </td>
                      <td className="p-2 text-muted-foreground">
                        {formatDate(file.modifiedAt)}
                      </td>
                    </tr>
                  ))}
                  {!isLoading &&
                    displayFolders.length === 0 &&
                    filteredFiles.length === 0 && (
                      <tr>
                        <td
                          colSpan={4}
                          className="p-8 text-center text-muted-foreground"
                        >
                          {searchResults
                            ? "No files found"
                            : pdfOnly
                            ? "No PDF files in this folder"
                            : "This folder is empty"}
                        </td>
                      </tr>
                    )}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <DialogFooter className="flex justify-between items-center">
          <div className="text-sm text-muted-foreground">
            {selectedFiles.length > 0 && (
              <>
                {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""}{" "}
                selected ({formatFileSize(totalSize)})
              </>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              onClick={handleImport}
              disabled={selectedFiles.length === 0 || isLoading}
            >
              Import Selected
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
