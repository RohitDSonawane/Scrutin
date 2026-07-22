/**
 * useVerification.ts
 * ==================
 * Custom hook that wires the React UI to the real Scrutin backend via the
 * auto-generated API client.
 *
 * Usage:
 *   const { verify, data, isPending, error, reset } = useVerification();
 *
 *   // Submit a text claim:
 *   verify({ claim: "The Eiffel Tower was built in 1889" });
 *
 *   // Submit a URL:
 *   verify({ url: "https://example.com/article" });
 *
 * The hook delegates to `useVerify` from the generated @workspace/api-client-react
 * package, which issues POST /api/verify to the Python FastAPI backend.
 */
import { useVerify } from "@workspace/api-client-react";
import type {
  VerificationReport,
  VerifyRequest,
} from "@workspace/api-client-react";

export interface UseVerificationReturn {
  /** Call this to start a verification run */
  verify: (input: VerifyRequest) => void;
  /** The final VerificationReport when the run is complete */
  data: VerificationReport | undefined;
  /** True while the orchestrator is running (shows loading UI) */
  isPending: boolean;
  /** Error message if the request failed */
  error: Error | null;
  /** Reset the mutation state (clears data + error) */
  reset: () => void;
}

export function useVerification(): UseVerificationReturn {
  // The generated useVerify wraps the body as { data: VerifyRequest }
  const mutation = useVerify();

  return {
    verify: (input: VerifyRequest) => mutation.mutate({ data: input }),
    data: mutation.data,
    isPending: mutation.isPending,
    error: mutation.error as Error | null,
    reset: mutation.reset,
  };
}
