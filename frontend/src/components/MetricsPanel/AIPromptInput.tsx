import React, { useState, useRef, useEffect } from 'react';
import { getPromptToTrade } from '../../api/client';

interface AIPromptInputProps {
  onStrategyGenerated: (data: { legs: any[]; symbol: string; strategyName?: string }) => void;
}

// Sentiment patterns
const SENTIMENT_PATTERNS = [
  { test: (t: string) => /\b(crash|collapse|panic|fear|worried|scared|stress|fall)\b/i.test(t), message: "📉 Fear detected — Iron Condors and defined-risk spreads perform well in uncertain markets.", type: 'fear' },
  { test: (t: string) => /\b(greed|moon|guaranteed|sure thing|can't lose|risk free|rocket)\b/i.test(t), message: "⚠️ High conviction detected — consider defined-risk strategies to protect against being wrong.", type: 'greed' },
  { test: (t: string) => /\b(sideways|range.?bound|flat|stuck|consolidat)\b/i.test(t), message: "📊 Range-bound view — Iron Condor or Short Straddle may suit this outlook.", type: 'neutral' },
  { test: (t: string) => /\b(breakout|big move|volatile|event|results|budget|rbi)\b/i.test(t), message: "🎯 High volatility expected — Long Straddle or Strangle benefits from large moves.", type: 'volatile' },
];

function detectSentiment(text: string) {
  for (const pattern of SENTIMENT_PATTERNS) {
    if (pattern.test(text)) return pattern;
  }
  return null;
}

export const AIPromptInput: React.FC<AIPromptInputProps> = ({ onStrategyGenerated }) => {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);
  const [sentiment, setSentiment] = useState<{message: string; type: string} | null>(null);
  const recognitionRef = useRef<any>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const isSpeechSupported = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const t = text.toLowerCase();
      setSentiment(detectSentiment(t));
    }, 500);
    return () => clearTimeout(debounceRef.current);
  }, [text]);

  const startSpeechRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = false;
    recognitionRef.current.interimResults = false;
    recognitionRef.current.lang = 'en-US';

    recognitionRef.current.onstart = () => setIsListening(true);
    recognitionRef.current.onend = () => setIsListening(false);
    
    recognitionRef.current.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setText(transcript);
      handleSubmit(transcript);
    };

    recognitionRef.current.start();
  };

  const handleSubmit = async (queryText: string) => {
    const activeText = queryText || text;
    if (!activeText.trim() || isLoading) return;

    setIsLoading(true);
    setMessage({ type: 'info', text: 'Analyzing market intent...' });
    setShowTooltip(false);

    try {
      const data = await getPromptToTrade(activeText);

      if (data.success) {
        setMessage({ type: 'success', text: data.message });
        onStrategyGenerated({ 
            legs: data.legs, 
            symbol: data.symbol,
            strategyName: data.requested_strategy
        });
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to generate strategy.' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Connection error. Reverting to local state.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex flex-col gap-3 rounded-2xl border border-accent/30 bg-gradient-to-br from-surface/40 to-accent/5 p-6 shadow-[0_0_30px_-5px_rgba(79,140,255,0.15)] backdrop-blur-md">
      
      {/* Ambient Glow Wrapper */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl">
        <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-accent/20 blur-[50px]" />
      </div>

      <div className="relative z-10 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-accent/90">
        <span className="flex h-4 items-center justify-center rounded bg-accent/10 px-1 text-[9px] font-bold text-accent ring-1 ring-inset ring-accent/20">AI</span>
        Strategy Copilot
      </div>
      
      <div className="relative z-20 flex items-center">
        {/* Tooltip positioned BELOW the input */}
        <div 
          className={`absolute top-[54px] left-2 z-50 rounded-lg border border-border/60 bg-surface/95 px-3 py-1.5 text-[11px] text-secondary shadow-lg backdrop-blur-md transition-all duration-200 pointer-events-none ${
            showTooltip ? 'opacity-100 translate-y-0 visible' : 'opacity-0 -translate-y-1 invisible'
          }`}
        >
          {/* Tooltip arrow pointing UP */}
          <div className="absolute -top-1.5 left-6 h-3 w-3 rotate-45 border-t border-l border-border/60 bg-surface/95" />
          <span>💡 <strong className="font-semibold text-white">Tip for best results:</strong> Mention the asset, direction, timeframe, and your budget.</span>
        </div>

        <input
          type="text"
          className="h-12 w-full rounded-xl border border-border/50 bg-surface/50 pl-4 pr-24 text-[13px] text-primary shadow-inner transition-all placeholder:text-secondary/50 focus:border-accent/60 focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/60 disabled:opacity-50"
          placeholder="e.g., I think NIFTY will go up next month, max risk ₹10k..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit('')}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          onFocus={() => setShowTooltip(false)}
          disabled={isLoading}
        />
        
        <div className="absolute right-1.5 flex items-center gap-1.5">
          {isSpeechSupported && (
            <button
              onClick={startSpeechRecognition}
              disabled={isLoading}
              className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                isListening ? 'bg-loss/10 text-loss' : 'bg-transparent text-secondary hover:bg-surface/80 hover:text-primary'
              } disabled:opacity-50 focus:outline-none`}
              title="Speak strategy"
            >
              {isListening ? (
                <span className="relative flex h-3 w-3">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-loss opacity-75"></span>
                  <span className="relative inline-flex h-3 w-3 rounded-full bg-loss"></span>
                </span>
              ) : (
                '🎤'
              )}
            </button>
          )}
          <button
            onClick={() => handleSubmit('')}
            disabled={isLoading || !text.trim()}
            className="flex h-9 items-center justify-center rounded-lg bg-accent px-4 text-[11px] font-bold tracking-wide text-white shadow-sm transition-all hover:bg-accent/90 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-accent/50 disabled:bg-border/50 disabled:text-secondary/50 disabled:shadow-none"
          >
            {isLoading ? 'Wait...' : 'Build'}
          </button>
        </div>
      </div>

      {sentiment && (
        <div className="relative z-10 mt-2 rounded-xl border border-accent/20 bg-accent/10 px-3 py-2 text-xs text-accent/90 animate-in fade-in">
          {sentiment.message}
        </div>
      )}

      {message && (
        <div className={`relative z-10 mt-1 rounded-xl border px-3 py-2 text-xs ${
          message.type === 'success' ? 'border-profit/20 bg-profit/10 text-profit' :
          message.type === 'error' ? 'border-loss/20 bg-loss/10 text-loss' : 'border-accent/20 bg-accent/10 text-accent'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
};