interface StorefrontStateProps {
  eyebrow: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function StorefrontState({
  eyebrow,
  title,
  description,
  actionLabel,
  onAction,
}: StorefrontStateProps) {
  return (
    <div className="rounded-[32px] border border-dashed border-[var(--border-color)] bg-white p-10 text-center shadow-[0_16px_45px_rgba(25,30,45,0.04)]">
      <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">{eyebrow}</p>
      <h2 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">{title}</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="mt-6 inline-flex rounded-full bg-[var(--foreground)] px-5 py-3 text-sm font-semibold text-[var(--background)]"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
