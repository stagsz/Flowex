import { useState, useEffect } from "react"
import { TrendingUp, AlertCircle, Loader2 } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/stores/authStore"
import { api } from "@/lib/api"

export interface UsageStats {
  organization_id: string
  organization_name: string
  period_start: string
  period_end: string
  plan: string
  plan_limit: number
  used_count: number
  remaining_count: number
  member_count: number
}

interface UsageStatsCardProps {
  className?: string
  onUpgrade?: () => void
}

function formatPlanName(plan: string): string {
  // Capitalize first letter and handle common plan names
  const planNames: Record<string, string> = {
    free: "Free Plan",
    starter: "Starter Plan",
    professional: "Professional Plan",
    enterprise: "Enterprise Plan",
  }
  return planNames[plan.toLowerCase()] || plan.charAt(0).toUpperCase() + plan.slice(1) + " Plan"
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function UsageStatsCard({ className, onUpgrade }: UsageStatsCardProps) {
  const { user } = useAuthStore()
  const [usage, setUsage] = useState<UsageStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchUsage() {
      if (!user?.organizationId) {
        setIsLoading(false)
        return
      }

      try {
        setIsLoading(true)
        setError(null)
        const response = await api.get(`/api/v1/organizations/${user.organizationId}/usage`)

        if (!response.ok) {
          throw new Error("Failed to fetch usage stats")
        }

        const data = await response.json()
        setUsage(data)
      } catch (err) {
        console.error("Error fetching usage stats:", err)
        setError("Unable to load usage stats")
      } finally {
        setIsLoading(false)
      }
    }

    fetchUsage()
  }, [user?.organizationId])

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error || !usage) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <AlertCircle className="h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">{error || "Usage data unavailable"}</p>
        </CardContent>
      </Card>
    )
  }

  const usagePercentage = Math.round((usage.used_count / usage.plan_limit) * 100)
  const isNearLimit = usagePercentage >= 80
  const isAtLimit = usagePercentage >= 100

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">Usage This Month</CardTitle>
        <CardDescription>{formatPlanName(usage.plan)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl font-bold">
              {usage.used_count}/{usage.plan_limit}
            </span>
            <span className="text-sm text-muted-foreground">P&IDs</span>
          </div>
          <Progress
            value={Math.min(usagePercentage, 100)}
            className={isAtLimit ? "[&>div]:bg-destructive" : isNearLimit ? "[&>div]:bg-yellow-500" : ""}
          />
          {isNearLimit && !isAtLimit && (
            <p className="text-xs text-yellow-600 mt-1 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              Approaching limit ({usage.remaining_count} remaining)
            </p>
          )}
          {isAtLimit && (
            <p className="text-xs text-destructive mt-1 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              Limit reached. Upgrade to continue processing.
            </p>
          )}
        </div>

        <div className="text-xs text-muted-foreground">
          Resets: {formatDate(usage.period_end)}
        </div>
      </CardContent>
      <CardFooter>
        <Button
          variant="outline"
          className="w-full"
          onClick={onUpgrade}
        >
          <TrendingUp className="mr-2 h-4 w-4" />
          Upgrade Plan
        </Button>
      </CardFooter>
    </Card>
  )
}
