import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface QuestionInputProps {
  onAsk: (question: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function QuestionInput({
  onAsk,
  isLoading = false,
  disabled = false,
  placeholder = 'Ask a question about this document...',
}: QuestionInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed && !isLoading && !disabled) {
      onAsk(trimmed);
      setInput('');
    }
  };

  const isInputDisabled = isLoading || disabled;

  return (
    <div className="p-8 border-t border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface">
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-3 border border-penny-border dark:border-penny-dark-border bg-penny-bg dark:bg-penny-dark-bg p-3 focus-within:border-penny-text dark:focus-within:border-penny-dark-text transition-colors"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isInputDisabled}
          placeholder={placeholder}
          className="flex-1 bg-transparent border-none outline-none text-sm placeholder-[#666666] dark:placeholder-[#999999] disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={isInputDisabled || !input.trim()}
          className="p-1 hover:text-penny-accent dark:hover:text-penny-dark-accent transition-colors disabled:opacity-40 disabled:hover:text-inherit cursor-pointer disabled:cursor-not-allowed"
          aria-label="Send question"
        >
          {isLoading ? (
            <Loader2 size={16} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </form>
    </div>
  );
}