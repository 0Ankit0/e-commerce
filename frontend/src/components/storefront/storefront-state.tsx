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
    <div className="rounded-[32px] border border-dashed border-[rgba(25,30,45,0.14)] bg-white p-10 text-center shadow-[0_16px_45px_rgba(25,30,45,0.04)]">
      <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">{eyebrow}</p>
      <h2 className="mt-3 font-[family:var(--font-display)] text-4xl text-[#1d1b18]">{title}</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#6f6257]">{description}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="mt-6 inline-flex rounded-full bg-[#1d1b18] px-5 py-3 text-sm font-semibold text-white"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
