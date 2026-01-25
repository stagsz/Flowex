import { useState, useEffect } from "react"
import { Check, TrendingUp, AlertCircle, Loader2, ExternalLink } from "lucide-react"
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
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/stores/authStore"
import { api } from "@/lib/api"
import type { UsageStats } from "@/components/UsageStatsCard"

interface PlanFeature {
  name: string
  free: boolean | string
  starter: boolean | string
  professional: boolean | string
  enterprise: boolean | string
}

const planFeatures: PlanFeature[] = [
  { name: "P&IDs per month", free: "5", starter: "20", professional: "50", enterprise: "Unlimited" },
  { name: "Projects", free: "1", starter: "5", professional: "Unlimited", enterprise: "Unlimited" },
  { name: "Team members", free: "1", starter: "3", professional: "10", enterprise: "Unlimited" },
  { name: "Cloud integrations", free: false, starter: true, professional: true, enterprise: true },
  { name: "Export to DXF", free: true, starter: true, professional: true, enterprise: true },
  { name: "Data list exports", free: false, starter: true, professional: true, enterprise: true },
  { name: "Priority support", free: false, starter: false, professional: true, enterprise: true },
  { name: "SSO / SAML", free: false, starter: false, professional: false, enterprise: true },
  { name: "Custom training", free: false, starter: false, professional: false, enterprise: true },
  { name: "Dedicated account manager", free: false, starter: false, professional: false, enterprise: true },
]

const planPricing: Record<string, { price: string; period: string }> = {
  free: { price: "€0", period: "forever" },
  starter: { price: "€29", period: "per month" },
  professional: { price: "€99", period: "per month" },
  enterprise: { price: "Custom", period: "contact sales" },
}

function formatPlanName(plan: string): string {
  const planNames: Record<string, string> = {
    free: "Free",
    starter: "Starter",
    professional: "Professional",
    enterprise: "Enterprise",
  }
  return planNames[plan.toLowerCase()] || plan.charAt(0).toUpperCase() + plan.slice(1)
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

function FeatureValue({ value }: { value: boolean | string }) {
  if (typeof value === "boolean") {
    return value ? (
      <Check className="h-5 w-5 text-green-600" />
    ) : (
      <span className="text-muted-foreground">—</span>
    )
  }
  return <span className="font-medium">{value}</span>
}

export function SettingsBillingPage() {
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
          throw new Error("Failed to fetch billing info")
        }

        const data = await response.json()
        setUsage(data)
      } catch (err) {
        console.error("Error fetching usage stats:", err)
        setError("Unable to load billing information")
      } finally {
        setIsLoading(false)
      }
    }

    fetchUsage()
  }, [user?.organizationId])

  const handleContactSales = () => {
    window.open("mailto:sales@flowex.io?subject=Enterprise%20Plan%20Inquiry", "_blank")
  }

  const handleUpgrade = (plan: string) => {
    // In production, this would open a payment modal or redirect to Stripe
    // For now, show contact information
    if (plan === "enterprise") {
      handleContactSales()
    } else {
      window.open(
        `mailto:sales@flowex.io?subject=Upgrade%20to%20${formatPlanName(plan)}%20Plan`,
        "_blank"
      )
    }
  }

  if (isLoading) {
    return (
      <div className="container max-w-6xl py-8">
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container max-w-6xl py-8">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-lg text-muted-foreground">{error}</p>
          <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
            Try again
          </Button>
        </div>
      </div>
    )
  }

  const currentPlan = usage?.plan?.toLowerCase() || "free"
  const usagePercentage = usage ? Math.round((usage.used_count / usage.plan_limit) * 100) : 0
  const isNearLimit = usagePercentage >= 80
  const isAtLimit = usagePercentage >= 100

  return (
    <div className="container max-w-6xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Billing & Plans</h1>
        <p className="text-muted-foreground mt-2">
          Manage your subscription and view usage details.
        </p>
      </div>

      {/* Current Plan Overview */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Current Plan
              <Badge variant="secondary">{formatPlanName(currentPlan)}</Badge>
            </CardTitle>
            <CardDescription>
              {usage?.organization_name || "Your organization"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {usage && (
              <>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">P&IDs used this period</span>
                    <span className="font-medium">
                      {usage.used_count} / {usage.plan_limit}
                    </span>
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

                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div>
                    <p className="text-sm text-muted-foreground">Period start</p>
                    <p className="font-medium">{formatDate(usage.period_start)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Resets on</p>
                    <p className="font-medium">{formatDate(usage.period_end)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Team members</p>
                    <p className="font-medium">{usage.member_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Remaining P&IDs</p>
                    <p className="font-medium">{usage.remaining_count}</p>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Need more P&IDs?</CardTitle>
            <CardDescription>
              Upgrade your plan to unlock more features and capacity.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Our plans are designed to grow with your business. Upgrade anytime to:
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-600" />
                Process more P&IDs each month
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-600" />
                Add more team members
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-600" />
                Access advanced features
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-600" />
                Get priority support
              </li>
            </ul>
          </CardContent>
          <CardFooter>
            <Button className="w-full" onClick={handleContactSales}>
              <ExternalLink className="mr-2 h-4 w-4" />
              Contact Sales
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* Plan Comparison */}
      <Card>
        <CardHeader>
          <CardTitle>Compare Plans</CardTitle>
          <CardDescription>
            Choose the plan that best fits your team's needs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-4 px-2 font-medium">Feature</th>
                  {["free", "starter", "professional", "enterprise"].map((plan) => (
                    <th key={plan} className="text-center py-4 px-4">
                      <div className="space-y-1">
                        <p className={`font-medium ${currentPlan === plan ? "text-primary" : ""}`}>
                          {formatPlanName(plan)}
                          {currentPlan === plan && (
                            <Badge variant="outline" className="ml-2 text-xs">
                              Current
                            </Badge>
                          )}
                        </p>
                        <p className="text-2xl font-bold">{planPricing[plan].price}</p>
                        <p className="text-xs text-muted-foreground">{planPricing[plan].period}</p>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {planFeatures.map((feature, index) => (
                  <tr key={index} className="border-b last:border-0">
                    <td className="py-3 px-2 text-sm">{feature.name}</td>
                    <td className="py-3 px-4 text-center">
                      <FeatureValue value={feature.free} />
                    </td>
                    <td className="py-3 px-4 text-center">
                      <FeatureValue value={feature.starter} />
                    </td>
                    <td className="py-3 px-4 text-center">
                      <FeatureValue value={feature.professional} />
                    </td>
                    <td className="py-3 px-4 text-center">
                      <FeatureValue value={feature.enterprise} />
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td className="py-4 px-2"></td>
                  {["free", "starter", "professional", "enterprise"].map((plan) => (
                    <td key={plan} className="py-4 px-4 text-center">
                      {currentPlan === plan ? (
                        <Button variant="outline" disabled className="w-full">
                          Current plan
                        </Button>
                      ) : (
                        <Button
                          variant={plan === "professional" ? "default" : "outline"}
                          className="w-full"
                          onClick={() => handleUpgrade(plan)}
                        >
                          {plan === "enterprise" ? (
                            <>Contact sales</>
                          ) : (
                            <>
                              <TrendingUp className="mr-2 h-4 w-4" />
                              Upgrade
                            </>
                          )}
                        </Button>
                      )}
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* FAQ Section */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium">Can I change my plan at any time?</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately,
              and we'll prorate your billing accordingly.
            </p>
          </div>
          <div>
            <h4 className="font-medium">What happens if I exceed my P&ID limit?</h4>
            <p className="text-sm text-muted-foreground mt-1">
              You'll be notified when approaching your limit. Once reached, you'll need to upgrade
              or wait for your next billing period to continue processing new P&IDs.
            </p>
          </div>
          <div>
            <h4 className="font-medium">Do unused P&IDs roll over?</h4>
            <p className="text-sm text-muted-foreground mt-1">
              No, unused P&IDs do not roll over to the next billing period. Each period starts
              fresh with your plan's full allocation.
            </p>
          </div>
          <div>
            <h4 className="font-medium">How do I cancel my subscription?</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Contact our support team to cancel your subscription. Your access will continue
              until the end of your current billing period.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsBillingPage
