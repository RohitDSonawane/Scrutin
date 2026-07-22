import { motion } from "framer-motion";

const NEWS_ITEMS = [
  {
    id: 1,
    source: "Reuters",
    category: "INTERNATIONAL",
    time: "3 minutes ago",
    headline: "UN Security Council convenes emergency session on Ukraine ceasefire proposal"
  },
  {
    id: 2,
    source: "BBC News",
    category: "POLITICS",
    time: "7 minutes ago",
    headline: "Government officials respond to claims about diplomatic negotiations"
  },
  {
    id: 3,
    source: "The Guardian",
    category: "FACT CHECK",
    time: "12 minutes ago",
    headline: "Independent verification: separating confirmed facts from unverified claims"
  },
  {
    id: 4,
    source: "AP News",
    category: "BREAKING",
    time: "1 minute ago",
    headline: "Official statement released contradicting earlier reports"
  }
];

export function CardTrending() {
  return (
    <div className="w-full h-full flex flex-col p-10 bg-[#F6F3EE] relative overflow-hidden">
      {/* Background Map SVG */}
      <svg 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-auto opacity-5 pointer-events-none" 
        viewBox="0 0 1000 500" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2"
      >
        <path d="M200,150 Q250,100 300,120 T400,150 T500,100 T600,180 T700,140 T800,200 T900,150" />
        <path d="M150,250 Q200,200 300,280 T450,220 T550,290 T700,260 T850,320" />
        <path d="M250,350 Q350,300 400,380 T550,320 T650,400 T800,350" />
        {/* Simplified abstract shapes representing continents */}
        <circle cx="300" cy="200" r="100" strokeDasharray="5 5" />
        <circle cx="650" cy="180" r="120" strokeDasharray="5 5" />
        <circle cx="500" cy="350" r="80" strokeDasharray="5 5" />
      </svg>

      <div className="relative z-10">
        <h2 className="font-serif text-[26px] text-[#171717] mb-8">
          Trending around this story
        </h2>

        <div className="flex flex-col gap-0">
          {NEWS_ITEMS.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 + (i * 0.15), ease: "easeOut" }}
              className="py-5 border-b border-black/[0.04] last:border-b-0 flex flex-col gap-2 group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-sans font-medium text-[12px] text-[#666666]">
                    {item.source}
                  </span>
                  <span className="w-1 h-1 rounded-full bg-black/10" />
                  <span className="font-sans text-[10px] tracking-[0.1em] text-[#C67845] font-semibold uppercase">
                    {item.category}
                  </span>
                </div>
                <span className="font-sans text-[12px] text-[#999999]">
                  {item.time}
                </span>
              </div>
              <h3 className="font-sans text-[16px] font-medium text-[#171717] leading-snug group-hover:text-[#C67845] transition-colors cursor-pointer">
                {item.headline}
              </h3>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
