import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CloudConnectionCard } from "@/components/cloud/CloudConnectionCard"
import { useCloudStore } from "@/stores/cloudStore"

const providers = [
  {
    id: "onedrive",
    name: "Microsoft OneDrive",
    description: "Connect your OneDrive account to import and export files",
    color: "#0078D4",
    icon: "M",
  },
  {
    id: "sharepoint",
    name: "SharePoint",
    description: "Connect to SharePoint sites and document libraries",
    color: "#038387",
    icon: "S",
  },
  {
    id: "google_drive",
    name: "Google Drive",
    description: "Connect your Google Drive account to import and export files",
    color: "#4285F4",
    icon: "G",
  },
]

export function SettingsIntegrationsPage() {
  const { connections, fetchConnections, connect, isLoading, error } =
    useCloudStore()

  useEffect(() => {
    fetchConnections()
  }, [])

  // Check URL for OAuth callback result
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const success = params.get("success")
    const errorParam = params.get("error")

    if (success === "true") {
      // Refresh connections after successful OAuth
      fetchConnections()
      // Clean URL
      window.history.replaceState({}, "", window.location.pathname)
    } else if (errorParam) {
      alert(`Connection failed: ${errorParam}`)
      window.history.replaceState({}, "", window.location.pathname)
    }
  }, [])

  const getConnectedProvider = (providerId: string) => {
    return connections.find((c) => c.provider === providerId)
  }

  return (
    <div className="container max-w-4xl py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground mt-2">
            Connect your cloud storage accounts to import P&IDs and export
            results.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-destructive/10 text-destructive rounded-lg">
            {error}
          </div>
        )}

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Cloud Storage</CardTitle>
              <CardDescription>
                Connect your cloud storage accounts to seamlessly import and
                export files.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {providers.map((provider) => {
                  const connection = getConnectedProvider(provider.id)

                  if (connection) {
                    return (
                      <CloudConnectionCard
                        key={provider.id}
                        connection={connection}
                      />
                    )
                  }

                  return (
                    <Card
                      key={provider.id}
                      className="border-dashed hover:border-solid hover:border-primary/50 transition-colors"
                    >
                      <CardHeader className="pb-3">
                        <div className="flex items-center gap-3">
                          <div
                            className="flex h-10 w-10 items-center justify-center rounded-lg text-white font-bold"
                            style={{ backgroundColor: provider.color }}
                          >
                            {provider.icon}
                          </div>
                          <CardTitle className="text-base">
                            {provider.name}
                          </CardTitle>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground mb-4">
                          {provider.description}
                        </p>
                        <Button
                          onClick={() => connect(provider.id)}
                          disabled={isLoading}
                          className="w-full"
                        >
                          Connect {provider.name}
                        </Button>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Connected Accounts</CardTitle>
              <CardDescription>
                Your connected cloud storage accounts
              </CardDescription>
            </CardHeader>
            <CardContent>
              {connections.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No accounts connected yet. Connect a cloud storage provider
                  above to get started.
                </p>
              ) : (
                <div className="space-y-4">
                  {connections.map((connection) => (
                    <div
                      key={connection.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-2 rounded-full bg-green-500" />
                        <div>
                          <p className="font-medium">
                            {connection.provider === "google_drive"
                              ? "Google Drive"
                              : connection.provider === "sharepoint"
                              ? `SharePoint - ${connection.siteName}`
                              : "OneDrive"}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {connection.accountEmail}
                          </p>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Connected{" "}
                        {new Date(connection.connectedAt).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Usage Tips</CardTitle>
            </CardHeader>
            <CardContent className="prose prose-sm max-w-none">
              <ul className="space-y-2 text-muted-foreground">
                <li>
                  <strong>Import:</strong> Use the cloud import button on the
                  upload page to select files from your connected storage.
                </li>
                <li>
                  <strong>Export:</strong> After processing a drawing, use the
                  cloud export option to save results directly to your storage.
                </li>
                <li>
                  <strong>SharePoint:</strong> After connecting Microsoft, you
                  can configure specific SharePoint sites and document
                  libraries.
                </li>
                <li>
                  <strong>Security:</strong> Your connection tokens are
                  encrypted and stored securely. You can disconnect at any time.
                </li>
              </ul>
            </CardContent>
          </Card>
      </div>
    </div>
  )
}

export default SettingsIntegrationsPage
