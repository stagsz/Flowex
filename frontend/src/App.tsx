import { useEffect } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import * as Sentry from "@sentry/react"
import { MainLayout } from "@/components/layout"
import {
  LoginPage,
  AuthCallbackPage,
  DashboardPage,
  ProjectsPage,
  DrawingsPage,
  UploadPage,
  ValidationPage,
  SettingsIntegrationsPage,
} from "@/pages"
import { useAuthStore } from "@/stores/authStore"

function ErrorFallback({ error, resetError }: { error: Error; resetError: () => void }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-6 p-6 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Something went wrong</h1>
          <p className="mt-2 text-sm text-gray-600">
            We've been notified of the issue and are working to fix it.
          </p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-700 font-mono break-all">
            {error.message}
          </p>
        </div>
        <div className="flex justify-center space-x-4">
          <button
            onClick={resetError}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
          >
            Try again
          </button>
          <button
            onClick={() => window.location.href = '/dashboard'}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, token, isLoading, checkAuth } = useAuthStore()

  useEffect(() => {
    // If we have a token but no user, verify the token
    if (token && !user && !isLoading) {
      checkAuth()
    }
  }, [token, user, isLoading, checkAuth])

  if (isLoading || (token && !user)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <ErrorFallback error={error} resetError={resetError} />
      )}
      onError={(error) => {
        console.error("Caught by Sentry ErrorBoundary:", error)
      }}
    >
      <BrowserRouter>
        <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />

        {/* Protected routes with layout */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/drawings" element={<DrawingsPage />} />
          <Route path="/drawings/:drawingId/validate" element={<ValidationPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/settings/integrations" element={<SettingsIntegrationsPage />} />
        </Route>

        {/* Redirects */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
    </Sentry.ErrorBoundary>
  )
}

export default App
