import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/stores/authStore"
import {
  LayoutDashboard,
  FolderKanban,
  FileImage,
  Upload,
  Settings,
  HelpCircle,
  Shield,
  ScrollText,
} from "lucide-react"

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", href: "/projects", icon: FolderKanban },
  { name: "Drawings", href: "/drawings", icon: FileImage },
  { name: "Upload", href: "/upload", icon: Upload },
]

const secondaryNavigation = [
  { name: "Settings", href: "/settings/integrations", icon: Settings },
  { name: "Help", href: "/help", icon: HelpCircle },
]

const adminNavigation = [
  { name: "Beta Admin", href: "/admin/beta", icon: Shield },
  { name: "Audit Logs", href: "/admin/audit-logs", icon: ScrollText },
]

export function Sidebar() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === "admin" || user?.role === "owner"
  return (
    <aside className="hidden md:flex md:w-64 md:flex-col">
      <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r bg-background px-6 py-4">
        <nav className="flex flex-1 flex-col">
          <ul role="list" className="flex flex-1 flex-col gap-y-7">
            <li>
              <ul role="list" className="-mx-2 space-y-1">
                {navigation.map((item) => (
                  <li key={item.name}>
                    <NavLink
                      to={item.href}
                      className={({ isActive }) =>
                        cn(
                          "group flex gap-x-3 rounded-md p-2 text-sm font-medium leading-6 transition-colors",
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )
                      }
                    >
                      <item.icon className="h-5 w-5 shrink-0" />
                      {item.name}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
            {isAdmin && (
              <li>
                <div className="text-xs font-semibold leading-6 text-muted-foreground">
                  Admin
                </div>
                <ul role="list" className="-mx-2 mt-2 space-y-1">
                  {adminNavigation.map((item) => (
                    <li key={item.name}>
                      <NavLink
                        to={item.href}
                        className={({ isActive }) =>
                          cn(
                            "group flex gap-x-3 rounded-md p-2 text-sm font-medium leading-6 transition-colors",
                            isActive
                              ? "bg-primary text-primary-foreground"
                              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                          )
                        }
                      >
                        <item.icon className="h-5 w-5 shrink-0" />
                        {item.name}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </li>
            )}
            <li className="mt-auto">
              <ul role="list" className="-mx-2 space-y-1">
                {secondaryNavigation.map((item) => (
                  <li key={item.name}>
                    <NavLink
                      to={item.href}
                      className={({ isActive }) =>
                        cn(
                          "group flex gap-x-3 rounded-md p-2 text-sm font-medium leading-6 transition-colors",
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )
                      }
                    >
                      <item.icon className="h-5 w-5 shrink-0" />
                      {item.name}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
          </ul>
        </nav>
      </div>
    </aside>
  )
}
