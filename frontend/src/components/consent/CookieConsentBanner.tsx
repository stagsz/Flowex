import { useState, useEffect } from "react"
import { Cookie, Settings, Shield, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import {
  hasConsentDecision,
  acceptAllCookies,
  acceptNecessaryOnly,
  saveConsent,
  getConsent,
  COOKIE_CATEGORIES,
  type CookieConsent,
} from "@/lib/cookieConsent"

interface CookieConsentBannerProps {
  className?: string
}

type CategoryKey = "necessary" | "analytics" | "functional" | "marketing"

export function CookieConsentBanner({ className }: CookieConsentBannerProps) {
  const [showBanner, setShowBanner] = useState(false)
  const [showPreferences, setShowPreferences] = useState(false)
  const [preferences, setPreferences] = useState<Record<CategoryKey, boolean>>({
    necessary: true,
    analytics: false,
    functional: false,
    marketing: false,
  })

  useEffect(() => {
    // Check if user has already made a consent decision
    if (!hasConsentDecision()) {
      // Small delay to prevent flash during page load
      const timer = setTimeout(() => setShowBanner(true), 500)
      return () => clearTimeout(timer)
    }
  }, [])

  const handleAcceptAll = () => {
    acceptAllCookies()
    setShowBanner(false)
    setShowPreferences(false)
  }

  const handleAcceptNecessary = () => {
    acceptNecessaryOnly()
    setShowBanner(false)
    setShowPreferences(false)
  }

  const handleSavePreferences = () => {
    saveConsent(preferences as Partial<CookieConsent>)
    setShowBanner(false)
    setShowPreferences(false)
  }

  const handleOpenPreferences = () => {
    // Load current preferences when opening dialog
    const current = getConsent()
    setPreferences({
      necessary: true,
      analytics: current.analytics,
      functional: current.functional,
      marketing: current.marketing,
    })
    setShowPreferences(true)
  }

  const toggleCategory = (category: CategoryKey) => {
    if (category === "necessary") return // Cannot toggle necessary
    setPreferences((prev) => ({
      ...prev,
      [category]: !prev[category],
    }))
  }

  if (!showBanner && !showPreferences) return null

  return (
    <>
      {/* Cookie Banner */}
      {showBanner && !showPreferences && (
        <div
          className={cn(
            "fixed bottom-0 left-0 right-0 z-50 border-t bg-background p-4 shadow-lg md:p-6",
            className
          )}
          role="dialog"
          aria-labelledby="cookie-banner-title"
          aria-describedby="cookie-banner-description"
          data-testid="cookie-consent-banner"
        >
          <div className="mx-auto max-w-6xl">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="flex gap-4">
                <div className="hidden sm:block">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                    <Cookie className="h-6 w-6 text-primary" />
                  </div>
                </div>
                <div className="space-y-2">
                  <h2
                    id="cookie-banner-title"
                    className="text-lg font-semibold"
                  >
                    Cookie Settings
                  </h2>
                  <p
                    id="cookie-banner-description"
                    className="text-sm text-muted-foreground"
                  >
                    We use cookies to provide essential functionality and improve
                    your experience. You can accept all cookies, customize your
                    preferences, or accept only necessary cookies.{" "}
                    <a
                      href="/privacy"
                      className="text-primary underline hover:text-primary/80"
                    >
                      Learn more in our Privacy Policy
                    </a>
                    .
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleOpenPreferences}
                  className="gap-2"
                  data-testid="cookie-customize-button"
                >
                  <Settings className="h-4 w-4" />
                  Customize
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAcceptNecessary}
                  data-testid="cookie-reject-button"
                >
                  Necessary Only
                </Button>
                <Button
                  size="sm"
                  onClick={handleAcceptAll}
                  data-testid="cookie-accept-button"
                >
                  Accept All
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preferences Dialog */}
      <Dialog open={showPreferences} onOpenChange={setShowPreferences}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Cookie Preferences
            </DialogTitle>
            <DialogDescription>
              Manage your cookie preferences below. Some cookies are necessary
              for the website to function and cannot be disabled.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {(Object.entries(COOKIE_CATEGORIES) as [CategoryKey, typeof COOKIE_CATEGORIES[CategoryKey]][]).map(
              ([key, category]) => (
                <div
                  key={key}
                  className="flex items-start justify-between gap-4 rounded-lg border p-4"
                  data-testid={`cookie-category-${key}`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{category.name}</h3>
                      {!category.canDisable && (
                        <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                          Required
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {category.description}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={preferences[key]}
                      aria-label={`Toggle ${category.name} cookies`}
                      disabled={!category.canDisable}
                      onClick={() => toggleCategory(key)}
                      className={cn(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                        preferences[key]
                          ? "bg-primary"
                          : "bg-input",
                        !category.canDisable && "cursor-not-allowed opacity-50"
                      )}
                      data-testid={`cookie-toggle-${key}`}
                    >
                      <span
                        className={cn(
                          "inline-block h-4 w-4 transform rounded-full bg-background shadow-sm transition-transform",
                          preferences[key] ? "translate-x-6" : "translate-x-1"
                        )}
                      />
                    </button>
                  </div>
                </div>
              )
            )}
          </div>

          <DialogFooter className="flex-col gap-2 sm:flex-row">
            <Button
              variant="outline"
              onClick={() => setShowPreferences(false)}
              className="w-full sm:w-auto"
            >
              <X className="mr-2 h-4 w-4" />
              Cancel
            </Button>
            <Button
              variant="outline"
              onClick={handleAcceptNecessary}
              className="w-full sm:w-auto"
            >
              Necessary Only
            </Button>
            <Button
              onClick={handleSavePreferences}
              className="w-full sm:w-auto"
              data-testid="cookie-save-preferences"
            >
              Save Preferences
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
