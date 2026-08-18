import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  resolveSmartSearchVoiceLanguage,
  smartSearchVoiceErrorMessage,
  useSmartSearchVoice,
} from "@/hooks/useSmartSearchVoice";
import { Mic, MicOff, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export type SmartSearchFieldSuggestion = {
  id: string | number;
  label: string;
  secondary?: string | null;
};

type Props = {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  isRTL: boolean;
  suggestions?: SmartSearchFieldSuggestion[];
  className?: string;
  inputClassName?: string;
  compact?: boolean;
  showClear?: boolean;
  ariaLabel?: string;
};

// SMART_SEARCH_PHASE5B2_FIELD_V1
export function SmartSearchField({
  value,
  onChange,
  placeholder,
  isRTL,
  suggestions = [],
  className,
  inputClassName,
  compact = false,
  showClear = true,
  ariaLabel,
}: Props) {
  const [focused, setFocused] = useState(false);
  const voice = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));
  const visibleSuggestions = value.trim().length >= 2 ? suggestions.slice(0, 6) : [];

  useEffect(() => {
    if (voice.transcript) onChange(voice.transcript);
  }, [voice.transcript]);

  useEffect(() => {
    if (voice.error) toast.error(smartSearchVoiceErrorMessage(voice.error, isRTL));
  }, [voice.error, isRTL]);

  const iconSize = compact ? 13 : 16;
  const inputHeight = compact ? "h-8 text-xs" : "h-10 text-sm";

  return (
    <div className={cn("relative", className)}>
      <Search
        size={iconSize}
        className="pointer-events-none absolute start-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => window.setTimeout(() => setFocused(false), 120)}
        placeholder={placeholder}
        aria-label={ariaLabel || placeholder}
        autoComplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={focused && visibleSuggestions.length > 0}
        className={cn(inputHeight, "ps-8 pe-16", inputClassName)}
      />
      <div className="absolute end-1.5 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
        {showClear && value ? (
          <button
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => onChange("")}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={isRTL ? "مسح البحث" : "Clear search"}
          >
            <X size={compact ? 12 : 14} />
          </button>
        ) : null}
        {voice.isSupported ? (
          <button
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() =>
              voice.isListening ? voice.stopListening() : voice.startListening()
            }
            className={cn(
              "relative rounded p-1 transition",
              voice.isListening
                ? "bg-rose-100 text-rose-600 dark:bg-rose-950/40"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
            title={isRTL ? "بحث صوتي" : "Voice search"}
            aria-label={isRTL ? "بحث صوتي" : "Voice search"}
          >
            {voice.isListening ? (
              <>
                <span className="absolute inset-0 animate-ping rounded bg-rose-400/20" />
                <MicOff size={compact ? 13 : 15} className="relative" />
              </>
            ) : (
              <Mic size={compact ? 13 : 15} />
            )}
          </button>
        ) : null}
      </div>

      {focused && visibleSuggestions.length > 0 ? (
        <div
          role="listbox"
          className="absolute start-0 end-0 top-full z-50 mt-1 overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-xl"
        >
          {visibleSuggestions.map((suggestion) => (
            <button
              key={suggestion.id}
              type="button"
              role="option"
              onMouseDown={(event) => {
                event.preventDefault();
                onChange(suggestion.label);
                setFocused(false);
              }}
              className="block w-full px-3 py-2 text-start text-sm hover:bg-muted"
            >
              <span className="block truncate font-medium">{suggestion.label}</span>
              {suggestion.secondary ? (
                <span className="block truncate text-[11px] text-muted-foreground">
                  {suggestion.secondary}
                </span>
              ) : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
