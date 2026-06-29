/**
 * CopilotHint — Inline one-sentence hint that appears below an edited leg.
 * Subtle — should not compete with main UI.
 */
interface Props {
  hint: string;
  isLoading: boolean;
}

export function CopilotHint({ hint, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="ml-4 border-l-2 border-border pl-3 py-1 mt-2">
        <div className="skeleton h-3 w-3/4" />
      </div>
    );
  }

  if (!hint) return null;

  return (
    <div className="ml-4 border-l-2 border-border pl-3 py-1 mt-2">
      <span className="text-accent text-xs mr-1">Copilot</span>
      <span className="text-secondary text-sm">{hint}</span>
    </div>
  );
}
