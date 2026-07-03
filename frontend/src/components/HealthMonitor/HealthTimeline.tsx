import { useState } from 'react';

interface Props {
  history: any[];
}

// HELPER: Forces IST Date & Time format (e.g., 02/07/2026, 07:57:32 pm)
const formatISTDateTime = (dateString: string) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });
};

export function HealthTimeline({ history }: Props) {
  const [showHistory, setShowHistory] = useState(true);

  if (!history || history.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-border flex flex-col gap-3">
      <button 
        onClick={() => setShowHistory(!showHistory)}
        className="text-secondary text-sm text-left hover:text-primary transition-colors w-fit"
      >
        {showHistory ? 'Hide history' : 'Show history'}
      </button>
      
      {showHistory && (
        <div className="flex flex-col max-h-60 overflow-y-auto pr-2">
          {history.map((item, i) => (
            <div key={i} className="flex flex-col gap-1 border-b border-border py-3 last:border-0">
              {/* THIS IS THE FIX: Using the IST formatter instead of raw date */}
              <div className="text-secondary text-xs">
                {formatISTDateTime(item.checked_at || item.timestamp)}
              </div>
              
              <div className="text-primary text-sm">
                {item.diff && item.diff.has_changes 
                  ? 'Changes detected in strategy health.' 
                  : 'No significant changes'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}