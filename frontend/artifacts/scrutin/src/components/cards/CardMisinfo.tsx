import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

const MISINFO_ITEMS = [
  {
    id: 1,
    location: "Pune, Maharashtra",
    claim: "AI-generated flood images circulating on social media",
    spread: { label: "High Spread", color: "bg-[#D97706]", text: "text-[#D97706]", bgLight: "bg-[#D97706]/10" },
    platforms: "WhatsApp · Facebook",
    updated: "45 minutes ago",
    status: { label: "Verified False", dot: "bg-[#3BAA65]" }
  },
  {
    id: 2,
    location: "Delhi NCR",
    claim: "WhatsApp election rumours about candidate disqualification",
    spread: { label: "Medium Spread", color: "bg-[#2563EB]/80", text: "text-[#2563EB]", bgLight: "bg-[#2563EB]/10" },
    platforms: "WhatsApp · Twitter",
    updated: "2 hours ago",
    status: { label: "Under Investigation", dot: "bg-[#999999]" }
  },
  {
    id: 3,
    location: "Mumbai",
    claim: "Old bridge collapse video being reshared as recent event",
    spread: { label: "Resurfacing", color: "bg-[#666666]", text: "text-[#666666]", bgLight: "bg-[#666666]/10" },
    platforms: "Twitter · Telegram",
    updated: "6 hours ago",
    status: { label: "Verified False", dot: "bg-[#3BAA65]" }
  }
];

export function CardMisinfo() {
  return (
    <div className="w-full h-full flex flex-col p-10 bg-[#F6F3EE] relative overflow-hidden">
      <div className="mb-6">
        <h2 className="font-serif text-[26px] text-[#171717] mb-1">
          Potential misinformation near you
        </h2>
        <p className="font-sans text-[13px] text-[#666666]">
          Detected in your region &middot; Updated 2 minutes ago
        </p>
      </div>

      <div className="flex flex-col gap-3 flex-1 overflow-y-auto">
        {MISINFO_ITEMS.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 + (i * 0.1), ease: "easeOut" }}
            className="rounded-[12px] bg-white/70 border border-black/[0.07] p-4 flex flex-col gap-3"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex flex-col gap-1">
                <span className="font-sans font-medium text-[14px] text-[#171717]">
                  {item.location}
                </span>
                <span className="font-sans text-[14px] text-[#171717] leading-snug">
                  {item.claim}
                </span>
              </div>
              <span className={`shrink-0 px-2 py-0.5 rounded-full ${item.spread.bgLight} ${item.spread.text} font-sans text-[11px] font-medium tracking-wide`}>
                {item.spread.label}
              </span>
            </div>

            <div className="flex items-center justify-between mt-1 pt-3 border-t border-black/[0.04]">
              <div className="flex flex-col gap-0.5">
                <span className="font-sans text-[11px] font-medium text-[#666666]">
                  {item.platforms}
                </span>
                <span className="font-sans text-[11px] text-[#999999]">
                  {item.updated}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${item.status.dot}`} />
                <span className="font-sans text-[12px] text-[#666666]">
                  {item.status.label}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-black/[0.04]">
        <button className="flex items-center gap-1.5 font-sans font-medium text-[14px] text-[#C67845] hover:text-[#D28753] transition-colors group">
          See regional misinformation report
          <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>
    </div>
  );
}
