import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileCode2, GitBranch, Languages, ShieldAlert } from "lucide-react";

const placeholderStats = [
  { label: "Total Files", value: "—", icon: FileCode2 },
  { label: "Languages", value: "—", icon: Languages },
  { label: "Repositories", value: "—", icon: GitBranch },
  { label: "Open Findings", value: "—", icon: ShieldAlert },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Analytics will populate here once a repository is indexed.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {placeholderStats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
              <stat.icon className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Getting started</CardTitle>
          <CardDescription>
            Connect a GitHub repository or upload one to begin analysis, documentation, and chat.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          This is the foundation scaffold. Feature modules are wired in upcoming steps.
        </CardContent>
      </Card>
    </div>
  );
}
