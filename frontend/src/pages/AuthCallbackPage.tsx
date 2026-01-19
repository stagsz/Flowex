import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuthStore } from "@/stores/authStore"

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const { handleAuthCallback, error } = useAuthStore()

  useEffect(() => {
    handleAuthCallback().then(() => {
      // Redirect after callback is processed
      setTimeout(() => {
        navigate("/dashboard", { replace: true })
      }, 100)
    })
  }, [handleAuthCallback, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/40">
        <div className="text-center space-y-4">
          <div className="text-destructive text-lg font-medium">
            Authentication Error
          </div>
          <p className="text-muted-foreground">{error}</p>
          <a href="/login" className="text-primary underline">
            Back to Login
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40">
      <div className="text-center space-y-4">
        <svg
          className="animate-spin h-8 w-8 mx-auto text-primary"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <p className="text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  )
}
