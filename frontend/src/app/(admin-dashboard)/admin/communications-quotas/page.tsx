'use client';

import { useEffect, useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  useSmsQuotaIncidentExport,
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
  const incidentExportQuery = useSmsQuotaIncidentExport(provider);
  const updateConfig = useUpdateSmsQuotaConfig();
  const resetCounters = useResetSmsQuotaCounters();

  const [perUserDailyLimit, setPerUserDailyLimit] = useState('100');
  const [perTenantDailyLimit, setPerTenantDailyLimit] = useState('2500');
  const [perPhoneWindowLimit, setPerPhoneWindowLimit] = useState('5');
  const [phoneWindowSeconds, setPhoneWindowSeconds] = useState('600');
  const [perIpWindowLimit, setPerIpWindowLimit] = useState('25');
  const [ipWindowSeconds, setIpWindowSeconds] = useState('300');
  const [providerSoftDailyLimit, setProviderSoftDailyLimit] = useState('8000');
  const [providerDailyLimit, setProviderDailyLimit] = useState('10000');

  useEffect(() => {
    if (!configQuery.data) return;
    setPerUserDailyLimit(String(configQuery.data.per_user_daily_limit ?? ''));
    setPerTenantDailyLimit(String(configQuery.data.per_tenant_daily_limit ?? ''));
    setPerPhoneWindowLimit(String(configQuery.data.per_phone_window_limit ?? ''));
    setPhoneWindowSeconds(String(configQuery.data.phone_window_seconds));
    setPerIpWindowLimit(String(configQuery.data.per_ip_window_limit ?? ''));
    setIpWindowSeconds(String(configQuery.data.ip_window_seconds));
    setProviderSoftDailyLimit(String(configQuery.data.global_provider_soft_daily_limit ?? ''));
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
          <Input value={perTenantDailyLimit} onChange={(event) => setPerTenantDailyLimit(event.target.value)} placeholder="Per tenant/day" />
          <Input value={perPhoneWindowLimit} onChange={(event) => setPerPhoneWindowLimit(event.target.value)} placeholder="Per phone/window" />
          <Input value={phoneWindowSeconds} onChange={(event) => setPhoneWindowSeconds(event.target.value)} placeholder="Phone window seconds" />
          <Input value={perIpWindowLimit} onChange={(event) => setPerIpWindowLimit(event.target.value)} placeholder="Per IP/window" />
          <Input value={ipWindowSeconds} onChange={(event) => setIpWindowSeconds(event.target.value)} placeholder="IP window seconds" />
          <Input value={providerSoftDailyLimit} onChange={(event) => setProviderSoftDailyLimit(event.target.value)} placeholder="Provider soft/day" />
          <Input value={providerDailyLimit} onChange={(event) => setProviderDailyLimit(event.target.value)} placeholder="Provider/day" />
          <Button
            onClick={() =>
              updateConfig.mutate({
                provider,
                per_user_daily_limit: Number(perUserDailyLimit),
                per_tenant_daily_limit: Number(perTenantDailyLimit),
                per_phone_window_limit: Number(perPhoneWindowLimit),
                phone_window_seconds: Number(phoneWindowSeconds),
                per_ip_window_limit: Number(perIpWindowLimit),
                ip_window_seconds: Number(ipWindowSeconds),
                global_provider_soft_daily_limit: Number(providerSoftDailyLimit),
                global_provider_daily_limit: Number(providerDailyLimit),
                soft_throttle_action: 'delay',
                hard_throttle_action: 'block',
                soft_throttle_delay_seconds: 30,
                hard_throttle_delay_seconds: 0,
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
          <CardTitle>Usage trends and top offenders</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(dashboardQuery.data?.usage_trends ?? []).slice(0, 10).map((trend) => (
            <p key={`${trend.scope}-${trend.window_start}`}>
              {trend.scope}: {trend.usage_count} ({new Date(trend.window_start).toLocaleTimeString()} - {new Date(trend.window_end).toLocaleTimeString()})
            </p>
          ))}
          <div className="pt-2 text-xs text-muted-foreground">Top offenders</div>
          {(dashboardQuery.data?.top_offenders ?? []).slice(0, 10).map((offender) => (
            <p key={offender.id}>
              {offender.scope}: {offender.usage_count} · user {offender.user_id ?? '-'} · tenant {offender.tenant_id ?? '-'}
            </p>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent quota violations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(violationsQuery.data ?? []).slice(0, 30).map((row) => (
            <p key={row.id}>
              [{row.scope}/{row.severity}] attempted {row.attempted_count}/{row.limit_count} · action: {row.throttle_action} · override: {row.override_applied ? 'yes' : 'no'}
            </p>
          ))}
          <div className="pt-3 text-xs text-muted-foreground">
            Incident export rows ready: {incidentExportQuery.data?.count ?? 0}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
