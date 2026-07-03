import React, { useState, useRef } from 'react';

interface AIPromptInputProps {
  onStrategyGenerated: (data: { legs: any[]; symbol: string; strategyName?: string }) => void;
}

export const AIPromptInput: React.FC<AIPromptInputProps> = ({ onStrategyGenerated }) => {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const recognitionRef = useRef<any>(null);

  const startSpeechRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessage({ type: 'error', text: 'Voice speech recognition not supported in this browser. Please type your query.' });
      return;
    }

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

    try {
      const response = await fetch('http://localhost:8000/api/prompt-to-trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: activeText }),
      });
      
      const data = await response.json();

      if (data.success) {
        setMessage({ type: 'success', text: data.message });
        onStrategyGenerated({ 
            legs: data.legs, 
            symbol: data.symbol,
            strategyName: data.requested_strategy // Catching the exact strategy name from Python
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
    <div className="w-full bg-[#111827] p-4 rounded-lg border border-gray-800 mb-6">
      <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
        <span>💡 <strong className="text-white">Tip for best results:</strong> Mention the asset, direction, timeframe, and your budget.</span>
      </div>
      
      <div className="relative flex items-center">
        <input
          type="text"
          className="w-full bg-black text-white placeholder-gray-600 text-sm rounded border border-gray-800 p-3 pr-24 focus:outline-none focus:border-blue-500"
          placeholder="e.g., I think Reliance will go up next month, and my budget is ₹20,000..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit('')}
          disabled={isLoading}
        />
        
        <div className="absolute right-2 flex items-center gap-2">
          <button
            onClick={startSpeechRecognition}
            disabled={isLoading}
            className={`p-2 rounded-full transition-colors ${isListening ? 'bg-red-600 text-white animate-pulse' : 'text-gray-400 hover:text-white bg-gray-900'} disabled:opacity-50`}
            title="Speak strategy"
          >
            🎤
          </button>
          <button
            onClick={() => handleSubmit('')}
            disabled={isLoading || !text.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-xs font-medium px-3 py-2 rounded transition-colors"
          >
            {isLoading ? 'Thinking...' : 'Generate'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`mt-2 text-xs p-2 rounded ${
          message.type === 'success' ? 'bg-green-950 text-green-400' : 
          message.type === 'error' ? 'bg-red-950 text-red-400' : 'bg-blue-950 text-blue-400'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
};