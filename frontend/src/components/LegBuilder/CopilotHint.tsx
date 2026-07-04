/**
 * CopilotHint — Inline one-sentence hint that appears below an edited leg.
 * Styled as a subtle, native AI callout.
 */
interface Props {
  hint: string;
  isLoading: boolean;
}

export function CopilotHint({ hint, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="mt-1 flex items-center gap-2 pl-2">
        <span className="flex h-4 items-center justify-center rounded bg-accent/5 px-1 text-[9px] font-bold text-accent/50 ring-1 ring-inset ring-accent/10">AI</span>
        <div className="h-2.5 w-48 animate-pulse rounded bg-border/50" />
      </div>
    );
  }

  if (!hint) return null;

  return (
    <div className="mt-1 flex animate-in fade-in slide-in-from-top-1 items-start gap-2 pl-2 duration-300">
      <span className="mt-0.5 flex h-4 shrink-0 items-center justify-center rounded bg-accent/10 px-1 text-[9px] font-bold text-accent ring-1 ring-inset ring-accent/20">
        AI
      </span>
      <span className="text-[12px] leading-relaxed text-secondary/90">{hint}</span>
    </div>
  );
}