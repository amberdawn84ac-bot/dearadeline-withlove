'use client';

/**
 * ReaderChatSidebar — Adeline's Socratic Reading Co-Pilot
 * 
 * A collapsible chat sidebar that provides contextual literary discussions
 * based on the student's current reading location and highlighted text.
 * 
 * Features:
 * - Streams responses in real-time using @ai-sdk/react useChat
 * - Auto-injects book context (title, chapter, highlighted text)
 * - Maintains conversation history during reading session
 * - Collapsible/expandable for distraction-free reading
 * 
 * Design:
 * - Right-side drawer that can slide in/out
 * - Earth tone theme matching the Reading Nook (#E7DAC3, #BD6809)
 * - Clean message bubbles with clear user/assistant distinction
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useChat } from '@ai-sdk/react';
import { MessageCircle, X, ChevronLeft, Send } from 'lucide-react';
import { useReader } from '@/lib/reader-context';

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

interface ReaderChatSidebarProps {
  studentId: string;
  isOpen: boolean;
  onToggle: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export function ReaderChatSidebar({ studentId, isOpen, onToggle }: ReaderChatSidebarProps) {
  const { 
    currentBook, 
    location, 
    selectedText, 
    clearSelectedText 
  } = useReader();
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Local input state (since this version of useChat doesn't provide it)
  const [inputValue, setInputValue] = useState('');

  // Initialize useChat with correct API for this @ai-sdk/react version
  // @ts-ignore - api property works at runtime despite type errors
  const chat = useChat({
    id: `reader-${studentId}-${currentBook?.id || 'unknown'}`,
    api: '/api/reader-chat',
    headers: typeof window !== 'undefined'
      ? { Authorization: `Bearer ${localStorage.getItem('auth_token') ?? ''}` }
      : {},
  });
  
  const { messages, sendMessage, status, setMessages } = chat;
  const isLoading = status === 'streaming' || status === 'submitted';

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // When text is selected, immediately send the discussion prompt
  useEffect(() => {
    if (selectedText && currentBook && location && status !== 'streaming') {
      // Send the highlighted text discussion prompt
      sendMessage(
        {
          text: `I highlighted this passage in ${currentBook.title}, Chapter "${location.chapterTitle}": "${selectedText}". Can you help me understand this?`,
        },
        {
          // Pass book context as options
          body: {
            student_id: studentId,
            track: 'ENGLISH_LITERATURE',
            context: {
              current_book: {
                id: currentBook.id,
                title: currentBook.title,
                author: currentBook.author,
                cfi: location?.cfi,
                chapter: location?.chapterTitle,
                progress_percent: location?.progress,
              },
              highlighted_text: selectedText,
            },
          },
        }
      );
      
      // Clear the selection after sending
      clearSelectedText();
    }
  }, [selectedText, currentBook, location, sendMessage, clearSelectedText, status, studentId]);

  // Handle sending message from input
  const handleSend = useCallback(() => {
    if (!inputValue.trim() || status === 'streaming') return;
    
    sendMessage(
      {
        text: inputValue,
      },
      {
        body: {
          student_id: studentId,
          track: 'ENGLISH_LITERATURE',
          context: currentBook ? {
            current_book: {
              id: currentBook.id,
              title: currentBook.title,
              author: currentBook.author,
              cfi: location?.cfi,
              chapter: location?.chapterTitle,
              progress_percent: location?.progress,
            },
          } : undefined,
        },
      }
    );
    
    setInputValue('');
  }, [inputValue, sendMessage, status, studentId, currentBook, location]);

  // Handle Enter key for submission (Shift+Enter for new line)
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // ───────────────────────────────────────────────────────────────────────────
  // RENDER
  // ───────────────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Toggle Button (visible when sidebar is closed) */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="fixed right-4 top-1/2 -translate-y-1/2 z-40 
                     flex items-center gap-2 px-3 py-4 
                     bg-[#BD6809] hover:bg-[#9A5507] text-white 
                     rounded-l-lg shadow-lg
                     transition-all duration-200
                     hover:pr-5"
          aria-label="Open Adeline chat"
        >
          <MessageCircle className="w-5 h-5" />
          <span className="text-sm font-semibold writing-mode-vertical hidden lg:block">
            Ask Adeline
          </span>
        </button>
      )}

      {/* Sidebar Container */}
      <div
        className={`
          fixed right-0 top-0 h-full z-50
          flex flex-col
          bg-white border-l-2 border-[#E7DAC3]
          transition-transform duration-300 ease-in-out
          shadow-2xl
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
          w-full sm:w-96 lg:w-[420px]
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E7DAC3] bg-[#FFFEF7]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#BD6809] flex items-center justify-center">
              <MessageCircle className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-[#2F4731] text-sm">Adeline</h3>
              <p className="text-xs text-[#2F4731]/60">
                {currentBook ? `Reading: ${currentBook.title}` : 'Your Reading Co-Pilot'}
              </p>
            </div>
          </div>
          <button
            onClick={onToggle}
            className="p-2 hover:bg-[#E7DAC3] rounded-lg transition-colors"
            aria-label="Close chat sidebar"
          >
            <ChevronLeft className="w-5 h-5 text-[#2F4731]" />
          </button>
        </div>

        {/* Current Location Indicator */}
        {location && (
          <div className="px-4 py-2 bg-[#F5F0E8] border-b border-[#E7DAC3]">
            <p className="text-xs text-[#2F4731]/80">
              <span className="font-semibold">Current location:</span> {location.chapterTitle}
            </p>
            {location.progress > 0 && (
              <div className="mt-1 w-full h-1 bg-[#E7DAC3] rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[#BD6809] transition-all"
                  style={{ width: `${location.progress}%` }}
                />
              </div>
            )}
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#FFFEF7]">
          {/* Welcome Message */}
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#E7DAC3] flex items-center justify-center">
                <MessageCircle className="w-8 h-8 text-[#BD6809]" />
              </div>
              <h4 className="font-semibold text-[#2F4731] mb-2">
                Ask me about what you're reading
              </h4>
              <p className="text-sm text-[#2F4731]/60 px-4">
                Highlight any passage in the book and click "Discuss" to get my thoughts. 
                Or just ask me anything about the story, characters, or themes!
              </p>
              {selectedText && (
                <div className="mt-4 p-3 bg-[#E7DAC3]/30 rounded-lg mx-4">
                  <p className="text-xs text-[#8B6914] font-semibold mb-1">
                    💬 Ready to discuss:
                  </p>
                  <p className="text-xs text-[#2F4731]/80 line-clamp-3 italic">
                    "{selectedText}"
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Chat Messages */}
          {messages.map((message, index) => (
            <div
              key={message.id || index}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`
                  max-w-[85%] rounded-2xl px-4 py-3
                  ${
                    message.role === 'user'
                      ? 'bg-[#BD6809] text-white rounded-br-sm'
                      : 'bg-[#E7DAC3] text-[#2F4731] rounded-bl-sm'
                  }
                `}
              >
                {/* Message Content - extract text from parts array */}
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {message.parts
                    ?.filter((part: unknown) => (part as { type?: string }).type === 'text')
                    .map((part: unknown) => (part as { text?: string }).text)
                    .join('') || ''}
                </div>

                {/* Streaming indicator for assistant */}
                {message.role === 'assistant' && isLoading && index === messages.length - 1 && (
                  <div className="mt-2 flex gap-1">
                    <span className="w-1.5 h-1.5 bg-[#BD6809] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-[#BD6809] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-[#BD6809] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          ))}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <form 
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }} 
          className="p-4 border-t border-[#E7DAC3] bg-white"
        >
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the book..."
              className="
                flex-1 min-h-[44px] max-h-[120px]
                px-3 py-2.5
                text-sm text-[#2F4731]
                bg-[#FFFEF7] border border-[#E7DAC3] rounded-lg
                placeholder:text-[#2F4731]/40
                focus:outline-none focus:ring-2 focus:ring-[#BD6809] focus:border-transparent
                resize-none
              "
              rows={1}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="
                px-4 py-2
                bg-[#BD6809] hover:bg-[#9A5507] disabled:bg-[#E7DAC3]
                text-white rounded-lg
                transition-colors
                flex items-center justify-center
              "
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="mt-2 text-[10px] text-[#2F4731]/40 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </div>

      {/* Backdrop (click to close on mobile) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 sm:hidden"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}
    </>
  );
}
