import { useCallback, useEffect, useRef, useState } from "react";

export type SmartSearchVoiceError =
  | "not-allowed"
  | "service-not-allowed"
  | "audio-capture"
  | "network"
  | "no-speech"
  | "aborted"
  | "start-failed"
  | string;

export function resolveSmartSearchVoiceLanguage(isRTL: boolean): "ar-SA" | "en-US" {
  return isRTL ? "ar-SA" : "en-US";
}

export function smartSearchVoiceErrorMessage(error: SmartSearchVoiceError | null, isRTL: boolean): string {
  if (!error) return "";
  const ar: Record<string, string> = {
    "not-allowed": "تم رفض إذن الميكروفون. اسمح للموقع باستخدام الميكروفون ثم حاول مرة أخرى.",
    "service-not-allowed": "المتصفح يمنع خدمة التعرف على الصوت لهذا الموقع.",
    "audio-capture": "لم يتم العثور على ميكروفون متاح.",
    network: "تعذر الاتصال بخدمة التعرف على الصوت. تحقق من الاتصال وحاول مرة أخرى.",
    "no-speech": "لم يتم التقاط كلام واضح. حاول مرة أخرى.",
    "start-failed": "تعذر تشغيل الميكروفون الآن. حاول مرة أخرى.",
  };
  const en: Record<string, string> = {
    "not-allowed": "Microphone permission was denied. Allow microphone access and try again.",
    "service-not-allowed": "Speech recognition is blocked for this site by the browser.",
    "audio-capture": "No available microphone was found.",
    network: "Speech recognition could not connect. Check the connection and try again.",
    "no-speech": "No clear speech was detected. Try again.",
    "start-failed": "The microphone could not start. Try again.",
  };
  const messages = isRTL ? ar : en;
  return messages[error] || (isRTL ? "تعذر استخدام البحث الصوتي." : "Voice search could not be used.");
}

export function useSmartSearchVoice(language: "ar-SA" | "en-US") {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState<SmartSearchVoiceError | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setIsSupported(false);
      recognitionRef.current = null;
      return;
    }

    setIsSupported(true);
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = language;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setError(null);
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let finalTranscript = "";
      let interimTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const value = String(event.results[i]?.[0]?.transcript ?? "");
        if (event.results[i]?.isFinal) finalTranscript += value;
        else interimTranscript += value;
      }
      const nextTranscript = (finalTranscript || interimTranscript).trim();
      if (nextTranscript) setTranscript(nextTranscript);
    };

    recognition.onerror = (event: any) => {
      const nextError = String(event?.error || "start-failed") as SmartSearchVoiceError;
      if (nextError !== "aborted") setError(nextError);
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;

    return () => {
      try { recognition.abort(); } catch {}
      recognition.onstart = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      if (recognitionRef.current === recognition) recognitionRef.current = null;
    };
  }, [language]);

  const startListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition || isListening) return;
    setTranscript("");
    setError(null);
    try {
      recognition.start();
    } catch {
      setIsListening(false);
      setError("start-failed");
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition || !isListening) return;
    try { recognition.stop(); } catch {}
    setIsListening(false);
  }, [isListening]);

  return {
    isListening,
    transcript,
    isSupported,
    error,
    startListening,
    stopListening,
  };
}
