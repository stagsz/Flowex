import { useEffect } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
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
  )
}

export default App
