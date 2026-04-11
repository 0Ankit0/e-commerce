'use client';

import { useEffect, useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  useResetSmsQuotaCounters,
  useSmsQuotaConfig,
  useSmsQuotaDashboard,
  useSmsQuotaViolations,
  useUpdateSmsQuotaConfig,
} from '@/hooks/use-system';

export default function CommunicationsQuotasPage() {
  const provider = 'default';
  const configQuery = useSmsQuotaConfig(provider);
  const dashboardQuery = useSmsQuotaDashboard(provider);
  const violationsQuery = useSmsQuotaViolations(provider);
  const updateConfig = useUpdateSmsQuotaConfig();
  const resetCounters = useResetSmsQuotaCounters();

  const [perUserDailyLimit, setPerUserDailyLimit] = useState('100');
  const [perIpWindowLimit, setPerIpWindowLimit] = useState('25');
  const [ipWindowSeconds, setIpWindowSeconds] = useState('300');
  const [providerDailyLimit, setProviderDailyLimit] = useState('10000');

  useEffect(() => {
    if (!configQuery.data) return;
    setPerUserDailyLimit(String(configQuery.data.per_user_daily_limit ?? ''));
    setPerIpWindowLimit(String(configQuery.data.per_ip_window_limit ?? ''));
    setIpWindowSeconds(String(configQuery.data.ip_window_seconds));
    setProviderDailyLimit(String(configQuery.data.global_provider_daily_limit ?? ''));
  }, [configQuery.data]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>SMS quota policy editor</CardTitle>
          <CardDescription>Configure per-user/day, per-IP/window, and global provider caps.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          <Input value={perUserDailyLimit} onChange={(event) => setPerUserDailyLimit(event.target.value)} placeholder="Per user/day" />
          <Input value={perIpWindowLimit} onChange={(event) => setPerIpWindowLimit(event.target.value)} placeholder="Per IP/window" />
          <Input value={ipWindowSeconds} onChange={(event) => setIpWindowSeconds(event.target.value)} placeholder="IP window seconds" />
          <Input value={providerDailyLimit} onChange={(event) => setProviderDailyLimit(event.target.value)} placeholder="Provider/day" />
          <Button
            onClick={() =>
              updateConfig.mutate({
                provider,
                per_user_daily_limit: Number(perUserDailyLimit),
                per_ip_window_limit: Number(perIpWindowLimit),
                ip_window_seconds: Number(ipWindowSeconds),
                global_provider_daily_limit: Number(providerDailyLimit),
                privileged_override_enabled: true,
              })
            }
          >
            Save quota policy
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quota dashboard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border p-3 text-sm">Counters: {dashboardQuery.data?.totals.counters ?? 0}</div>
            <div className="rounded-xl border p-3 text-sm">Violations: {dashboardQuery.data?.totals.violations ?? 0}</div>
            <div className="rounded-xl border p-3 text-sm">Override violations: {dashboardQuery.data?.totals.override_violations ?? 0}</div>
          </div>
          <div className="space-y-2 text-sm">
            {Object.entries(dashboardQuery.data?.usage_by_scope ?? {}).map(([scope, count]) => (
              <p key={scope}>
                {scope}: {count}
              </p>
            ))}
          </div>
          <Button variant="outline" onClick={() => resetCounters.mutate(provider)}>Reset counters</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent quota violations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(violationsQuery.data ?? []).slice(0, 30).map((row) => (
            <p key={row.id}>
              [{row.scope}] attempted {row.attempted_count}/{row.limit_count} · override: {row.override_applied ? 'yes' : 'no'}
            </p>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
