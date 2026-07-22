import { motion } from "framer-motion";
import { useState, useEffect } from "react";

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`fixed top-0 left-0 right-0 z-50 h-[80px] flex items-center px-8 transition-colors duration-300 ${
        isScrolled ? "bg-[#FCFAF7]/80 backdrop-blur-md border-b border-black/[0.04]" : "bg-transparent"
      }`}
    >
      <div className="flex items-center gap-3">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#171717" />
          <path d="M2 17L12 22L22 17" stroke="#171717" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M2 12L12 17L22 12" stroke="#171717" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="font-sans font-medium text-[#171717] tracking-tight">SCRUTIN</span>
      </div>
    </motion.nav>
  );
}
