import { SignupForm } from '@/components/auth/signup-form';
import { getEnabledProviders } from '@/lib/oauth';

export default async function SignupPage() {
  const enabledProviders = await getEnabledProviders();
  const kycChecklist = ['GST document', 'PAN document', 'Primary bank account proof'];
  return (
    <div className="space-y-6">
      <SignupForm enabledProviders={enabledProviders} />
      <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-5">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">Vendor KYC progress</h2>
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          Onboarding moves through submitted → under_review → resubmission_required/approved/rejected.
        </p>
        <ul className="mt-3 space-y-1.5 text-xs text-[var(--text-secondary)]">
          {kycChecklist.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
