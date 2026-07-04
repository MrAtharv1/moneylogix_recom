/**
 * ExplainerPanel — AI explanation panel. 
 * Styled as a premium, native copilot integration.
 */
interface Props {
  explanation: string;
  isLoading: boolean;
}

export function ExplainerPanel({ explanation, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 rounded-xl border border-accent/20 bg-surface/20 p-4 shadow-[0_0_15px_-3px_rgba(79,140,255,0.05)]">
        <div className="h-3 w-full animate-pulse rounded bg-border/50" />
        <div className="h-3 w-5/6 animate-pulse rounded bg-border/50" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-border/50" />
      </div>
    );
  }

  if (!explanation) return null;

  return (
    <div className="relative rounded-xl border border-accent/20 bg-surface/20 p-4 shadow-[0_0_15px_-3px_rgba(79,140,255,0.05)]">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-5 items-center justify-center rounded bg-accent/10 px-1.5 text-[10px] font-bold text-accent ring-1 ring-inset ring-accent/20">
          AI
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-secondary/60">
          Analysis
        </span>
      </div>
      <p className="text-[13px] leading-relaxed text-primary/90">{explanation}</p>
      <p className="mt-3 text-[10px] text-secondary/50">
        This is a mechanical evaluation, not investment advice.
      </p>
    </div>
  );
}