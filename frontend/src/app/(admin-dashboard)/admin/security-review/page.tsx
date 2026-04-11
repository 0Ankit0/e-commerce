'use client';

import Link from 'next/link';
import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  Eye,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  useObservabilitySummary,
  useSecurityIncident,
  useSecurityIncidents,
  useUpdateSecurityIncident,
} from '@/hooks/use-observability';
import { usePrivilegedPolicies } from '@/hooks/use-rbac';
import { buildIncidentLogHref, incidentSeverityTone, incidentStatusTone } from '@/lib/observability';

const STATUS_OPTIONS = ['all', 'open', 'acknowledged', 'resolved'];
const SEVERITY_OPTIONS = ['all', 'high', 'medium', 'low'];

export default function SecurityReviewPage() {
  const [statusFilter, setStatusFilter] = useState('open');
  const [severity, setSeverity] = useState('all');
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);
  const filters = useMemo(
    () => ({
      status: statusFilter === 'all' ? undefined : statusFilter,
      severity: severity === 'all' ? undefined : severity,
      search: deferredSearch || undefined,
      limit: 40,
    }),
    [deferredSearch, severity, statusFilter]
  );

  const summaryQuery = useObservabilitySummary();
  const incidentsQuery = useSecurityIncidents(filters);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const selectedIncidentQuery = useSecurityIncident(selectedIncidentId);
  const updateIncident = useUpdateSecurityIncident();
  const policiesQuery = usePrivilegedPolicies();
  const [reviewNotes, setReviewNotes] = useState('');
  const [enforcementFailureReason, setEnforcementFailureReason] = useState<string | null>(null);

  useEffect(() => {
    const firstIncidentId = incidentsQuery.data?.items[0]?.id ?? null;
    setSelectedIncidentId((current) => current ?? firstIncidentId);
  }, [incidentsQuery.data]);

  useEffect(() => {
    setReviewNotes(selectedIncidentQuery.data?.review_notes ?? '');
  }, [selectedIncidentQuery.data]);

  const selectedIncident = selectedIncidentQuery.data;
  const incidentReviewPolicy = policiesQuery.data?.find(
    (policy) => policy.action === 'admin.observability.incident_review'
  );

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-none bg-[var(--foreground)] text-[var(--background)] shadow-[0_24px_80px_rgba(0,0,0,0.24)]">
        <CardContent className="relative px-6 py-8">
          <div className="absolute inset-0 opacity-10" style={{ background: `radial-gradient(circle at top left, var(--accent), transparent 30%), radial-gradient(circle at bottom right, var(--warning-soft), transparent 28%)` }} />
          <div className="relative grid gap-6 lg:grid-cols-[1.3fr,0.7fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.26em] opacity-60">Security Review</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight">Suspicious activity queue</h1>
              <p className="mt-3 max-w-2xl text-sm opacity-70">
                Review high-risk auth patterns, sensitive admin changes, and operational spikes before they turn into incidents someone else discovers for us.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-1">
              <div className="rounded-2xl border border-[rgba(128,128,128,0.2)] bg-[rgba(128,128,128,0.08)] px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] opacity-60">Open</p>
                <p className="mt-2 text-2xl font-semibold">{summaryQuery.data?.open_incidents ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-[var(--warning-soft)] bg-[color-mix(in_srgb,var(--warning-soft)_30%,transparent)] px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] opacity-70">Acknowledged</p>
                <p className="mt-2 text-2xl font-semibold">{summaryQuery.data?.acknowledged_incidents ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-[var(--danger-soft)] bg-[color-mix(in_srgb,var(--danger-soft)_30%,transparent)] px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] opacity-70">Critical</p>
                <p className="mt-2 text-2xl font-semibold">{summaryQuery.data?.critical_incidents ?? 0}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[360px,minmax(0,1fr)]">
        <Card className="border-[var(--border-color)] bg-white/90 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <ShieldAlert className="h-5 w-5 text-red-600" />
              Queue
            </CardTitle>
            <CardDescription>Filter the active queue, then open an incident to inspect the log trail.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="search title, summary, ip"
            />

            <div className="grid grid-cols-2 gap-3">
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm"
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <select
                value={severity}
                onChange={(event) => setSeverity(event.target.value)}
                className="rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm"
              >
                {SEVERITY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-3">
              {(incidentsQuery.data?.items ?? []).map((incident) => {
                const selected = incident.id === selectedIncidentId;
                return (
                  <button
                    key={incident.id}
                    type="button"
                    onClick={() => setSelectedIncidentId(incident.id)}
                    className={`w-full rounded-2xl border px-4 py-4 text-left transition-all ${
                      selected
                        ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_12px_30px_rgba(0,0,0,0.08)]'
                        : 'border-[var(--border-color)] bg-white hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]'
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${incidentSeverityTone(incident.severity)}`}>
                        {incident.severity}
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${incidentStatusTone(incident.status)}`}>
                        {incident.status}
                      </span>
                    </div>
                    <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">{incident.title}</p>
                    <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{incident.summary}</p>
                    <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-muted)]">
                      <span>{incident.signal_type}</span>
                      <span>{incident.occurrence_count} hits</span>
                    </div>
                  </button>
                );
              })}

              {!incidentsQuery.data?.items.length ? (
                <div className="rounded-2xl border border-dashed border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-10 text-center">
                  <Sparkles className="mx-auto h-7 w-7 text-[var(--text-muted)]" />
                  <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">No incidents match right now.</p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">Change the filters or come back when the detector has something to review.</p>
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card className="border-[var(--border-color)] bg-white/95 backdrop-blur">
          <CardHeader className="border-b border-[var(--border-color)]">
            <CardTitle className="text-xl">Incident Detail</CardTitle>
            <CardDescription>
              Review notes, linked logs, and the latest metadata for the selected incident.
            </CardDescription>
            <p className="text-xs text-[var(--text-muted)]">
              Step-up enforcement:{' '}
              <span className="font-semibold text-[var(--text-primary)]">
                {incidentReviewPolicy?.require_step_up ? `enabled (${incidentReviewPolicy.otp_freshness_seconds}s)` : 'disabled'}
              </span>
            </p>
          </CardHeader>
          <CardContent className="space-y-5">
            {!selectedIncident ? (
              <div className="flex min-h-72 flex-col items-center justify-center gap-3 text-center">
                <Eye className="h-8 w-8 text-[var(--text-muted)]" />
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">Select an incident to inspect it.</p>
                  <p className="text-xs text-[var(--text-muted)]">The detail panel will stay pinned while you move through the queue.</p>
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${incidentSeverityTone(selectedIncident.severity)}`}>
                        {selectedIncident.severity}
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${incidentStatusTone(selectedIncident.status)}`}>
                        {selectedIncident.status}
                      </span>
                    </div>
                    <h2 className="mt-3 text-2xl font-semibold text-[var(--text-primary)]">{selectedIncident.title}</h2>
                    <p className="mt-2 text-sm text-[var(--text-muted)]">{selectedIncident.summary}</p>
                  </div>
                  <Link
                    href={buildIncidentLogHref(selectedIncident)}
                    className="inline-flex items-center rounded-full border border-[var(--border-color)] px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]"
                  >
                    Open linked logs
                    <ArrowUpRight className="ml-2 h-4 w-4" />
                  </Link>
                </div>

                <div className="grid gap-4 lg:grid-cols-3">
                  <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Signal</p>
                    <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{selectedIncident.signal_type}</p>
                  </div>
                  <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Occurrences</p>
                    <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{selectedIncident.occurrence_count}</p>
                  </div>
                  <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">IP Address</p>
                    <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{selectedIncident.ip_address || 'n/a'}</p>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-[1fr,1fr]">
                  <div className="rounded-3xl border border-[var(--border-color)] bg-[var(--surface-muted)] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Timeline</p>
                    <div className="mt-3 space-y-3 text-sm text-[var(--text-secondary)]">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="mt-0.5 h-4 w-4 text-red-600" />
                        <div>
                          <p className="font-medium text-[var(--text-primary)]">First seen</p>
                          <p>{new Date(selectedIncident.first_seen_at).toLocaleString()}</p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <ShieldCheck className="mt-0.5 h-4 w-4 text-[var(--accent)]" />
                        <div>
                          <p className="font-medium text-[var(--text-primary)]">Last seen</p>
                          <p>{new Date(selectedIncident.last_seen_at).toLocaleString()}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-3xl border border-[var(--border-color)] bg-[var(--foreground)] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--background)] opacity-60">Metadata</p>
                    <pre className="mt-3 overflow-x-auto text-xs leading-6 text-[var(--background)] opacity-80">
                      {JSON.stringify(selectedIncident.metadata ?? {}, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                    Review Notes
                  </label>
                  <textarea
                    value={reviewNotes}
                    onChange={(event) => setReviewNotes(event.target.value)}
                    rows={5}
                    className="w-full rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--text-primary)] shadow-sm"
                    placeholder="Capture what you found, what changed, and whether follow-up is needed."
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  {enforcementFailureReason ? (
                    <p className="w-full rounded-xl border border-[var(--warning-soft)] bg-[color-mix(in_srgb,var(--warning-soft)_30%,white)] px-3 py-2 text-xs text-[var(--text-primary)]">
                      Step-up validation required: {enforcementFailureReason}
                    </p>
                  ) : null}
                  <Button
                    variant="outline"
                    isLoading={updateIncident.isPending}
                    onClick={() =>
                      updateIncident.mutate({
                        incidentId: selectedIncident.id,
                        payload: { status: 'acknowledged', review_notes: reviewNotes },
                      }, {
                        onError: (error: any) => {
                          setEnforcementFailureReason(error?.response?.data?.detail?.reason ?? 'missing_or_expired_step_up');
                        },
                        onSuccess: () => setEnforcementFailureReason(null),
                      })
                    }
                  >
                    Acknowledge
                  </Button>
                  <Button
                    isLoading={updateIncident.isPending}
                    onClick={() =>
                      updateIncident.mutate({
                        incidentId: selectedIncident.id,
                        payload: { status: 'resolved', review_notes: reviewNotes },
                      }, {
                        onError: (error: any) => {
                          setEnforcementFailureReason(error?.response?.data?.detail?.reason ?? 'missing_or_expired_step_up');
                        },
                        onSuccess: () => setEnforcementFailureReason(null),
                      })
                    }
                  >
                    Resolve
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
