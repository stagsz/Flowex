import { CloudConnection, useCloudStore } from "@/stores/cloudStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CloudConnectionCardProps {
  connection: CloudConnection
}

const providerInfo: Record<
  string,
  { name: string; icon: string; color: string }
> = {
  onedrive: {
    name: "Microsoft OneDrive",
    icon: "M12 2L2 7v3h10V7l8 4v6l-8 4v3l10-5v-3z",
    color: "#0078D4",
  },
  sharepoint: {
    name: "SharePoint",
    icon: "M12 2L2 7v3h10V7l8 4v6l-8 4v3l10-5v-3z",
    color: "#038387",
  },
  google_drive: {
    name: "Google Drive",
    icon: "M7.71 3.5L1.15 15l3.43 6h12.84l3.43-6-6.56-11.5zm1.42 1h5.74l5.58 9.5H14.7L7.13 4.5z",
    color: "#4285F4",
  },
}

export function CloudConnectionCard({ connection }: CloudConnectionCardProps) {
  const { disconnect, isLoading } = useCloudStore()
  const info = providerInfo[connection.provider] || {
    name: connection.provider,
    icon: "",
    color: "#666",
  }

  const handleDisconnect = async () => {
    if (confirm("Are you sure you want to disconnect this account?")) {
      await disconnect(connection.id)
    }
  }

  return (
    <Card className="relative">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-lg"
            style={{ backgroundColor: info.color + "20" }}
          >
            <svg
              viewBox="0 0 24 24"
              className="h-6 w-6"
              fill={info.color}
            >
              <path d={info.icon} />
            </svg>
          </div>
          <div>
            <CardTitle className="text-base">{info.name}</CardTitle>
            {connection.siteName && (
              <p className="text-xs text-muted-foreground">
                {connection.siteName}
              </p>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span className="text-sm">Connected as: {connection.accountEmail}</span>
          </div>
          {connection.accountName && (
            <p className="text-sm text-muted-foreground">
              {connection.accountName}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Connected: {new Date(connection.connectedAt).toLocaleDateString()}
          </p>
          {connection.lastUsedAt && (
            <p className="text-xs text-muted-foreground">
              Last used: {new Date(connection.lastUsedAt).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="mt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDisconnect}
            disabled={isLoading}
          >
            Disconnect
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
