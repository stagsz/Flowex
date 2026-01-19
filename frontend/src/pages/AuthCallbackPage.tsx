import { useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuthStore } from "@/stores/authStore"

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setToken, checkAuth, setError } = useAuthStore()

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get("token")
      const error = searchParams.get("error")

      if (error) {
        setError(decodeURIComponent(error))
        navigate("/login")
        return
      }

      if (token) {
        setToken(token)
        await checkAuth()
        navigate("/dashboard")
      } else {
        setError("No authentication token received")
        navigate("/login")
      }
    }

    handleCallback()
  }, [searchParams, setToken, checkAuth, setError, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40">
      <div className="text-center">
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
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <p className="mt-4 text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  )
}
