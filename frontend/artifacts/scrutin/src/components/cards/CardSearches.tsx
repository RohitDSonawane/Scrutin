import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";

const ALL_SEARCHES = [
  { id: 1, text: "Did Elon Musk actually buy Twitter?", count: "14,302", time: "2m ago", trending: true },
  { id: 2, text: "How much did Elon Musk pay for Twitter?", count: "9,847", time: "5m ago", trending: false },
  { id: 3, text: "Why was Twitter renamed to X?", count: "7,231", time: "8m ago", trending: false },
  { id: 4, text: "Original SEC acquisition filing", count: "3,102", time: "12m ago", trending: false },
  { id: 5, text: "Twitter board response to buyout", count: "2,891", time: "15m ago", trending: false },
  { id: 6, text: "Elon Musk net worth after Twitter", count: "11,204", time: "1m ago", trending: true },
  { id: 7, text: "Who is on the Twitter board now?", count: "1,834", time: "20m ago", trending: false },
];

export function CardSearches() {
  const [searches, setSearches] = useState(ALL_SEARCHES.slice(0, 5));
  const [index, setIndex] = useState(5);

  useEffect(() => {
    const timer = setInterval(() => {
      setSearches((prev) => {
        const nextSearches = [...prev.slice(1)];
        nextSearches.push(ALL_SEARCHES[index % ALL_SEARCHES.length]);
        return nextSearches;
      });
      setIndex((prev) => prev + 1);
    }, 1500);
    return () => clearInterval(timer);
  }, [index]);

  return (
    <div className="w-full h-full flex flex-col p-10 bg-[#F6F3EE] relative overflow-hidden">
      <h2 className="font-serif text-[26px] text-[#171717] mb-6">
        What others are asking right now
      </h2>

      <div className="flex-1 relative mt-2 -mx-4 px-4 overflow-hidden mask-image-b">
        {/* We use a mask in CSS ideally, but padding works to show fading edges */}
        <div className="absolute inset-x-4 top-0 h-4 bg-gradient-to-b from-[#F6F3EE] to-transparent z-10 pointer-events-none" />
        <div className="absolute inset-x-4 bottom-0 h-8 bg-gradient-to-t from-[#F6F3EE] to-transparent z-10 pointer-events-none" />
        
        <div className="flex flex-col pt-2">
          <AnimatePresence mode="popLayout">
            {searches.map((search) => (
              <motion.div
                key={search.id}
                layout
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -40 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="py-4 border-b border-black/[0.04] flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <span className="font-sans text-[15px] text-[#171717] group-hover:text-[#C67845] transition-colors">
                    {search.text}
                  </span>
                  {search.trending && (
                    <span className="px-2 py-0.5 rounded-full bg-[#C67845]/10 text-[#C67845] font-sans text-[11px] font-medium tracking-wide">
                      🔥 Trending
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className={`font-sans text-[13px] ${search.trending ? "text-[#C67845]" : "text-[#666666]"}`}>
                    {search.count} searches
                  </span>
                  <span className="font-sans text-[12px] text-[#999999]">
                    {search.time}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-black/[0.04]">
        <button className="flex items-center gap-1.5 font-sans font-medium text-[14px] text-[#C67845] hover:text-[#D28753] transition-colors group">
          Explore all related searches
          <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>
    </div>
  );
}
