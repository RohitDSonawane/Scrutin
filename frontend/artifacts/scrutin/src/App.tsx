import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { Route, Switch, Router as WouterRouter } from 'wouter';
import { Hero } from '@/components/Hero';
import { Navbar } from '@/components/Navbar';
import { SpatialScroll } from '@/SpatialScroll';
import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import '@/lib/api-config'; // initialise API base URL from VITE_API_URL
import { useVerification } from '@/hooks/useVerification';
import { VerificationResult } from '@/components/VerificationResult';

const queryClient = new QueryClient();

function Home() {
  const [verifying, setVerifying] = useState(false);
  const [queryText, setQueryText] = useState("");
  const { verify, data: verificationResult, isPending, error: verifyError, reset } = useVerification();

  const handleVerify = (text: string) => {
    setQueryText(text);
    setVerifying(true);
    verify({ claim: text }); // ← real POST /api/verify to the Python backend
  };

  const handleCancel = () => {
    setVerifying(false);
    reset(); // clear any pending/errored mutation state
  };

  return (
    <>
      <Navbar />
      <div className="w-full relative min-h-screen flex flex-row overflow-hidden bg-[#FCFAF7]">
        {/* Background Video under the whole container */}
          <div style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
            <video 
              src="https://res.cloudinary.com/dcryxjtb3/video/upload/v1784225334/Video_from_image_prompt_1080p_202607162337_cmez1z.mp4" 
              autoPlay 
              loop 
              muted 
              playsInline 
              style={{ 
                width: '100%', 
                height: '100%', 
                objectFit: 'cover',
                filter: 'saturate(1.38) contrast(1.22) brightness(1.04)'
              }} 
            />
            <div 
              style={{ 
                position: 'absolute', 
                inset: 0, 
                background: 'linear-gradient(to bottom, #FCFAF7 0%, #FCFAF7 18%, rgba(252, 250, 247, 0.68) 28%, rgba(252, 250, 247, 0.15) 100%)' 
              }} 
            />
            {/* Cinematic viewport vignette and edge shadow overlays */}
            <div 
              style={{ 
                position: 'absolute', 
                inset: 0, 
                background: `
                  radial-gradient(circle, transparent 38%, rgba(0, 0, 0, 0.22) 100%),
                  radial-gradient(circle at 0% 0%, rgba(0, 0, 0, 0.18) 0%, transparent 45%), 
                  radial-gradient(circle at 100% 0%, rgba(0, 0, 0, 0.18) 0%, transparent 45%), 
                  radial-gradient(circle at 0% 100%, rgba(0, 0, 0, 0.2) 0%, transparent 45%), 
                  radial-gradient(circle at 100% 100%, rgba(0, 0, 0, 0.2) 0%, transparent 45%), 
                  linear-gradient(to bottom, rgba(0, 0, 0, 0.08) 0%, transparent 20%)
                `,
                pointerEvents: 'none'
              }} 
            />
          </div>
        
        <AnimatePresence mode="wait">
          {verificationResult && !isPending ? (
            <motion.div 
              key="result"
              initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
              animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)' }}
              transition={{ duration: 0.85, ease: [0.76, 0, 0.24, 1] }}
              className="absolute inset-0 z-50 flex justify-center items-start overflow-y-auto no-scrollbar p-4 md:p-8 pt-[80px] pb-24"
            >
              <VerificationResult result={verificationResult} onReset={handleCancel} />
            </motion.div>
          ) : (
            <>
              {/* Left Column: Hero page. Shrinks to 40% width on verification. */}
              <motion.div
                animate={verifying ? { width: '40vw' } : { width: '100vw' }}
                transition={{ duration: 0.85, ease: [0.76, 0, 0.24, 1] }}
                className="relative min-h-screen flex-shrink-0 flex items-center justify-center overflow-hidden z-10"
              >
                <Hero onVerify={handleVerify} isVerifying={verifying} onCancel={handleCancel} />
              </motion.div>

              {/* Right Column: Spatial Scroll cards. Slides in from right. */}
              <AnimatePresence>
                {verifying && (
                  <motion.div
                    key="verification-workspace"
                    initial={{ x: '60vw', opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: '60vw', opacity: 0 }}
                    transition={{ duration: 0.85, ease: [0.76, 0, 0.24, 1] }}
                    className="w-[60vw] h-screen flex-shrink-0 relative overflow-hidden z-10"
                  >
                    <SpatialScroll />
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL?.replace(/\/$/, '') || ''}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
