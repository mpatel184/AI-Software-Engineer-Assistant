import {
  Bug,
  FileText,
  FlaskConical,
  FolderGit2,
  LayoutDashboard,
  MessageSquare,
  ScrollText,
  Settings,
  Shield,
  Telescope,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

/** Sidebar navigation, mirroring the 12 feature modules. */
export const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Repositories", href: "/repositories", icon: FolderGit2 },
  { label: "Analysis", href: "/analysis", icon: Telescope },
  { label: "Documentation", href: "/documentation", icon: FileText },
  { label: "Bug Detection", href: "/bugs", icon: Bug },
  { label: "Security", href: "/security", icon: Shield },
  { label: "Test Generator", href: "/tests", icon: FlaskConical },
  { label: "Chat", href: "/chat", icon: MessageSquare },
  { label: "Reports", href: "/reports", icon: ScrollText },
  { label: "Settings", href: "/settings", icon: Settings },
];
