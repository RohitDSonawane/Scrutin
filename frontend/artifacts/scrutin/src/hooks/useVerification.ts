/**
 * useVerification.ts
 * ==================
 * Custom hook that wires the React UI to the Scrutin backend with Server-Sent Events (SSE)
 * for real-time live agent execution traces, falling back to standard POST /api/verify if needed.
 */
import { useState, useCallback, useRef } from "react";
import { useVerify } from "@workspace/api-client-react";
import type {
  VerificationReport,
  VerifyRequest,
} from "@workspace/api-client-react";
import { apiUrl } from "@/lib/api-config";

export interface LogEntry {
  timestamp: string;
  level: string;
  agent: string;
  message: string;
}

export interface AgentStatusMap {
  decomposition: "pending" | "running" | "done";
  evidence: "pending" | "running" | "done";
  credibility: "pending" | "running" | "done";
  forensics: "pending" | "running" | "done";
  adversarial: "pending" | "running" | "done";
}

export interface FindingItem {
  agent: string;
  claim_id: string;
  stance: string;
  confidence: number;
  rationale?: string;
}

export interface UseVerificationReturn {
  verify: (input: VerifyRequest) => void;
  data: VerificationReport | undefined;
  isPending: boolean;
  error: Error | null;
  reset: () => void;
  // Real-time SSE State
  logs: LogEntry[];
  agentStatuses: AgentStatusMap;
  currentStatusMessage: string;
  provisionalVerdict: string | null;
  evaluatorScore: number | null;
  findings: FindingItem[];
  claims: Array<{ claim_id: string; claim_text: string }>;
}

const INITIAL_AGENT_STATUSES: AgentStatusMap = {
  decomposition: "pending",
  evidence: "pending",
  credibility: "pending",
  forensics: "pending",
  adversarial: "pending",
};

export function useVerification(): UseVerificationReturn {
  const [data, setData] = useState<VerificationReport | undefined>(undefined);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatusMap>(INITIAL_AGENT_STATUSES);
  const [currentStatusMessage, setCurrentStatusMessage] = useState<string>("Initializing verification...");
  const [provisionalVerdict, setProvisionalVerdict] = useState<string | null>(null);
  const [evaluatorScore, setEvaluatorScore] = useState<number | null>(null);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [claims, setClaims] = useState<Array<{ claim_id: string; claim_text: string }>>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const fallbackMutation = useVerify();

  const cleanupSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    cleanupSSE();
    setData(undefined);
    setIsPending(false);
    setError(null);
    setLogs([]);
    setAgentStatuses(INITIAL_AGENT_STATUSES);
    setCurrentStatusMessage("Initializing verification...");
    setProvisionalVerdict(null);
    setEvaluatorScore(null);
    setFindings([]);
    setClaims([]);
    fallbackMutation.reset();
  }, [cleanupSSE, fallbackMutation]);

  const verify = useCallback(
    (input: VerifyRequest) => {
      reset();
      setIsPending(true);

      const baseUrl = apiUrl.replace(/\/$/, "");
      const params = new URLSearchParams();
      if (input.claim) params.append("claim", input.claim);
      if (input.url) params.append("url", input.url);

      const streamUrl = `${baseUrl}/verify/stream?${params.toString()}`;

      try {
        const es = new EventSource(streamUrl);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data);
            const evtType = parsed.type;
            const evtData = parsed.data;

            if (evtType === "start") {
              setCurrentStatusMessage(`Started run ${evtData.run_id}`);
            } else if (evtType === "log") {
              setLogs((prev) => [...prev.slice(-99), evtData]);
              if (evtData.message) {
                setCurrentStatusMessage(evtData.message);
              }
            } else if (evtType === "agent_start") {
              const agentName = evtData.agent as keyof AgentStatusMap;
              if (agentName in INITIAL_AGENT_STATUSES) {
                setAgentStatuses((prev) => ({ ...prev, [agentName]: "running" }));
              }
              setCurrentStatusMessage(`Running ${evtData.agent} agent on ${evtData.claim_id}`);
            } else if (evtType === "finding") {
              const agentName = evtData.agent as keyof AgentStatusMap;
              if (agentName in INITIAL_AGENT_STATUSES) {
                setAgentStatuses((prev) => ({ ...prev, [agentName]: "done" }));
              }
              setFindings((prev) => [...prev, evtData]);
            } else if (evtType === "decomposition") {
              if (evtData.claims) {
                setClaims(evtData.claims);
                setAgentStatuses((prev) => ({ ...prev, decomposition: "done" }));
              }
            } else if (evtType === "provisional_verdict") {
              setProvisionalVerdict(evtData.verdict);
            } else if (evtType === "evaluator") {
              setEvaluatorScore(evtData.score);
            } else if (evtType === "final_report") {
              setData(evtData.report);
              setIsPending(false);
              cleanupSSE();
            } else if (evtType === "complete") {
              setIsPending(false);
              cleanupSSE();
            } else if (evtType === "error") {
              setError(new Error(evtData.detail || "Verification streaming error"));
              setIsPending(false);
              cleanupSSE();
            }
          } catch (e) {
            console.error("Failed to parse SSE payload:", e);
          }
        };

        es.onerror = (err) => {
          console.warn("EventSource error, falling back to standard POST /api/verify:", err);
          cleanupSSE();

          fallbackMutation.mutate(
            { data: input },
            {
              onSuccess: (res: VerificationReport) => {
                setData(res);
                setIsPending(false);
              },
              onError: (err: unknown) => {
                setError(err as Error);
                setIsPending(false);
              },
            }
          );
        };
      } catch (err) {
        console.warn("Failed to instantiate EventSource, falling back to POST:", err);
        fallbackMutation.mutate(
          { data: input },
          {
            onSuccess: (res: VerificationReport) => {
              setData(res);
              setIsPending(false);
            },
            onError: (err: unknown) => {
              setError(err as Error);
              setIsPending(false);
            },
          }
        );
      }
    },
    [cleanupSSE, fallbackMutation, reset]
  );

  return {
    verify,
    data,
    isPending,
    error,
    reset,
    logs,
    agentStatuses,
    currentStatusMessage,
    provisionalVerdict,
    evaluatorScore,
    findings,
    claims,
  };
}
