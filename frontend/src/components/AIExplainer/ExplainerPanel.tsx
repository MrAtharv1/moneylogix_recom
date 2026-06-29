/**
 * ExplainerPanel — AI explanation panel. Only shows when explanation string is non-empty.
 * Subtle blue-tinted card with "AI" badge.
 */
interface Props {
  explanation: string;
  isLoading: boolean;
}

export function ExplainerPanel({ explanation, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-lg p-4 mt-2" style={{ backgroundColor: '#0f1e3d', border: '1px solid #1e3a5f' }}>
        <div className="flex flex-col gap-2">
          <div className="skeleton h-3 w-full" />
          <div className="skeleton h-3 w-5/6" />
          <div className="skeleton h-3 w-2/3" />
        </div>
      </div>
    );
  }

  if (!explanation) return null;

  return (
    <div className="rounded-lg p-4 mt-2" style={{ backgroundColor: '#0f1e3d', border: '1px solid #1e3a5f' }}>
      <span
        className="inline-block text-xs px-1.5 py-0.5 rounded mb-2"
        style={{ backgroundColor: '#1e3a5f', color: '#3b82f6' }}
      >
        AI
      </span>
      <p className="text-primary leading-relaxed text-sm">{explanation}</p>
      <p className="text-secondary text-xs mt-2">This is a mechanical explanation, not investment advice.</p>
    </div>
  );
}
