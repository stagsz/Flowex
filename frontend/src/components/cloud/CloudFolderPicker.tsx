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
import { CloudConnection, CloudFolder, useCloudStore } from "@/stores/cloudStore"

interface CloudFolderPickerProps {
  open: boolean
  onClose: () => void
  connection: CloudConnection | null
  onSelect: (folderId: string, folderName: string) => void
  filesToExport?: string[]
}

export function CloudFolderPicker({
  open,
  onClose,
  connection,
  onSelect,
  filesToExport = [],
}: CloudFolderPickerProps) {
  const {
    browse,
    browseResult,
    isLoading,
    folderHistory,
    goBack,
    createFolder,
  } = useCloudStore()

  const [newFolderName, setNewFolderName] = useState("")
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [selectedFolder, setSelectedFolder] = useState<CloudFolder | null>(null)

  useEffect(() => {
    if (open && connection) {
      browse(connection.id)
      setSelectedFolder(null)
      setNewFolderName("")
      setShowNewFolder(false)
    }
  }, [open, connection])

  const handleFolderClick = (folder: CloudFolder) => {
    if (connection) {
      browse(connection.id, folder.id)
    }
  }

  const handleCreateFolder = async () => {
    if (connection && newFolderName.trim()) {
      const parentId = browseResult?.currentFolder?.id || "root"
      await createFolder(connection.id, parentId, newFolderName.trim())
      setNewFolderName("")
      setShowNewFolder(false)
    }
  }

  const handleSelect = () => {
    const folder = browseResult?.currentFolder
    if (folder) {
      onSelect(folder.id, folder.name)
      onClose()
    }
  }

  const displayFolders = browseResult?.folders || []

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-lg max-h-[70vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            Export to{" "}
            {connection?.provider === "google_drive"
              ? "Google Drive"
              : connection?.provider === "sharepoint"
              ? "SharePoint"
              : "OneDrive"}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col">
          <p className="text-sm text-muted-foreground mb-3">
            Select destination folder:
          </p>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3 bg-muted p-2 rounded">
            <span className="text-lg">📁</span>
            <button
              onClick={() => connection && browse(connection.id)}
              className="hover:text-foreground"
            >
              Root
            </button>
            {folderHistory.map((folder) => (
              <span key={folder.id} className="flex items-center gap-2">
                <span>&gt;</span>
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

          {/* Folder list */}
          <div className="flex-1 overflow-auto border rounded-md min-h-[200px]">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : (
              <div className="divide-y">
                {folderHistory.length > 0 && (
                  <div
                    className="flex items-center gap-2 p-3 hover:bg-muted/50 cursor-pointer"
                    onClick={goBack}
                  >
                    <span className="text-lg">📁</span>
                    <span>..</span>
                  </div>
                )}
                {displayFolders.map((folder) => (
                  <div
                    key={folder.id}
                    className="flex items-center gap-2 p-3 hover:bg-muted/50 cursor-pointer"
                    onClick={() => handleFolderClick(folder)}
                  >
                    <span className="text-lg">📁</span>
                    <span>{folder.name}</span>
                    <span className="text-xs text-muted-foreground ml-auto">
                      {folder.childCount > 0 && `${folder.childCount} items`}
                    </span>
                  </div>
                ))}
                {displayFolders.length === 0 && !isLoading && (
                  <div className="p-4 text-center text-muted-foreground">
                    No subfolders
                  </div>
                )}
              </div>
            )}
          </div>

          {/* New folder */}
          <div className="mt-3">
            {showNewFolder ? (
              <div className="flex gap-2">
                <Input
                  placeholder="Folder name"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                  autoFocus
                />
                <Button onClick={handleCreateFolder} disabled={isLoading}>
                  Create
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setShowNewFolder(false)
                    setNewFolderName("")
                  }}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowNewFolder(true)}
              >
                + New Folder
              </Button>
            )}
          </div>

          {/* Files to export */}
          {filesToExport.length > 0 && (
            <div className="mt-4 p-3 bg-muted rounded-md">
              <p className="text-sm font-medium mb-2">Files to export:</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                {filesToExport.map((file, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <span>•</span>
                    <span>{file}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSelect}
            disabled={isLoading || !browseResult?.currentFolder}
          >
            Export to Folder
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
