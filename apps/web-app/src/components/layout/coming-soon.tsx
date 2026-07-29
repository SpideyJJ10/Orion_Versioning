import { Construction } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ComingSoonProps {
  title:        string;
  description?: string;
}

/**
 * Reusable placeholder for routes that are wired up in the navigation but
 * whose UI is still pending. Keeps the user informed without leaving an
 * empty screen on dead-end clicks.
 */
export function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="rounded-full bg-primary/10 p-4">
            <Construction className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold">{title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {description ??
                "This screen is on the roadmap. Track progress in CHANGELOG.md or ask the team for a delivery date."}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
