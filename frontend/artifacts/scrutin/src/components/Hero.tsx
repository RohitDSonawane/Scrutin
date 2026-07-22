import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { ArrowUp, ArrowLeft, Mic, Paperclip, X } from "lucide-react";
const backgroundVideo = "https://res.cloudinary.com/dcryxjtb3/video/upload/v1784225334/Video_from_image_prompt_1080p_202607162337_cmez1z.mp4";
import { useRef, useState, useEffect } from "react";

const THINKING_STATUSES = [
  "Analyzing claim structure...",
  "Querying multi-agent network...",
  "Extracting context metadata...",
  "Cross-referencing database nodes...",
  "Synthesizing credibility score..."
];

export function Hero({ onVerify, isVerifying = false, onCancel }: { onVerify?: (text: string) => void; isVerifying?: boolean; onCancel?: () => void }) {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 1000], [0, 300]); // Moves at ~0.3x scroll speed
  const inputRef = useRef<HTMLDivElement>(null);
  const [statusIndex, setStatusIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [loopNum, setLoopNum] = useState(0);
  const [typingSpeed, setTypingSpeed] = useState(75);
  const [isInputEmpty, setIsInputEmpty] = useState(true);
  const [recentSearches, setRecentSearches] = useState<{query: string, verdict: string}[]>([]);

  useEffect(() => {
    import('@/lib/api-config').then(({ apiUrl }) => {
      // apiUrl is usually "http://localhost:8000" or "/api"
      const url = apiUrl.endsWith('/api') ? apiUrl.replace(/\/api$/, '/api/recent') : `${apiUrl}/api/recent`;
      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            setRecentSearches(data);
          }
        })
        .catch(err => console.error("Failed to fetch recent searches", err));
    });
  }, []);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedUrl, setAttachedUrl] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const micButtonRef = useRef<HTMLButtonElement>(null);
  const [micTooltipPos, setMicTooltipPos] = useState<{ x: number; y: number } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile(file);
      if (attachedUrl) {
        URL.revokeObjectURL(attachedUrl);
      }
      setAttachedUrl(URL.createObjectURL(file));
    }
  };

  const removeAttachedFile = () => {
    setAttachedFile(null);
    if (attachedUrl) {
      URL.revokeObjectURL(attachedUrl);
      setAttachedUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  useEffect(() => {
    return () => {
      if (attachedUrl) {
        URL.revokeObjectURL(attachedUrl);
      }
    };
  }, [attachedUrl]);

  const [micError, setMicError] = useState<string | null>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const createRecognition = () => {
        const r = new SpeechRecognition();
        r.continuous = false;
        r.interimResults = true;
        r.lang = 'en-US';

        r.onresult = (event: any) => {
          const transcript = Array.from(event.results)
            .map((result: any) => result[0].transcript)
            .join("");
          setMicError(null);
          if (inputRef.current) {
            inputRef.current.innerText = transcript;
            setIsInputEmpty(transcript.trim() === "");
          }
        };

        r.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsListening(false);
          if (event.error === 'network') {
            setMicError("Mic requires internet access to Google's speech servers. Try typing instead.");
          } else if (event.error === 'not-allowed') {
            setMicError("Microphone access denied. Please allow mic access in your browser settings.");
          } else {
            setMicError(`Speech error: ${event.error}. Please try again.`);
          }
          // Auto-clear error after 4 seconds
          setTimeout(() => setMicError(null), 4000);
        };
        
        r.onend = () => {
          setIsListening(false);
        };
        return r;
      };
      recognitionRef.current = createRecognition();
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);


  const handleMicClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      // Capture button position for fixed tooltip
      if (micButtonRef.current) {
        const rect = micButtonRef.current.getBoundingClientRect();
        setMicTooltipPos({ x: rect.left + rect.width / 2, y: rect.top - 12 });
      }
      setIsListening(true);
      recognitionRef.current?.start();
    }
  };

  const phrases = [
    "Verify if: 'Bananas are slightly radioactive'...",
    "Verify if: 'AI models use more water than data centers'...",
    "Verify if: 'NASA found liquid water on Mars recently'...",
    "Verify if: 'Drinking warm water burns fat instantly'..."
  ];

  useEffect(() => {
    if (isVerifying) return;
    const timer = setTimeout(() => {
      handleType();
    }, typingSpeed);
    return () => clearTimeout(timer);
  }, [displayText, isDeleting, typingSpeed, loopNum, isVerifying]);

  const handleType = () => {
    const idx = loopNum % phrases.length;
    const fullText = phrases[idx];
    
    if (!isDeleting) {
      setDisplayText(fullText.substring(0, displayText.length + 1));
      setTypingSpeed(65);
      
      if (displayText === fullText) {
        setIsDeleting(true);
        setTypingSpeed(2200); // Hold phrase at the end
      }
    } else {
      setDisplayText(fullText.substring(0, displayText.length - 1));
      setTypingSpeed(25); // Fast delete speed
      
      if (displayText === "") {
        setIsDeleting(false);
        setLoopNum((prev) => prev + 1);
        setTypingSpeed(350); // Pause before next phrase
      }
    }
  };

  useEffect(() => {
    if (!isVerifying) return;
    const interval = setInterval(() => {
      setStatusIndex((prev) => (prev + 1) % THINKING_STATUSES.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [isVerifying]);

  const handleSubmit = () => {
    if (onVerify && inputRef.current) {
      const text = inputRef.current.innerText.trim();
      onVerify(text || "Verify this claim");
    }
  };

  return (
    <>
      {/* Fixed-position mic error tooltip — escapes all overflow:hidden parents */}
      <AnimatePresence>
        {micError && micTooltipPos && (
          <motion.div
            key="mic-tooltip"
            initial={{ opacity: 0, y: 6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{
              position: 'fixed',
              left: micTooltipPos.x,
              top: micTooltipPos.y,
              transform: 'translate(-50%, -100%)',
              background: 'rgba(15, 8, 3, 0.92)',
              backdropFilter: 'blur(16px)',
              color: '#fff',
              fontSize: '12.5px',
              fontFamily: 'var(--font-aeonik)',
              padding: '10px 16px',
              borderRadius: '12px',
              boxShadow: '0 12px 32px rgba(0,0,0,0.35)',
              border: '1px solid rgba(255,255,255,0.1)',
              zIndex: 99999,
              pointerEvents: 'none',
              width: '240px',
              textAlign: 'center',
              lineHeight: 1.45,
            }}
          >
            <div style={{
              position: 'absolute', bottom: '-6px', left: '50%',
              transform: 'translateX(-50%)',
              width: 0, height: 0,
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '6px solid rgba(15, 8, 3, 0.92)'
            }} />
            {micError}
          </motion.div>
        )}
      </AnimatePresence>

    <div className={`relative w-full flex flex-col items-center justify-start overflow-hidden transition-all duration-700 ${isVerifying ? 'min-h-0 pt-6 px-6' : 'min-h-[100dvh] pt-[100px]'}`}>
      <div className="relative z-10 w-full max-w-7xl px-4 flex flex-col items-center">
        {/* Organic merged warm-white highlight cloud behind text to blend with background video */}
        {!isVerifying && (
          <div 
            className="absolute z-0 pointer-events-none select-none"
            style={{
              top: '-20px',
              width: '840px',
              height: '320px',
              background: 'radial-gradient(circle, rgba(252, 250, 247, 0.98) 0%, rgba(252, 250, 247, 0.92) 40%, rgba(252, 250, 247, 0.7) 65%, rgba(252, 250, 247, 0) 100%)',
              filter: 'blur(36px)',
            }}
          />
        )}

        {isVerifying && onCancel && (
          <button
            onClick={onCancel}
            className="mb-8 self-start flex items-center gap-2 px-4 py-2 rounded-full border border-black/10 bg-white/40 backdrop-blur-md text-[#171717] hover:bg-white/60 transition-all font-sans text-sm cursor-pointer shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Search
          </button>
        )}

        {/* Hero Headline */}
        {!isVerifying && (
          <div className="relative z-10 text-center max-w-[820px] mb-6 flex flex-col items-center gap-1">
            <div className="overflow-hidden">
              <motion.h1 
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="font-serif text-[72px] font-normal text-[#171717] leading-[0.92] tracking-[-0.03em]"
                style={{
                  textShadow: '0 4px 10px rgba(0,0,0,0.08), 0 2px 3px rgba(0,0,0,0.06), 0 1px 0 rgba(255,255,255,0.85)',
                  filter: 'drop-shadow(0 2px 3px rgba(0, 0, 0, 0.04))'
                }}
              >
                Verify the truth.
              </motion.h1>
            </div>
            <div className="overflow-hidden">
              <motion.h1 
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                className="font-serif text-[72px] font-normal text-[#171717] leading-[0.92] tracking-[-0.03em]"
                style={{
                  textShadow: '0 4px 10px rgba(0,0,0,0.08), 0 2px 3px rgba(0,0,0,0.06), 0 1px 0 rgba(255,255,255,0.85)',
                  filter: 'drop-shadow(0 2px 3px rgba(0, 0, 0, 0.04))'
                }}
              >
                <span 
                  className="italic text-[#C67845]"
                  style={{
                    textShadow: '0 4px 10px rgba(198, 120, 69, 0.18), 0 1px 2px rgba(198, 120, 69, 0.12), 0 1px 0 rgba(255, 255, 255, 0.6)',
                  }}
                >
                  Trust
                </span> with confidence.
              </motion.h1>
            </div>
          </div>
        )}

        {/* Subtitle */}
        {!isVerifying && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.7 }}
            className="relative z-10 text-center max-w-[620px] font-sans text-[22px] font-normal text-[#4A453E] leading-[1.65] mb-10"
            style={{
              textShadow: '0 2px 4px rgba(0, 0, 0, 0.04)',
            }}
          >
            Scrutin uses multi-agent reasoning, real-time evidence, and source credibility to deliver verifiable truth you can trust.
          </motion.p>
        )}

        {/* Main Input Panel: Styled directly as the premium parchment paper notebook card (all outer glass borders removed) */}
        <motion.div
          initial={{ scale: 0.97, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.9 }}
          className="relative w-full max-w-[780px] mb-4 cursor-text overflow-hidden rounded-[20px] z-10"
          style={{
            backgroundImage: `
              radial-gradient(rgba(198, 120, 69, 0.16) 1.5px, transparent 1.5px),
              url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.22'/%3E%3C/svg%3E"),
              linear-gradient(135deg, #FFFFFF 0%, #F6F6F6 100%)
            `,
            backgroundSize: '24px 24px, auto, 100% 100%',
            boxShadow: '0 30px 70px -15px rgba(0, 0, 0, 0.15), 0 10px 25px -10px rgba(0, 0, 0, 0.1), inset 0 0 45px rgba(0, 0, 0, 0.08), inset 0 6px 18px rgba(0, 0, 0, 0.05), inset 0 0 0 1px rgba(255, 255, 255, 0.85), 0 1px 0 rgba(255, 255, 255, 0.5)',
            border: '1px solid rgba(0, 0, 0, 0.08)',
          }}
          onClick={(e) => {
            if (inputRef.current && e.target !== inputRef.current) inputRef.current.focus();
          }}
        >
          {/* Inner Groove Outline - Golden Beige proper grooved track */}
          <div 
            className="absolute inset-2 rounded-[14px] pointer-events-none z-0" 
            style={{
              border: '1.5px solid rgba(198, 120, 69, 0.15)',
              boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.05), inset 0 -1px 0 rgba(255, 255, 255, 0.9), 0 1px 1px rgba(255, 255, 255, 0.7)'
            }} 
          />

          {isVerifying ? (
            <div className="relative z-10 flex flex-col items-center justify-center py-12 px-8 min-h-[220px] overflow-hidden">
              {/* Pulsating & Rippling Logo Container */}
              <div className="relative flex items-center justify-center mb-5" style={{ width: '88px', height: '88px' }}>
                {/* Ripples radiating out */}
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="absolute inset-0 rounded-full bg-[#C67845]/8 border border-[#C67845]/15 pointer-events-none"
                    initial={{ scale: 0.7, opacity: 0.6 }}
                    animate={{ scale: 2.2, opacity: 0 }}
                    transition={{
                      duration: 3.8,
                      repeat: Infinity,
                      delay: i * 1.25,
                      ease: "easeOut"
                    }}
                  />
                ))}

                {/* Grooved socket for the logo to sit in */}
                <div 
                  className="absolute flex items-center justify-center pointer-events-none"
                  style={{
                    width: '72px',
                    height: '72px',
                    borderRadius: '9999px',
                    background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.18) 0%, rgba(255, 255, 255, 0.7) 100%)',
                    boxShadow: 'inset 0 3px 6px rgba(0, 0, 0, 0.3), 0 1.5px 2px rgba(255, 255, 255, 0.9)',
                    padding: '3.5px'
                  }}
                >
                  <div 
                    className="w-full h-full rounded-full flex items-center justify-center"
                    style={{
                      background: 'radial-gradient(circle at 50% 50%, #ECE7DB 0%, #DCD6C5 100%)',
                      boxShadow: 'inset 0 1.5px 3px rgba(0, 0, 0, 0.12)'
                    }}
                  >
                    {/* Central pulsating logo dial with tactile gold highlights */}
                    <motion.div
                      animate={{ scale: [1, 1.03, 1] }}
                      transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
                      className="flex items-center justify-center cursor-default"
                      style={{
                        width: '52px',
                        height: '52px',
                        borderRadius: '9999px',
                        border: '1px solid rgba(212, 175, 55, 0.55)',
                        background: 'radial-gradient(circle at 35% 35%, #332C24 0%, #1F1B16 55%, #0E0C0A 100%)',
                        boxShadow: '0 4px 8px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.22), inset 0 -2.5px 5px rgba(212, 175, 55, 0.3), 0 0 6px rgba(212, 175, 55, 0.18)',
                      }}
                    >
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#D4AF37" />
                        <path d="M2 12L12 17L22 12" stroke="#D4AF37" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M2 17L12 22L22 17" stroke="#D4AF37" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </motion.div>
                  </div>
                </div>
              </div>

              {/* Status messages */}
              <div className="flex flex-col items-center gap-1 z-10 text-center">
                <span 
                  className="font-sans text-[11.5px] font-bold tracking-[0.2em] uppercase text-[#A36C45] animate-pulse"
                  style={{
                    textShadow: '0 1px 1px rgba(255, 255, 255, 0.95), 0 -0.5px 0.5px rgba(0, 0, 0, 0.22)',
                  }}
                >
                  Scrutinizing query
                </span>
                <AnimatePresence mode="wait">
                  <motion.p
                    key={statusIndex}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.35, ease: "easeOut" }}
                    className="font-sans text-[17px] font-extrabold tracking-wide min-h-[26px]"
                    style={{
                      color: '#2B2015',
                      textShadow: '0 1.5px 1px rgba(255, 255, 255, 0.9), 0 -1px 1px rgba(0, 0, 0, 0.2)',
                    }}
                  >
                    {THINKING_STATUSES[statusIndex]}
                  </motion.p>
                </AnimatePresence>
              </div>
            </div>
          ) : (
            <>
              {/* Editable input field text area */}
              <div className="relative z-10 px-7 pt-6 pb-16 flex-1 flex flex-col justify-start">
                {isInputEmpty && (
                  <div className="absolute left-7 top-6 pointer-events-none select-none font-sans text-[17px] text-[#8C8275]/80 leading-relaxed flex items-center">
                    <span>{displayText}</span>
                    <span className="w-[1.5px] h-[20px] bg-[#C67845] ml-[1px] animate-pulse" />
                  </div>
                )}
                <div
                  id="hero-input"
                  ref={inputRef}
                  contentEditable
                  role="textbox"
                  aria-label="Ask anything"
                  className="w-full min-h-[80px] outline-none resize-none bg-transparent font-sans text-[17px] text-[#1F140A] overflow-y-auto leading-relaxed"
                  onInput={(e) => {
                    setIsInputEmpty(!e.currentTarget.innerText.trim());
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit();
                    }
                  }}
                />

                {/* Attached File Preview Thumbnail */}
                {attachedUrl && attachedFile && (
                  <div className="relative mt-4 self-start rounded-[12px] overflow-hidden border border-black/10 bg-[#FCFAF7] p-1.5 shadow-md flex items-center gap-3 pr-8 group/file">
                    {attachedFile.type.startsWith("image/") ? (
                      <img 
                        src={attachedUrl} 
                        alt="attachment preview" 
                        className="w-14 h-14 rounded-[8px] object-cover border border-black/5" 
                      />
                    ) : (
                      <div className="w-14 h-14 rounded-[8px] bg-black/5 flex items-center justify-center border border-black/5 relative overflow-hidden">
                        <video 
                          src={attachedUrl} 
                          className="w-full h-full object-cover" 
                        />
                        <div className="absolute inset-0 bg-black/25 flex items-center justify-center">
                          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z" />
                          </svg>
                        </div>
                      </div>
                    )}
                    <div className="flex flex-col min-w-0 max-w-[200px]">
                      <span className="text-[12.5px] font-semibold text-[#2B2015] truncate">
                        {attachedFile.name}
                      </span>
                      <span className="text-[11px] text-[#6E6254] font-medium">
                        {(attachedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeAttachedFile();
                      }}
                      className="absolute right-1.5 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-black/5 hover:bg-black/10 flex items-center justify-center text-[#4A3B2C] transition-colors focus:outline-none cursor-pointer"
                      aria-label="Remove attachment"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Inside-paper actions area at the bottom right */}
              <div className="absolute bottom-4 right-4 z-20 flex items-center gap-3">
                {/* Hidden File Input */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept="image/*,video/*"
                  className="hidden"
                />

                {/* Upload File / Attachment Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (fileInputRef.current) fileInputRef.current.click();
                  }}
                  className="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 active:scale-95 focus:outline-none cursor-pointer"
                  style={{
                    background: 'rgba(0, 0, 0, 0.04)',
                    border: '1px solid rgba(0, 0, 0, 0.06)',
                    boxShadow: 'inset 0 1px 2px rgba(255, 255, 255, 0.8), 0 1px 1px rgba(0,0,0,0.03)',
                    color: '#6E6254',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0, 0, 0, 0.08)';
                    e.currentTarget.style.color = '#3E3529';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)';
                    e.currentTarget.style.color = '#6E6254';
                  }}
                  aria-label="Attach images or videos"
                >
                  <Paperclip className="w-5 h-5" />
                </button>

                {/* Audio/Mic Button */}
                <button
                  ref={micButtonRef}
                  onClick={handleMicClick}
                  className="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 active:scale-95 focus:outline-none cursor-pointer"
                  style={{
                    background: isListening ? 'rgba(239, 68, 68, 0.1)' : 'rgba(0, 0, 0, 0.04)',
                    border: isListening ? '1px solid rgba(239, 68, 68, 0.2)' : '1px solid rgba(0, 0, 0, 0.06)',
                    boxShadow: 'inset 0 1px 2px rgba(255, 255, 255, 0.8), 0 1px 1px rgba(0,0,0,0.03)',
                    color: isListening ? '#ef4444' : '#6E6254',
                  }}
                  onMouseEnter={(e) => {
                    if (!isListening) {
                      e.currentTarget.style.background = 'rgba(0, 0, 0, 0.08)';
                      e.currentTarget.style.color = '#3E3529';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isListening) {
                      e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)';
                      e.currentTarget.style.color = '#6E6254';
                    }
                  }}
                  aria-label="Voice input"
                >
                  <Mic className={`w-5 h-5 ${isListening ? 'animate-pulse' : ''}`} />
                </button>

                {/* Gold Dial Grooved Submit Button */}
                <div
                  style={{
                    padding: '3.5px',
                    borderRadius: '9999px',
                    background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.05) 0%, rgba(255, 255, 255, 0.8) 100%)',
                    boxShadow: 'inset 0 1.5px 3px rgba(0, 0, 0, 0.15), 0 1px 1px rgba(255, 255, 255, 0.9)',
                  }}
                  className="flex-shrink-0 flex items-center justify-center"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSubmit();
                    }}
                    className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 active:scale-95 focus:outline-none cursor-pointer group/btn"
                    style={{
                      background: 'radial-gradient(circle at 35% 35%, #332C24 0%, #1F1B16 55%, #0E0C0A 100%)',
                      boxShadow: '0 4px 8px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.15), inset 0 -2px 4px rgba(212, 175, 55, 0.2), 0 0 0 1.5px rgba(212, 175, 55, 0.45)',
                      color: '#f4dfa7',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 0 12px rgba(212, 175, 55, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.25), inset 0 -2px 5px rgba(212, 175, 55, 0.25), 0 0 0 1.5px rgba(212, 175, 55, 0.65)';
                      e.currentTarget.style.color = '#fff0c7';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.15), inset 0 -2px 4px rgba(212, 175, 55, 0.2), 0 0 0 1.5px rgba(212, 175, 55, 0.45)';
                      e.currentTarget.style.color = '#f4dfa7';
                    }}
                    aria-label="Submit query"
                  >
                    <ArrowUp className="w-5.5 h-5.5 transition-transform duration-300 group-hover/btn:-translate-y-0.5" />
                  </button>
                </div>
              </div>
            </>
          )}
        </motion.div>

        {/* Recent Searches */}
        {!isVerifying && recentSearches.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.6 }}
            className="flex flex-wrap justify-center items-center gap-2 max-w-[780px] px-4 mb-20 z-10"
          >
            <span className="text-[11.5px] uppercase tracking-widest text-[#5E5143] font-bold mr-1 font-sans opacity-90 drop-shadow-sm">
              Recent:
            </span>
            {recentSearches.map((search, idx) => (
              <button
                key={idx}
                onClick={() => {
                  if (onVerify) onVerify(search.query);
                }}
                className="px-3.5 py-1.5 rounded-full border border-[rgba(255,255,255,0.7)] text-[12.5px] text-[#2B231D] font-medium transition-all hover:scale-105 hover:bg-[rgba(250,248,240,0.9)] active:scale-95 cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.05),inset_0_1px_1px_rgba(255,255,255,0.9)] flex items-center"
                style={{
                  background: 'rgba(238, 234, 222, 0.75)',
                  backdropFilter: 'blur(16px)',
                }}
              >
                <span className="max-w-[180px] truncate drop-shadow-sm">{search.query}</span>
              </button>
            ))}
          </motion.div>
        )}

      </div>
    </div>
    </>
  );
}

