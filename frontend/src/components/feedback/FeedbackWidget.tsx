import { useState } from "react"
import { MessageSquarePlus, Bug, Lightbulb, Gauge, Smile, Star, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

type FeedbackType = "bug" | "feature_request" | "usability" | "performance" | "general"
type FeedbackPriority = "low" | "medium" | "high" | "critical"

const feedbackTypeOptions: { value: FeedbackType; label: string; icon: React.ReactNode }[] = [
  { value: "bug", label: "Bug Report", icon: <Bug className="h-4 w-4" /> },
  { value: "feature_request", label: "Feature Request", icon: <Lightbulb className="h-4 w-4" /> },
  { value: "usability", label: "Usability Issue", icon: <Smile className="h-4 w-4" /> },
  { value: "performance", label: "Performance", icon: <Gauge className="h-4 w-4" /> },
  { value: "general", label: "General Feedback", icon: <MessageSquarePlus className="h-4 w-4" /> },
]

const priorityOptions: { value: FeedbackPriority; label: string; color: string }[] = [
  { value: "low", label: "Low", color: "text-gray-500" },
  { value: "medium", label: "Medium", color: "text-yellow-500" },
  { value: "high", label: "High", color: "text-orange-500" },
  { value: "critical", label: "Critical", color: "text-red-500" },
]

interface FeedbackWidgetProps {
  drawingId?: string
  className?: string
}

export function FeedbackWidget({ drawingId, className }: FeedbackWidgetProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [feedbackType, setFeedbackType] = useState<FeedbackType>("general")
  const [priority, setPriority] = useState<FeedbackPriority>("medium")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [satisfactionRating, setSatisfactionRating] = useState<number | null>(null)

  const resetForm = () => {
    setFeedbackType("general")
    setPriority("medium")
    setTitle("")
    setDescription("")
    setSatisfactionRating(null)
    setError(null)
    setSubmitted(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const payload = {
        feedback_type: feedbackType,
        priority,
        title,
        description,
        drawing_id: drawingId || null,
        page_url: window.location.href,
        user_agent: navigator.userAgent,
        screen_size: `${window.innerWidth}x${window.innerHeight}`,
        satisfaction_rating: satisfactionRating,
      }

      const response = await api.post("/api/v1/feedback", payload)

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || "Failed to submit feedback")
      }

      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback")
    } finally {
      setLoading(false)
    }
  }

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen)
    if (!newOpen) {
      resetForm()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn("gap-2", className)}
          data-testid="feedback-button"
        >
          <MessageSquarePlus className="h-4 w-4" />
          <span className="hidden sm:inline">Feedback</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        {submitted ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-green-600">
                Thank you for your feedback!
              </DialogTitle>
              <DialogDescription>
                We appreciate you taking the time to help us improve Flowex. Our team
                will review your feedback and take appropriate action.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)}>Close</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Send Feedback</DialogTitle>
              <DialogDescription>
                Help us improve Flowex by sharing your thoughts, reporting bugs, or
                suggesting new features.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Feedback Type Selection */}
              <div className="grid grid-cols-5 gap-2">
                {feedbackTypeOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setFeedbackType(option.value)}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-md border p-2 text-xs transition-colors",
                      feedbackType === option.value
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-muted hover:border-primary/50"
                    )}
                    data-testid={`feedback-type-${option.value}`}
                  >
                    {option.icon}
                    <span className="text-center leading-tight">{option.label.split(" ")[0]}</span>
                  </button>
                ))}
              </div>

              {/* Title */}
              <div className="space-y-2">
                <Label htmlFor="feedback-title">Title</Label>
                <Input
                  id="feedback-title"
                  placeholder="Brief summary of your feedback"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  minLength={3}
                  maxLength={200}
                  data-testid="feedback-title"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="feedback-description">Description</Label>
                <Textarea
                  id="feedback-description"
                  placeholder="Please provide details about your feedback..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  minLength={10}
                  maxLength={5000}
                  rows={4}
                  data-testid="feedback-description"
                />
              </div>

              {/* Priority */}
              <div className="space-y-2">
                <Label htmlFor="feedback-priority">Priority</Label>
                <Select value={priority} onValueChange={(v) => setPriority(v as FeedbackPriority)}>
                  <SelectTrigger id="feedback-priority" data-testid="feedback-priority">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {priorityOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <span className={option.color}>{option.label}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Satisfaction Rating */}
              <div className="space-y-2">
                <Label>How would you rate your experience? (optional)</Label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((rating) => (
                    <button
                      key={rating}
                      type="button"
                      onClick={() => setSatisfactionRating(satisfactionRating === rating ? null : rating)}
                      className={cn(
                        "rounded-full p-1 transition-colors",
                        satisfactionRating && rating <= satisfactionRating
                          ? "text-yellow-500"
                          : "text-gray-300 hover:text-yellow-400"
                      )}
                      data-testid={`rating-${rating}`}
                    >
                      <Star
                        className="h-6 w-6"
                        fill={satisfactionRating && rating <= satisfactionRating ? "currentColor" : "none"}
                      />
                    </button>
                  ))}
                  {satisfactionRating && (
                    <button
                      type="button"
                      onClick={() => setSatisfactionRating(null)}
                      className="ml-2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <p className="text-sm text-destructive" data-testid="feedback-error">
                  {error}
                </p>
              )}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleOpenChange(false)}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={loading || !title || !description}
                  data-testid="submit-feedback"
                >
                  {loading ? "Submitting..." : "Submit Feedback"}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
