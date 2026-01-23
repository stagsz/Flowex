import { useEffect, lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import * as Sentry from "@sentry/react"
import { MainLayout } from "@/components/layout"
import { useAuthStore } from "@/stores/authStore"

// Lazy-loaded page components for code splitting
const LoginPage = lazy(() => import("@/pages/LoginPage").then(m => ({ default: m.LoginPage })))
const AuthCallbackPage = lazy(() => import("@/pages/AuthCallbackPage").then(m => ({ default: m.AuthCallbackPage })))
const DashboardPage = lazy(() => import("@/pages/DashboardPage").then(m => ({ default: m.DashboardPage })))
const ProjectsPage = lazy(() => import("@/pages/ProjectsPage").then(m => ({ default: m.ProjectsPage })))
const DrawingsPage = lazy(() => import("@/pages/DrawingsPage").then(m => ({ default: m.DrawingsPage })))
const UploadPage = lazy(() => import("@/pages/UploadPage").then(m => ({ default: m.UploadPage })))
const ValidationPage = lazy(() => import("@/pages/ValidationPage").then(m => ({ default: m.ValidationPage })))
const SettingsIntegrationsPage = lazy(() => import("@/pages/SettingsIntegrationsPage").then(m => ({ default: m.SettingsIntegrationsPage })))
const BetaAdminPage = lazy(() => import("@/pages/BetaAdminPage").then(m => ({ default: m.BetaAdminPage })))
const AuditLogsPage = lazy(() => import("@/pages/AuditLogsPage").then(m => ({ default: m.AuditLogsPage })))

function PageLoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
}

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
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Suspense fallback={<PageLoadingFallback />}>
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
              <Route path="/admin/beta" element={<BetaAdminPage />} />
              <Route path="/admin/audit-logs" element={<AuditLogsPage />} />
            </Route>

            {/* Redirects */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </Sentry.ErrorBoundary>
  )
}

export default App
