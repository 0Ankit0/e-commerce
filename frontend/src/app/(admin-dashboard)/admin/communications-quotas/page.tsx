'use client';

import { useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  useChannelQuotaAudit,
  useChannelQuotaDashboard,
  useChannelQuotaPolicies,
  useChannelQuotaUsage,
  useCreateChannelQuotaPolicy,
  useOverrideChannelQuotaPolicy,
} from '@/hooks/use-system';

export default function CommunicationsQuotasPage() {
  const policiesQuery = useChannelQuotaPolicies();
  const usageQuery = useChannelQuotaUsage();
  const auditQuery = useChannelQuotaAudit();
  const dashboardQuery = useChannelQuotaDashboard();
  const createPolicy = useCreateChannelQuotaPolicy();
  const overridePolicy = useOverrideChannelQuotaPolicy();
  const [limitCount, setLimitCount] = useState('50');
  const [windowSeconds, setWindowSeconds] = useState('3600');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>SMS quota governance</CardTitle>
          <CardDescription>Create tenant/user/channel quotas and apply emergency overrides.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div>
            <p className="mb-1 text-xs text-[var(--text-muted)]">Limit</p>
            <Input value={limitCount} onChange={(event) => setLimitCount(event.target.value)} />
          </div>
          <div>
            <p className="mb-1 text-xs text-[var(--text-muted)]">Window seconds</p>
            <Input value={windowSeconds} onChange={(event) => setWindowSeconds(event.target.value)} />
          </div>
          <Button
            onClick={() =>
              createPolicy.mutate({ channel: 'sms', limit_count: Number(limitCount), window_seconds: Number(windowSeconds), timezone: 'UTC' })
            }
          >
            Add global policy
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Policies</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(policiesQuery.data ?? []).map((policy) => (
            <div key={policy.id} className="flex items-center justify-between rounded-xl border p-3">
              <div>
                <p className="font-medium">#{policy.id} · {policy.scope} · {policy.channel}</p>
                <p className="text-xs text-[var(--text-muted)]">{policy.limit_count} per {policy.window_seconds}s · {policy.enabled ? 'enabled' : 'disabled'}</p>
              </div>
              <Button
                variant="outline"
                onClick={() => overridePolicy.mutate({ policyId: policy.id, limit_count: policy.limit_count + 5, reason: 'manual bump' })}
              >
                +5 override
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usage dashboard</CardTitle>
          <CardDescription>Track active policies, saturation risk, and per-policy utilization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border p-3 text-sm">Policies: {dashboardQuery.data?.totals.policies ?? 0}</div>
            <div className="rounded-xl border p-3 text-sm">Active: {dashboardQuery.data?.totals.active_policies ?? 0}</div>
            <div className="rounded-xl border p-3 text-sm">Usage rows: {dashboardQuery.data?.totals.usage_rows ?? 0}</div>
            <div className="rounded-xl border p-3 text-sm">At risk (≥80%): {dashboardQuery.data?.totals.at_risk ?? 0}</div>
          </div>
          <div className="space-y-3">
            {(dashboardQuery.data?.items ?? []).slice(0, 12).map((item) => (
              <div key={item.policy_id} className="rounded-xl border p-3">
                <p className="text-sm font-medium">Policy #{item.policy_id} · {item.scope}</p>
                <p className="text-xs text-[var(--text-muted)]">
                  {item.usage_count}/{item.limit_count} in {item.window_seconds}s · resets in {item.seconds_until_reset ?? 'n/a'}s
                </p>
                <div className="mt-2 h-2 w-full rounded-full bg-[var(--surface-muted)]">
                  <div
                    className="h-full rounded-full bg-[var(--accent)]"
                    style={{ width: `${Math.max(3, Math.min(100, Math.round(item.utilization * 100)))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(usageQuery.data ?? []).slice(0, 20).map((row) => (
            <p key={row.id}>policy #{row.policy_id} used {row.usage_count} (window ends {new Date(row.window_end).toLocaleString()})</p>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Override audit</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(auditQuery.data ?? []).slice(0, 20).map((row) => (
            <p key={row.id}>policy #{row.policy_id}: {row.action} ({row.reason || 'no reason'})</p>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
