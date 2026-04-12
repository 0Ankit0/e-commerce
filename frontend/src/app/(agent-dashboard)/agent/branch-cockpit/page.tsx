'use client';

import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useBranchDashboardAlerts, useBranchDashboardDrilldown, useBranchDashboardSnapshot } from '@/hooks/use-observability';

export default function AgentBranchCockpitPage() {
  const { data: snapshot } = useBranchDashboardSnapshot({ timezone: 'UTC' });
  const { data: drilldown } = useBranchDashboardDrilldown({ timezone: 'UTC' });
  const { data: alerts } = useBranchDashboardAlerts({ timezone: 'UTC' });

  return (
    <div className="space-y-6">
      <Card className="rounded-[28px]">
        <CardHeader>
          <CardTitle>Branch manager cockpit</CardTitle>
          <CardDescription>Single-screen workflow to monitor branch SLA risk and trigger interventions.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <p className="rounded-lg border p-3 text-sm">Inventory health: <strong>{snapshot?.snapshot.inventory_posture ?? 'healthy'}</strong></p>
          <p className="rounded-lg border p-3 text-sm">Undelivered aging (6h+): <strong>{snapshot?.snapshot.aging_queue_over_6h ?? 0}</strong></p>
          <p className="rounded-lg border p-3 text-sm">First-attempt success: <strong>{snapshot?.snapshot.first_attempt_success_rate_percent ?? 0}%</strong></p>
          <p className="rounded-lg border p-3 text-sm">Agent utilization: <strong>{snapshot?.snapshot.avg_agent_utilization_percent ?? 0}%</strong></p>
        </CardContent>
      </Card>

      <Card className="rounded-[28px]">
        <CardHeader>
          <CardTitle>Intervention queues</CardTitle>
          <CardDescription>Reassign agents, escalate delayed shipments, and prioritize aging deliveries.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm md:grid-cols-3">
          <div className="rounded-lg border p-3">
            <p className="font-medium">Reassign agent</p>
            <p className="text-xs text-[var(--text-muted)]">{drilldown?.actionable_queues?.reassign_agent.length ?? 0} candidates</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="font-medium">Escalate delayed</p>
            <p className="text-xs text-[var(--text-muted)]">{drilldown?.actionable_queues?.escalate_delayed.length ?? 0} delayed exceptions</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="font-medium">Prioritize aging</p>
            <p className="text-xs text-[var(--text-muted)]">{drilldown?.actionable_queues?.prioritize_aging.length ?? 0} pickups waiting</p>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[28px]">
        <CardHeader>
          <CardTitle>SLA alert hooks</CardTitle>
          <CardDescription>Threshold breaches and escalation hooks from backend branch SLA policy.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(alerts?.alerts ?? []).map((alert) => (
            <p key={alert.code} className="rounded-lg border p-3">{alert.message}</p>
          ))}
          {(alerts?.escalation_hooks ?? []).map((hook) => (
            <p key={hook.action} className="text-xs text-[var(--text-muted)]">{hook.action} → {hook.path}</p>
          ))}
          <Button asChild variant="outline"><Link href="/agent/history">Back to delivery history</Link></Button>
        </CardContent>
      </Card>
    </div>
  );
}
