"use client";

import React, { useState, useEffect } from "react";
import { 
  Shield, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Database, 
  Cpu, 
  TrendingUp, 
  Terminal, 
  FileText, 
  Zap, 
  Check, 
  X, 
  RotateCcw, 
  RefreshCw, 
  Sparkles,
  Server,
  UserCheck,
  Sun,
  Moon
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid
} from "recharts";


// Types matching backend models
interface Service {
  id: string;
  name: string;
  status: "healthy" | "warning" | "critical" | "recovering";
  dependencies: string[];
}


interface Metric {
  service_id: string;
  cpu_usage: number;
  memory_usage: number;
  request_rate: number;
  error_rate: number;
  latency: number;
  active_connections: number;
  db_pool_utilization: number;
  timestamp: string;
  pue?: number;
  it_power_kw?: number;
  cooling_power_kw?: number;
  diurnal_factor?: number;
  temperature?: number;
}

interface Incident {
  id: string;
  title: string;
  description: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "detected" | "investigating" | "proposed" | "executing" | "verified" | "resolved" | "failed";
  service_id: string;
  detected_at: string;
  resolved_at: string | null;
  root_cause: string | null;
  confidence: number | null;
}

interface IncidentEvent {
  id: number;
  incident_id: string;
  timestamp: string;
  sender: string;
  message: string;
}

interface RemediationPlan {
  id: number;
  incident_id: string;
  runbook: string;
  target: string;
  reason: string;
  risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  rollback_available: boolean;
  status: "proposed" | "approved" | "rejected" | "executing" | "completed" | "failed" | "rolled_back";
}

interface PostMortem {
  id: number;
  incident_id: string;
  created_at: string;
  mttd: number;
  mttr: number;
  timeline: { timestamp: string; sender: string; message: string }[];
  root_cause: string;
  evidence: string;
  actions_executed: { runbook: string; target: string; status: string }[];
  preventive_recommendations: string;
}

const HISTORICAL_INCIDENTS = [
  { id: "inc_hist_001", title: "Database pool exhaustion", service: "Database Service", root_cause: "Connection Pool Exhaustion", runbook: "increase_pool_limit", mttr: 42, count: 1, symptoms: "Database connection pool saturated (100% capacity)." },
  { id: "inc_hist_002", title: "Payment service memory leak", service: "Payment Service", root_cause: "Memory Leak", runbook: "rolling_restart", mttr: 65, count: 1, symptoms: "Monotonic growth of memory usage on Payment Service." },
  { id: "inc_hist_003", title: "Database crashed (out of descriptors)", service: "Database Service", root_cause: "Descriptor Crash", runbook: "restart_service", mttr: 28, count: 1, symptoms: "CRITICAL - Database engine panicked: out of file descriptors" },
  { id: "inc_hist_004", title: "Auth Service token verification latency", service: "Auth Service", root_cause: "CPU Saturation", runbook: "scale_service", mttr: 35, count: 1, symptoms: "Token decrypt thread pool saturated. Task queue backlog > 1000." },
  { id: "inc_hist_005", title: "Order Service lock timeout contention", service: "Order Service", root_cause: "Transaction Contention", runbook: "activate_circuit_breaker", mttr: 50, count: 1, symptoms: "Database lock timeout: could not acquire write lock on orders table" },
  { id: "inc_hist_006", title: "API Gateway TLS connection leak", service: "API Gateway", root_cause: "Connection Leak", runbook: "restart_service", mttr: 20, count: 1, symptoms: "Max open connections reached (500). Dropping incoming SYN packet." },
  { id: "inc_hist_007", title: "Payment gateway HTTP 502 Stripe outage", service: "Payment Service", root_cause: "Downstream Outage", runbook: "activate_circuit_breaker", mttr: 15, count: 1, symptoms: "HTTP 502 Bad Gateway from api.stripe.com" },
  { id: "inc_hist_008", title: "Database service index fragmentation", service: "Database Service", root_cause: "Index Fragmentation", runbook: "scale_service", mttr: 80, count: 1, symptoms: "Slow query logged (1150ms): SELECT * FROM orders WHERE user_id = ..." },
  { id: "inc_hist_009", title: "Auth Service cache sync delay", service: "Auth Service", root_cause: "Redis Lag", runbook: "restart_service", mttr: 48, count: 1, symptoms: "Cache replication queue delayed. Lag count: 485 items." },
  { id: "inc_hist_010", title: "Order Service task CPU throttling", service: "Order Service", root_cause: "CPU Throttling", runbook: "scale_service", mttr: 30, count: 1, symptoms: "CPU throttle limit reached. Docker cgroups throttling container." }
];

const RAG_SERVICE_FREQUENCY_DATA = [
  { name: "Database Service", count: 3, fill: "#8b5cf6" },
  { name: "Auth Service", count: 2, fill: "#10b981" },
  { name: "Payment Service", count: 2, fill: "#ec4899" },
  { name: "Order Service", count: 2, fill: "#f59e0b" },
  { name: "API Gateway", count: 1, fill: "#3b82f6" }
];

const RAG_RESOLUTION_MTTR_DATA = [
  { name: "inc_001", mttr: 42, label: "DB Pool" },
  { name: "inc_002", mttr: 65, label: "Pay Leak" },
  { name: "inc_003", mttr: 28, label: "DB Crash" },
  { name: "inc_004", mttr: 35, label: "Auth CPU" },
  { name: "inc_005", mttr: 50, label: "Order Cont" },
  { name: "inc_006", mttr: 20, label: "Gateway Leak" },
  { name: "inc_007", mttr: 15, label: "Pay Ext" },
  { name: "inc_008", mttr: 80, label: "DB Frag" },
  { name: "inc_009", mttr: 48, label: "Auth Lag" },
  { name: "inc_010", mttr: 30, label: "Order Throt" }
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"overview" | "topology" | "incidents" | "approvals" | "reports" | "rag">("overview");
  const [backendConnected, setBackendConnected] = useState<boolean>(false);
  const [sseStatus, setSseStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [feedEvents, setFeedEvents] = useState<Array<{ time: string; sender: string; msg: string; type: string }>>([]);
  
  // State for data
  const [services, setServices] = useState<Service[]>([
    { id: "gateway", name: "API Gateway", status: "healthy", dependencies: ["auth_service", "order_service"] },
    { id: "auth_service", name: "Auth Service", status: "healthy", dependencies: [] },
    { id: "order_service", name: "Order Service", status: "healthy", dependencies: ["payment_service", "database_service"] },
    { id: "payment_service", name: "Payment Service", status: "healthy", dependencies: [] },
    { id: "database_service", name: "Database Service", status: "healthy", dependencies: [] }
  ]);
  
  const [metrics, setMetrics] = useState<Record<string, Metric>>({});
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [selectedIncidentEvents, setSelectedIncidentEvents] = useState<IncidentEvent[]>([]);
  const [selectedIncidentPlans, setSelectedIncidentPlans] = useState<RemediationPlan[]>([]);
  
  const [pendingApprovals, setPendingApprovals] = useState<RemediationPlan[]>([]);
  const [completedReports, setCompletedReports] = useState<PostMortem[]>([]);
  const [selectedReport, setSelectedReport] = useState<PostMortem | null>(null);
  const [hardwareLogs, setHardwareLogs] = useState<any[]>([]);
  const [historicalData, setHistoricalData] = useState<any[]>([]);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [palette, setPalette] = useState<"emerald" | "indigo" | "amber" | "teal">("emerald");
  const [focusedMetric, setFocusedMetric] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState<boolean>(false);
  const [apiUrl, setApiUrl] = useState<string>("http://localhost:8000");
  const [showConfigModal, setShowConfigModal] = useState<boolean>(false);
  const [tempUrl, setTempUrl] = useState<string>("http://localhost:8000");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sentinelops_api_url");
      if (saved) {
        setApiUrl(saved);
        setTempUrl(saved);
      } else {
        const defaultUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        setApiUrl(defaultUrl);
        setTempUrl(defaultUrl);
      }
    }
  }, []);

  // Hydration handling
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Fetch reports when switching to the Reports tab
  useEffect(() => {
    if (activeTab === "reports") {
      fetchReports();
    }
  }, [activeTab]);

  // Sync theme and palette with HTML class
  useEffect(() => {
    if (typeof window !== "undefined") {
      const root = window.document.documentElement;
      
      // Remove other theme classes
      root.classList.remove("theme-emerald", "theme-indigo", "theme-amber", "theme-teal");
      root.classList.add(`theme-${palette}`);
      
      if (theme === "dark") {
        root.classList.add("dark");
      } else {
        root.classList.remove("dark");
      }
    }
  }, [theme, palette]);

  // Check health and initialize connection
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/health`);
        if (res.ok) {
          setBackendConnected(true);
          // Initial fetches
          fetchServices();
          fetchIncidents();
          fetchHardwareLogs();
          fetchPendingApprovals();
          fetchReports();
        } else {
          setBackendConnected(false);
        }
      } catch (err) {
        setBackendConnected(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  // Fetch functions
  const fetchServices = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/services`);
      if (res.ok) {
        const data = await res.json();
        setServices(data);
      }
    } catch (e) {
      console.error("Error fetching services", e);
    }
  };

  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/incidents`);
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);
        // Also split out pending approvals
        // And update selected incident if applicable
      }
    } catch (e) {
      console.error("Error fetching incidents", e);
    }
  };

  const fetchPendingApprovals = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/approvals`);
      if (res.ok) {
        const data = await res.json();
        setPendingApprovals(data);
      }
    } catch (e) {
      console.error("Error fetching approvals", e);
    }
  };

  const fetchHardwareLogs = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/hardware/logs`);
      if (res.ok) {
        const data = await res.json();
        setHardwareLogs(data);
      }
    } catch (e) {
      console.error("Error fetching hardware logs", e);
    }
  };

  const fetchReports = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/reports`);
      if (res.ok) {
        const data = await res.json();
        setCompletedReports(data);
      }
    } catch (e) {
      console.error("Error fetching reports", e);
    }
  };

  const getHardwareNodeChartData = () => {
    const counts: Record<string, number> = {};
    hardwareLogs.forEach(log => {
      const node = log.service_id || "Other";
      counts[node] = (counts[node] || 0) + 1;
    });
    return Object.entries(counts).map(([name, count]) => ({
      name: name.replace("_service", "").toUpperCase(),
      count
    }));
  };

  const getNodeColor = (name: string) => {
    switch (name.toLowerCase()) {
      case "gateway": return "#3b82f6";
      case "auth": return "#10b981";
      case "order": return "#f59e0b";
      case "payment": return "#ec4899";
      case "database": return "#8b5cf6";
      default: return "#71717a";
    }
  };

  // SSE Event stream listener
  useEffect(() => {
    setSseStatus("connecting");
    const es = new EventSource(`${apiUrl}/api/events/stream`);

    es.onopen = () => {
      setSseStatus("connected");
      logger("System", "Event stream established with SentinelOps core", "info");
    };

    es.onerror = () => {
      setSseStatus("disconnected");
      logger("System", "Event stream disconnected. Retrying...", "warn");
    };

    // Generic event list handler
    const handleSseEvent = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data);
        logger(parsed.sender || "Core", parsed.message || JSON.stringify(parsed), parsed.level || "info");
        
        // Dynamic state updates based on event type
        if (parsed.type === "metric") {
          setMetrics(prev => ({ ...prev, [parsed.data.service_id]: parsed.data }));
        } else if (parsed.type === "incident_new") {
          setIncidents(prev => [parsed.data, ...prev]);
        } else if (parsed.type === "incident_update") {
          setIncidents(prev => prev.map(inc => inc.id === parsed.data.id ? parsed.data : inc));
          if (selectedIncident && selectedIncident.id === parsed.data.id) {
            setSelectedIncident(parsed.data);
          }
        } else if (parsed.type === "service_update") {
          setServices(prev => prev.map(s => s.id === parsed.data.id ? parsed.data : s));
        } else if (parsed.type === "remediation_proposed") {
          setPendingApprovals(prev => [...prev, parsed.data]);
        }
      } catch (err) {
        // SSE formatting fallback
      }
    };

    es.addEventListener("ping", () => {});
    es.addEventListener("heartbeat", () => {});
    
    // Listen for custom events
    es.addEventListener("telemetry", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setMetrics(prev => ({ ...prev, [data.service_id]: data }));
      
      setHistoricalData(prev => {
        const timeLabel = new Date(data.timestamp).toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit' 
        });
        const existingIdx = prev.findIndex(item => item.time === timeLabel);
        let updated = [...prev];
        const keyId = data.service_id.replace(/-/g, "_");
        
        if (existingIdx >= 0) {
          updated[existingIdx] = {
            ...updated[existingIdx],
            [`${keyId}_cpu`]: data.cpu_usage,
            [`${keyId}_mem`]: data.memory_usage,
            [`${keyId}_lat`]: data.latency,
            [`${keyId}_err`]: data.error_rate
          };
        } else {
          updated.push({
            time: timeLabel,
            [`${keyId}_cpu`]: data.cpu_usage,
            [`${keyId}_mem`]: data.memory_usage,
            [`${keyId}_lat`]: data.latency,
            [`${keyId}_err`]: data.error_rate
          });
        }
        
        if (updated.length > 15) {
          updated = updated.slice(updated.length - 15);
        }
        return updated;
      });
    });

    es.addEventListener("incident_event", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      logger(data.sender, data.message, "info");
      
      if (selectedIncident && selectedIncident.id === data.incident_id) {
        fetchIncidentDetails(data.incident_id);
      }
      fetchIncidents();
      fetchReports();
    });

    es.addEventListener("remediation_proposed", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      logger("Remediator", `New remediation plan proposed: ${data.runbook} on target ${data.target}`, "warn");
      fetchPendingApprovals();
    });

    es.addEventListener("remediation_approved", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      logger("Remediator", `Remediation plan approved: ${data.runbook} on target ${data.target}`, "info");
      fetchPendingApprovals();
    });

    return () => {
      es.close();
    };
  }, [apiUrl, selectedIncident]);

  const fetchIncidentDetails = async (incId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/incidents/${incId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedIncident(data);
        setSelectedIncidentEvents(data.events || []);
        setSelectedIncidentPlans(data.remediation_plans || []);
      }
    } catch (e) {}
  };

  const logger = (sender: string, msg: string, type: string = "info") => {
    const time = new Date().toLocaleTimeString();
    setFeedEvents(prev => [{ time, sender, msg, type }, ...prev.slice(0, 49)]);
  };

  // Demo Trigger Scenarios
  const triggerScenario = async (scenarioId: string) => {
    logger("Operator", `Triggering scenario scenario_${scenarioId}`, "warn");
    try {
      const res = await fetch(`${apiUrl}/api/demo/scenario/${scenarioId}`, {
        method: "POST"
      });
      if (res.ok) {
        logger("Core", `Scenario ${scenarioId} injected successfully`, "info");
      }
    } catch (err) {
      // Offline fallback simulation
      simulateOfflineScenario(scenarioId);
    }
  };

  const simulateOfflineScenario = (scenarioId: string) => {
    logger("System", "Running DEMO fallback mode (Backend offline)", "warn");
    if (scenarioId === "1") {
      logger("Detector", "CPU / Connection pool usage anomaly on database_service detected", "error");
      setServices(prev => prev.map(s => s.id === "database_service" ? { ...s, status: "critical" } : s));
      // Simulate incident
      const mockInc: Incident = {
        id: "inc_db_pool",
        title: "database_service Connection Pool Exhaustion",
        description: "Database queries timing out. Gateway reporting high latency.",
        severity: "CRITICAL",
        status: "investigating",
        service_id: "database_service",
        detected_at: new Date().toISOString(),
        resolved_at: null,
        root_cause: null,
        confidence: null
      };
      setIncidents(prev => [mockInc, ...prev]);
      setSelectedIncident(mockInc);
      setActiveTab("incidents");
    }
  };

  const handleApprove = async (planId: number) => {
    const plan = pendingApprovals.find(p => p.id === planId);
    if (!plan) return;
    
    logger("Operator", `Approving remediation plan #${planId} for incident ${plan.incident_id}`, "info");
    try {
      const res = await fetch(`${apiUrl}/api/incidents/${plan.incident_id}/approve`, {
        method: "POST"
      });
      if (res.ok) {
        logger("Core", `Remediation runbook approved: starting execution`, "info");
        setPendingApprovals(prev => prev.filter(p => p.id !== planId));
        fetchIncidents();
      }
    } catch (err) {
      logger("System", `Connection error during approval: ${err}`, "error");
    }
  };

  const handleReject = async (planId: number) => {
    const plan = pendingApprovals.find(p => p.id === planId);
    if (!plan) return;

    logger("Operator", `Rejecting remediation plan #${planId} for incident ${plan.incident_id}`, "info");
    try {
      const res = await fetch(`${apiUrl}/api/incidents/${plan.incident_id}/reject`, {
        method: "POST"
      });
      if (res.ok) {
        logger("Core", `Remediation runbook rejected`, "warn");
        setPendingApprovals(prev => prev.filter(p => p.id !== planId));
        fetchIncidents();
      }
    } catch (err) {
      logger("System", `Connection error during rejection: ${err}`, "error");
    }
  };

  // Helper colors for badges
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "healthy": return "bg-green-950/40 text-green-400 border border-green-800/40";
      case "warning": return "bg-yellow-950/40 text-yellow-400 border border-yellow-800/40";
      case "critical": return "bg-red-950/40 text-red-400 border border-red-800/40";
      case "recovering": return "bg-blue-950/40 text-blue-400 border border-blue-800/40";
      default: return "bg-zinc-800 text-zinc-400 border border-zinc-700";
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground antialiased font-sans transition-colors duration-300 bg-grid-glow relative">
      {/* Header Bar */}
      <header className="border-b border-border bg-background/85 backdrop-blur sticky top-0 z-50 transition-colors duration-300 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-lg border border-primary/20 text-primary shadow-[0_0_15px_rgba(34,197,94,0.1)] transition-colors duration-300">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-wider text-foreground flex items-center gap-2">
                SENTINEL<span className="text-primary font-extrabold transition-colors duration-300">OPS</span>
              </h1>
              <p className="text-[10px] text-muted-foreground font-mono tracking-widest uppercase">Self-Healing Infrastructure Core</p>
            </div>
          </div>
          
          {/* Theme Inspector & Connection Status badges */}
          <div className="flex items-center gap-3">
            {/* Theme & Palette Selector */}
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-card border border-border text-xs shadow-sm transition-all duration-300">
              <span className="text-[9px] font-mono text-muted-foreground uppercase mr-1 select-none">Palette:</span>
              <div className="flex gap-1.5 mr-2">
                <button 
                  onClick={() => setPalette("emerald")} 
                  className={`h-3 w-3 rounded-full bg-[#10b981] hover:scale-110 transition-transform cursor-pointer ${palette === "emerald" ? "ring-1 ring-foreground ring-offset-1 ring-offset-background" : ""}`}
                  title="Neon Emerald"
                />
                <button 
                  onClick={() => setPalette("indigo")} 
                  className={`h-3 w-3 rounded-full bg-[#6366f1] hover:scale-110 transition-transform cursor-pointer ${palette === "indigo" ? "ring-1 ring-foreground ring-offset-1 ring-offset-background" : ""}`}
                  title="Cyberpunk Indigo"
                />
                <button 
                  onClick={() => setPalette("amber")} 
                  className={`h-3 w-3 rounded-full bg-[#f59e0b] hover:scale-110 transition-transform cursor-pointer ${palette === "amber" ? "ring-1 ring-foreground ring-offset-1 ring-offset-background" : ""}`}
                  title="Solar Amber"
                />
                <button 
                  onClick={() => setPalette("teal")} 
                  className={`h-3 w-3 rounded-full bg-[#06b6d4] hover:scale-110 transition-transform cursor-pointer ${palette === "teal" ? "ring-1 ring-foreground ring-offset-1 ring-offset-background" : ""}`}
                  title="Teal Quantum"
                />
              </div>
              <button
                onClick={() => setTheme(prev => prev === "dark" ? "light" : "dark")}
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground cursor-pointer transition-colors duration-300 border-l border-border pl-2 ml-1"
                title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
              >
                {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              </button>
            </div>

            <div 
              onClick={() => setShowConfigModal(true)}
              className="flex items-center gap-2 px-3 py-1 rounded-full bg-card border border-border text-xs shadow-sm hover:border-primary/50 cursor-pointer transition-colors duration-200"
              title="Click to configure API URL"
            >
              <span className={`h-2 w-2 rounded-full ${backendConnected ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" : "bg-red-500"}`}></span>
              <span className="text-muted-foreground font-semibold">Backend:</span>
              <span className="font-mono text-foreground">{backendConnected ? "Connected" : "Disconnected"}</span>
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-card border border-border text-xs shadow-sm">
              <span className={`h-2 w-2 rounded-full ${sseStatus === "connected" ? "bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" : sseStatus === "connecting" ? "bg-yellow-500 animate-pulse" : "bg-red-500"}`}></span>
              <span className="text-muted-foreground">Events:</span>
              <span className="font-mono text-foreground capitalize">{sseStatus}</span>
            </div>
          </div>
        </div>
      </header>

      {/* API Endpoint Configuration Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => setShowConfigModal(false)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground p-1 rounded-lg cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-base font-semibold text-foreground mb-1 flex items-center gap-2">
              <Zap className="h-5 w-5 text-primary animate-pulse" /> Configure API URL
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Set the backend API connection endpoint for SentinelOps SRE metrics.
            </p>
            <div className="flex flex-col gap-3">
              <div>
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider block mb-1">API Address</label>
                <input 
                  type="text" 
                  value={tempUrl} 
                  onChange={(e) => setTempUrl(e.target.value)} 
                  placeholder="e.g. http://localhost:8000 or https://api.my-sentinel.com"
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:border-primary/50 transition-colors"
                />
              </div>
              <div className="text-[10px] text-muted-foreground leading-relaxed bg-background/50 p-2.5 rounded-lg border border-border">
                <strong>Note:</strong> Connecting from HTTPS pages (GitHub Pages) to insecure HTTP endpoints will be blocked by browsers. Use an HTTPS tunnel (e.g. ngrok) or cloud hosting.
              </div>
              <div className="flex gap-2 justify-end mt-2">
                <button 
                  onClick={() => setShowConfigModal(false)}
                  className="px-3.5 py-1.5 rounded-xl border border-border text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    localStorage.setItem("sentinelops_api_url", tempUrl);
                    setApiUrl(tempUrl);
                    setShowConfigModal(false);
                    // Force refresh health check
                    window.location.reload();
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-primary text-background text-xs font-bold hover:bg-primary/95 transition-colors cursor-pointer"
                >
                  Save URL
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-1 max-w-7xl w-full mx-auto px-4 py-6 gap-6">
        
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col gap-6 min-w-0">
          
          {focusedMetric ? (
            <div className="flex flex-col gap-6 animate-in fade-in duration-300">
              {/* Sub-page Header */}
              <div className="flex items-center justify-between border-b border-border pb-4">
                <div className="flex flex-col gap-1">
                  <button 
                    onClick={() => setFocusedMetric(null)}
                    className="text-xs font-semibold text-primary hover:underline flex items-center gap-1 cursor-pointer mb-2"
                  >
                    &larr; Back to Dashboard Cockpit
                  </button>
                  <h2 className="text-xl font-bold text-foreground capitalize flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary animate-pulse" /> 
                    {focusedMetric} Utilization Analysis & Diagnostics
                  </h2>
                  <p className="text-xs text-muted-foreground font-sans">Live telemetry trend lines, incident thresholds, and automated anomaly diagnostic reports.</p>
                </div>
                <div className="px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-muted-foreground shadow-sm">
                  Status: <span className="font-bold text-green-500 font-mono">LIVE MONITORING</span>
                </div>
              </div>

              {/* Grid content */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Massive Chart (2/3 width) */}
                <div className="lg:col-span-2 bg-card/45 border border-border rounded-xl p-6 flex flex-col gap-4 shadow-sm">
                  <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">
                    Detailed Trend Line ({focusedMetric === "latency" ? "ms" : "%"})
                  </h3>
                  <div className="h-[400px] w-full bg-background p-3 rounded-lg border border-border">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={historicalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
                        <XAxis dataKey="time" tick={{ fill: theme === 'dark' ? '#71717a' : '#64748b', fontSize: 10 }} />
                        <YAxis tick={{ fill: theme === 'dark' ? '#71717a' : '#64748b', fontSize: 10 }} />
                        <Tooltip contentStyle={{ backgroundColor: theme === 'dark' ? '#121214' : '#ffffff', border: '1px solid var(--border)', borderRadius: '8px' }} labelClassName="text-xs text-muted-foreground" />
                        
                        {/* Render lines dynamically based on selected metric and active services */}
                        {services.map((service, index) => {
                          const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#ef4444", "#06b6d4", "#a855f7", "#eab308"];
                          const suffix = focusedMetric === "cpu" ? "cpu" : focusedMetric === "memory" ? "mem" : focusedMetric === "latency" ? "lat" : "err";
                          const label = focusedMetric === "cpu" ? "CPU" : focusedMetric === "memory" ? "Memory" : focusedMetric === "latency" ? "Latency" : "Errors";
                          return (
                            <Line 
                              key={service.id} 
                              type="monotone" 
                              dataKey={`${service.id.replace(/-/g, "_")}_${suffix}`} 
                              name={`${service.name} ${label}`} 
                              stroke={colors[index % colors.length]} 
                              strokeWidth={2.5} 
                              dot={false} 
                              isAnimationActive={false} 
                            />
                          );
                        })}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Right Panel (1/3 width) - Dynamic Telemetry Report */}
                <div className="flex flex-col gap-6">
                  {/* Summary Report */}
                  <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
                    <h4 className="font-bold text-xs text-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <FileText className="h-4 w-4 text-primary" /> Metrics Diagnostic Report
                    </h4>
                    
                    {/* Dynamic report content based on metric type */}
                    <div className="flex flex-col gap-3 text-xs text-muted-foreground font-sans leading-relaxed">
                      {focusedMetric === "cpu" && (
                        <>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Core Thermal Threshold: 80%</span>
                            <p>Current health checks indicate that CPU load is nominal under baseline flow. Spikes correlates directly to DB connection stress levels.</p>
                          </div>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Diagnostic Conclusion:</span>
                            <p>Should CPU exceed 80% on `database_service`, SentinelOps is trained to check connection leakage and roll out threadpool recovery runbooks.</p>
                          </div>
                        </>
                      )}
                      {focusedMetric === "memory" && (
                        <>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Leak Limit: 75%</span>
                            <p>Memory allocations are monitored using Isolation Forest. A slope rise indicates active garbage-collector leaks.</p>
                          </div>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Diagnostic Conclusion:</span>
                            <p>Under Scenario 2 (Memory Leak), `payment_service` RAM allocations spike above 85% causing heap death. Action plan: roll back or hot restart the pods.</p>
                          </div>
                        </>
                      )}
                      {focusedMetric === "latency" && (
                        <>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Timeout Threshold: 2000ms</span>
                            <p>Cascading timeouts propagate upstream. A database delay of 4.5s causes orders and payments API gateway calls to queue up.</p>
                          </div>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Diagnostic Conclusion:</span>
                            <p>Slow db queries clog gateway connections. Auto-scale rules or caching filters should be deployed to prevent threadpool starvation.</p>
                          </div>
                        </>
                      )}
                      {focusedMetric === "errors" && (
                        <>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Error Rate Alert Limit: 5.0%</span>
                            <p>Any non-zero error rate triggers instant alert correlation. Multi-service failures indicates shared infrastructure blockage.</p>
                          </div>
                          <div className="p-3 bg-background border border-border rounded-lg flex flex-col gap-1">
                            <span className="font-semibold text-foreground">Diagnostic Conclusion:</span>
                            <p>High API Gateway error rates (e.g. 45%) indicate downstream dependencies (Order/Auth services) are unresponsive or connection pool is exhausted.</p>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Active Anomaly Alerts Log */}
                  <div className="bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col gap-3">
                    <h4 className="font-bold text-xs text-foreground uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="h-4 w-4 text-red-500" /> Active Anomaly Log
                    </h4>
                    
                    <div className="flex flex-col gap-2 overflow-y-auto max-h-[220px]">
                      {incidents.filter(inc => inc.status !== "resolved").length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground text-[10px]">
                          No active anomalies reported for this metric.
                        </div>
                      ) : (
                        incidents
                          .filter(inc => inc.status !== "resolved")
                          .map((inc, index) => (
                            <div key={index} className="p-2.5 bg-background border border-border rounded-lg flex flex-col gap-1 text-[10px]">
                              <div className="flex justify-between items-center mb-1">
                                <span className="font-bold text-red-500 uppercase tracking-wider">Alert #{inc.id}</span>
                                <span className="text-muted-foreground">{new Date(inc.detected_at).toLocaleTimeString()}</span>
                              </div>
                              <p className="text-foreground font-semibold leading-snug">{inc.title}</p>
                              <span className="text-muted-foreground mt-1 block">Service Node: {inc.service_id}</span>
                            </div>
                          ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Tabs Navigation */}
          <div className="flex border-b border-border transition-colors duration-300">
            <button 
              onClick={() => setActiveTab("overview")}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors duration-300 ${activeTab === "overview" ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <Activity className="inline-block h-4 w-4 mr-2" /> Overview
            </button>
            <button 
              onClick={() => setActiveTab("topology")}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors duration-300 ${activeTab === "topology" ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <Server className="inline-block h-4 w-4 mr-2" /> Service Topology
            </button>
            <button 
              onClick={() => setActiveTab("incidents")}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors duration-300 ${activeTab === "incidents" ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <AlertTriangle className="inline-block h-4 w-4 mr-2" /> Incident Command {incidents.filter(i => i.status !== "resolved").length > 0 && (
                <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full ml-1 font-bold">
                  {incidents.filter(i => i.status !== "resolved").length}
                </span>
              )}
            </button>
            <button 
              onClick={() => setActiveTab("approvals")}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors duration-300 ${activeTab === "approvals" ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <UserCheck className="inline-block h-4 w-4 mr-2" /> Approvals {pendingApprovals.length > 0 && (
                <span className="bg-yellow-500 text-zinc-950 text-[10px] px-1.5 py-0.5 rounded-full ml-1 font-bold">
                  {pendingApprovals.length}
                </span>
              )}
            </button>
            <button 
              onClick={() => setActiveTab("reports")}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors duration-300 ${activeTab === "reports" ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <FileText className="inline-block h-4 w-4 mr-2" /> Reports
            </button>
            <button 
              onClick={() => setActiveTab("rag")}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors duration-300 ${activeTab === "rag" ? "border-primary text-primary bg-primary/5" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <Database className="inline-block h-4 w-4 mr-2" /> RAG Database Graph
            </button>
          </div>

          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div className="flex flex-col gap-6 animate-in fade-in duration-200">
              
              {/* Key Metrics Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm transition-all duration-300">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block">System Health</span>
                  <span className="text-xl font-bold text-green-500 flex items-center gap-1.5 mt-1">
                    <CheckCircle2 className="h-5 w-5" /> Online
                  </span>
                </div>
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm transition-all duration-300">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block">Active Incidents</span>
                  <span className="text-xl font-bold text-foreground block mt-1">
                    {incidents.filter(i => i.status !== "resolved").length}
                  </span>
                </div>
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm transition-all duration-300">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block">MTTD</span>
                  <span className="text-xl font-bold text-foreground flex items-center gap-1.5 mt-1">
                    <Clock className="h-4 w-4 text-blue-500" /> 14.5s
                  </span>
                </div>
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm transition-all duration-300">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block">MTTR</span>
                  <span className="text-xl font-bold text-foreground flex items-center gap-1.5 mt-1">
                    <Clock className="h-4 w-4 text-purple-500" /> 42.1s
                  </span>
                </div>
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm transition-all duration-300">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block">Self-Healing Rate</span>
                  <span className="text-xl font-bold text-primary flex items-center gap-1.5 mt-1">
                    <Zap className="h-4 w-4 text-yellow-500 fill-yellow-500" /> 92.5%
                  </span>
                </div>
              </div>

              {/* Google Datacenter Cluster Analytics Console */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 bg-card/30 border border-border rounded-xl p-6 transition-all duration-300">
                
                {/* Dial / Circular Meter (PUE Indicator) */}
                <div className="bg-card border border-border p-5 rounded-xl flex flex-col items-center justify-center text-center relative overflow-hidden shadow-sm transition-all duration-300 hover:shadow-md">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase mb-1">Google Datacenter PUE</span>
                  <div className="relative flex items-center justify-center my-3 h-28 w-28">
                    {/* Ring background */}
                    <svg className="w-full h-full transform -rotate-90">
                      <circle 
                        cx="56" cy="56" r="46" 
                        stroke="var(--border)" strokeWidth="8" fill="transparent" 
                      />
                      <circle 
                        cx="56" cy="56" r="46" 
                        stroke={((metrics["datacenter"]?.pue || 1.10) > 1.15) ? "#f97316" : "#22c55e"} 
                        strokeWidth="8" fill="transparent" 
                        strokeDasharray={2 * Math.PI * 46}
                        strokeDashoffset={2 * Math.PI * 46 * (1.0 - Math.min(1.0, (metrics["datacenter"]?.pue || 1.10) / 1.5))}
                        className="transition-all duration-1000 ease-out"
                      />
                    </svg>
                    <div className="absolute flex flex-col items-center justify-center">
                      <span className="text-2xl font-black text-foreground">
                        {(metrics["datacenter"]?.pue || 1.10).toFixed(3)}
                      </span>
                      <span className="text-[8px] font-mono text-muted-foreground uppercase tracking-widest">
                        {((metrics["datacenter"]?.pue || 1.10) > 1.15) ? "Overhead Warning" : "Optimal (Google Target)"}
                      </span>
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-2 leading-relaxed">
                    Power Usage Effectiveness (PUE) defines datacenter efficiency. Lower is better. Google target standard is ≤ 1.11.
                  </p>
                </div>

                {/* Power draw split and carbon footprint */}
                <div className="bg-card border border-border p-5 rounded-xl flex flex-col justify-between shadow-sm transition-all duration-300 hover:shadow-md">
                  <div>
                    <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block mb-3">Power Allocations & Carbon Footprint</span>
                    <div className="flex flex-col gap-3">
                      <div className="flex justify-between items-center border-b border-border pb-1.5 text-xs">
                        <span className="text-muted-foreground">IT Equipment Power:</span>
                        <span className="font-mono font-bold text-foreground">
                          {(metrics["datacenter"]?.it_power_kw || 120.0).toFixed(1)} kW
                        </span>
                      </div>
                      <div className="flex justify-between items-center border-b border-border pb-1.5 text-xs">
                        <span className="text-muted-foreground">Cooling System Load:</span>
                        <span className="font-mono font-bold text-orange-500">
                          {(metrics["datacenter"]?.cooling_power_kw || 12.0).toFixed(1)} kW
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground">Est. Carbon Equivalent:</span>
                        <span className="font-mono font-bold text-primary flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          {((metrics["datacenter"]?.it_power_kw || 120.0) * 0.42).toFixed(2)} kg/hr
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-4 p-2.5 bg-background/50 border border-border rounded-lg text-[10px] text-muted-foreground leading-relaxed">
                    <strong>Cluster Workload Cycle:</strong> Currently experiencing diurnal fluctuation at <span className="text-primary font-bold">{(metrics["datacenter"]?.diurnal_factor || 1.0).toFixed(2)}x</span> baseline draw.
                  </div>
                </div>

                {/* Animated cooling fan system */}
                <div className="bg-card border border-border p-5 rounded-xl flex flex-col items-center justify-between text-center shadow-sm relative overflow-hidden transition-all duration-300 hover:shadow-md group">
                  <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase block self-start">Smart Temperature Cooling Fan</span>
                  
                  <div className="my-4 relative flex items-center justify-center">
                    {/* Glowing outer boundary */}
                    <div className={`absolute h-24 w-24 rounded-full border border-dashed animate-spin transition-colors duration-1000 ${((metrics["datacenter"]?.temperature || 45.0) > 80.0) ? "border-orange-500/40" : "border-primary/20"}`} style={{ animationDuration: "12s" }}></div>
                    
                    {/* SVG Fan Blade */}
                    <svg 
                      className={`h-16 w-16 text-muted-foreground transition-all duration-300 ${((metrics["datacenter"]?.temperature || 45.0) > 80.0) ? "text-orange-500 fill-orange-500 animate-spin" : "text-primary fill-primary animate-spin"}`}
                      style={{ 
                        animationDuration: `${Math.max(0.2, 5.0 - ((metrics["datacenter"]?.temperature || 45.0) - 30.0) * 0.1)}s`
                      }}
                      viewBox="0 0 24 24"
                    >
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-2c.55 0 1-.45 1-1V5c0-.55-.45-1-1-1s-1 .45-1 1v2c0 .55.45 1 1 1zm0 8c-.55 0-1 .45-1 1v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1zm-4-4c0-.55-.45-1-1-1H5c-.55 0-1 .45-1 1s.45 1 1 1h2c.55 0 1-.45 1-1zm8 0c0-.55-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1h2c.55 0 1-.45 1-1z" />
                    </svg>
                  </div>

                  <div className="w-full flex items-center justify-between border-t border-border pt-3 text-[10px]">
                    <span className="text-muted-foreground">Regulator Mode:</span>
                    <span className={`font-mono font-bold uppercase ${((metrics["datacenter"]?.temperature || 45.0) > 80.0) ? "text-orange-500 animate-pulse" : "text-primary"}`}>
                      {((metrics["datacenter"]?.temperature || 45.0) > 80.0) ? "Emergency Cooling" : "Active Eco-Cooling"}
                    </span>
                  </div>
                </div>

              </div>

              {/* Service Cards list */}
              <div className="bg-card/40 border border-border rounded-xl p-6 transition-all duration-300 animate-fade-in-up">
                <h3 className="text-sm font-semibold mb-4 text-foreground">Microservice Status Overview</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {services.map(service => (
                    <div key={service.id} className="bg-card border border-border p-4 rounded-xl flex flex-col justify-between min-h-36 hover:border-primary/50 transition-all duration-300 shadow-sm">
                      <div className="flex flex-col gap-1.5">
                        <div className="flex items-start justify-between gap-1.5">
                          <span className="font-bold text-xs text-foreground leading-tight">{service.name}</span>
                          <span className={`px-2 py-0.5 rounded text-[8px] font-extrabold tracking-wider uppercase whitespace-nowrap ${getStatusBadgeClass(service.status)}`}>
                            {service.status}
                          </span>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-y-2.5 gap-x-4 border-t border-border pt-3 mt-3">
                        <div className="text-left">
                          <span className="text-[8px] font-semibold text-zinc-500 uppercase block tracking-wider">CPU</span>
                          <span className="text-xs font-mono font-bold text-zinc-350">
                            {metrics[service.id]?.cpu_usage?.toFixed(1) || "12.4"}%
                          </span>
                        </div>
                        <div className="text-left">
                          <span className="text-[8px] font-semibold text-zinc-500 uppercase block tracking-wider">RAM</span>
                          <span className="text-xs font-mono font-bold text-zinc-350">
                            {metrics[service.id]?.memory_usage?.toFixed(1) || "35.2"}%
                          </span>
                        </div>
                        <div className="text-left">
                          <span className="text-[8px] font-semibold text-zinc-500 uppercase block tracking-wider">Errors</span>
                          <span className={`text-xs font-mono font-bold ${(metrics[service.id]?.error_rate || 0) > 0 ? "text-red-400" : "text-zinc-350"}`}>
                            {metrics[service.id]?.error_rate?.toFixed(2) || "0.00"}%
                          </span>
                        </div>
                        <div className="text-left">
                          <span className="text-[8px] font-semibold text-zinc-500 uppercase block tracking-wider">Temp</span>
                          <span className={`text-xs font-mono font-bold ${(metrics[service.id]?.temperature || 0.0) > 75.0 ? "text-orange-400 font-extrabold animate-pulse" : "text-zinc-350"}`}>
                            {(metrics[service.id]?.temperature || 35.0).toFixed(1)}°C
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Charts Section */}
              {isMounted && historicalData.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-zinc-900/30 border border-zinc-800 rounded-xl p-6">
                  {/* CPU Chart */}
                  <div 
                    onClick={() => setFocusedMetric("cpu")}
                    className="flex flex-col gap-2 cursor-pointer p-4 rounded-xl border border-zinc-805/40 hover:border-primary/45 bg-zinc-950/20 hover:bg-zinc-950/40 transition-all duration-300 group"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-semibold text-zinc-300">CPU Utilization Trend (%)</span>
                      <span className="text-[9px] text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300 font-mono">Deep-Dive &rarr;</span>
                    </div>
                    <div className="h-64 w-full bg-zinc-950/45 p-2 rounded-lg border border-zinc-900">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historicalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a/30" />
                          <XAxis dataKey="time" tick={{ fill: '#71717a', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717a', fontSize: 10 }} domain={[0, 100]} />
                          <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }} labelClassName="text-xs text-zinc-400" />
                          {services.map((service, index) => {
                            const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#ef4444", "#06b6d4", "#a855f7", "#eab308"];
                            return (
                              <Line 
                                key={service.id} 
                                type="monotone" 
                                dataKey={`${service.id.replace(/-/g, "_")}_cpu`} 
                                name={service.name} 
                                stroke={colors[index % colors.length]} 
                                strokeWidth={1.5} 
                                dot={false} 
                                isAnimationActive={false} 
                              />
                            );
                          })}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  
                  {/* Memory Chart */}
                  <div 
                    onClick={() => setFocusedMetric("memory")}
                    className="flex flex-col gap-2 cursor-pointer p-4 rounded-xl border border-zinc-805/40 hover:border-primary/45 bg-zinc-950/20 hover:bg-zinc-950/40 transition-all duration-300 group"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-semibold text-zinc-300">Memory Utilization Trend (%)</span>
                      <span className="text-[9px] text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300 font-mono">Deep-Dive &rarr;</span>
                    </div>
                    <div className="h-64 w-full bg-zinc-950/45 p-2 rounded-lg border border-zinc-900">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historicalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a/30" />
                          <XAxis dataKey="time" tick={{ fill: '#71717a', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717a', fontSize: 10 }} domain={[0, 100]} />
                          <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }} labelClassName="text-xs text-zinc-400" />
                          {services.map((service, index) => {
                            const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#ef4444", "#06b6d4", "#a855f7", "#eab308"];
                            return (
                              <Line 
                                key={service.id} 
                                type="monotone" 
                                dataKey={`${service.id.replace(/-/g, "_")}_mem`} 
                                name={service.name} 
                                stroke={colors[index % colors.length]} 
                                strokeWidth={1.5} 
                                dot={false} 
                                isAnimationActive={false} 
                              />
                            );
                          })}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Latency Chart */}
                  <div 
                    onClick={() => setFocusedMetric("latency")}
                    className="flex flex-col gap-2 cursor-pointer p-4 rounded-xl border border-zinc-805/40 hover:border-primary/45 bg-zinc-950/20 hover:bg-zinc-950/40 transition-all duration-300 group"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-semibold text-zinc-300">Response Latency Trend (ms)</span>
                      <span className="text-[9px] text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300 font-mono">Deep-Dive &rarr;</span>
                    </div>
                    <div className="h-64 w-full bg-zinc-950/45 p-2 rounded-lg border border-zinc-900">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historicalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a/30" />
                          <XAxis dataKey="time" tick={{ fill: '#71717a', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717a', fontSize: 10 }} />
                          <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }} labelClassName="text-xs text-zinc-400" />
                          {services.map((service, index) => {
                            const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#ef4444", "#06b6d4", "#a855f7", "#eab308"];
                            return (
                              <Line 
                                key={service.id} 
                                type="monotone" 
                                dataKey={`${service.id.replace(/-/g, "_")}_lat`} 
                                name={service.name} 
                                stroke={colors[index % colors.length]} 
                                strokeWidth={1.5} 
                                dot={false} 
                                isAnimationActive={false} 
                              />
                            );
                          })}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Errors Chart */}
                  <div 
                    onClick={() => setFocusedMetric("errors")}
                    className="flex flex-col gap-2 cursor-pointer p-4 rounded-xl border border-zinc-805/40 hover:border-primary/45 bg-zinc-950/20 hover:bg-zinc-950/40 transition-all duration-300 group"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-semibold text-zinc-300">Error Rate Trend (%)</span>
                      <span className="text-[9px] text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300 font-mono">Deep-Dive &rarr;</span>
                    </div>
                    <div className="h-64 w-full bg-zinc-950/45 p-2 rounded-lg border border-zinc-900">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historicalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a/30" />
                          <XAxis dataKey="time" tick={{ fill: '#71717a', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717a', fontSize: 10 }} domain={[0, 100]} />
                          <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a' }} labelClassName="text-xs text-zinc-400" />
                          {services.map((service, index) => {
                            const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#ef4444", "#06b6d4", "#a855f7", "#eab308"];
                            return (
                              <Line 
                                key={service.id} 
                                type="monotone" 
                                dataKey={`${service.id.replace(/-/g, "_")}_err`} 
                                name={service.name} 
                                stroke={colors[index % colors.length]} 
                                strokeWidth={1.5} 
                                dot={false} 
                                isAnimationActive={false} 
                              />
                            );
                          })}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 border border-dashed border-zinc-800 rounded-xl bg-zinc-900/10 text-zinc-500 text-xs">
                  <RefreshCw className="h-5 w-5 mb-2 animate-spin text-zinc-500" />
                  Waiting for live metrics stream to populate charts...
                </div>
              )}

              {/* Trigger Scenario Control Panel */}
              <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col gap-6">
                <div>
                  <h3 className="text-sm font-semibold mb-1 text-foreground flex items-center gap-1.5">
                    <Zap className="h-4 w-4 text-yellow-500" /> Infrastructure Failure Injector (Local Simulation)
                  </h3>
                  <p className="text-xs text-muted-foreground">Simulate standard infrastructure faults in the environment to trigger automated agent self-healing workflows.</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                    <button 
                      onClick={() => triggerScenario("1")}
                      className="flex flex-col text-left p-4 bg-background border border-border hover:border-primary/40 rounded-xl group transition-all card-glow-hover cursor-pointer"
                    >
                      <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors">1. DB Connection Exhaustion</span>
                      <span className="text-[10px] text-muted-foreground mt-1">Inject high query load to Database Service. Saturates pool limits and causes downstream timeout events.</span>
                    </button>
                    <button 
                      onClick={() => triggerScenario("2")}
                      className="flex flex-col text-left p-4 bg-background border border-border hover:border-primary/40 rounded-xl group transition-all card-glow-hover cursor-pointer"
                    >
                      <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors">2. Memory Leak</span>
                      <span className="text-[10px] text-muted-foreground mt-1">Slow heap memory leak in Payment Service. Spikes RAM allocations past 85% alerting threshold.</span>
                    </button>
                    <button 
                      onClick={() => triggerScenario("3")}
                      className="flex flex-col text-left p-4 bg-background border border-border hover:border-primary/40 rounded-xl group transition-all card-glow-hover cursor-pointer"
                    >
                      <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors">3. Cascading Failure</span>
                      <span className="text-[10px] text-muted-foreground mt-1">Simulate database service crash. Triggers correlated downstream warnings up to API Gateway.</span>
                    </button>
                  </div>
                </div>

                <div className="border-t border-border pt-4">
                  <h3 className="text-sm font-semibold mb-1 text-foreground flex items-center gap-1.5">
                    <Server className="h-4 w-4 text-primary" /> Real-world Datacenter Outages (2025/2026 Datasets)
                  </h3>
                  <p className="text-xs text-muted-foreground">Inject authentic operational outages from major cloud providers to test multi-agent RAG investigations and policy approvals.</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                    <button 
                      onClick={() => triggerScenario("4")}
                      className="flex flex-col text-left p-4 bg-background border border-border hover:border-blue-600/40 rounded-xl group transition-all card-glow-hover cursor-pointer"
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-semibold text-xs text-foreground group-hover:text-blue-500 transition-colors">4. Google Cloud (June 2025)</span>
                        <span className="text-[8px] bg-blue-500/10 text-blue-400 px-1 rounded">GCP API</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground mt-1">incorrect rollout caused infinite crash loop in ServiceControl component. Requires configuration rollback.</span>
                    </button>
                    <button 
                      onClick={() => triggerScenario("5")}
                      className="flex flex-col text-left p-4 bg-background border border-border hover:border-orange-500/40 rounded-xl group transition-all card-glow-hover cursor-pointer"
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-semibold text-xs text-foreground group-hover:text-orange-500 transition-colors">5. Cloudflare (Nov 2025)</span>
                        <span className="text-[8px] bg-orange-500/10 text-orange-400 px-1 rounded">CF routing</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground mt-1">Database permission update led to Bot Management config file size overrun. Edge routing software crashed.</span>
                    </button>
                    <button 
                      onClick={() => triggerScenario("6")}
                      className="flex flex-col text-left p-4 bg-background border border-border hover:border-amber-500/40 rounded-xl group transition-all card-glow-hover cursor-pointer"
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-semibold text-xs text-foreground group-hover:text-amber-500 transition-colors">6. AWS DynamoDB (Oct 2025)</span>
                        <span className="text-[8px] bg-amber-500/10 text-amber-400 px-1 rounded">AWS DNS</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground mt-1">DNS automated configuration corrupted DynamoDB DNS lookups in US-EAST-1. Requires cache flush.</span>
                    </button>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: SERVICE TOPOLOGY */}
          {activeTab === "topology" && (
            <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 flex flex-col items-center justify-center min-h-[400px] animate-in fade-in duration-200">
              <h3 className="text-sm font-semibold mb-6 self-start text-zinc-300">Service Dependency Topology</h3>
              
              {/* Interactive Topology Graph rendering */}
              <div className="relative w-full max-w-lg h-96 flex flex-col justify-between items-center py-4 border border-border rounded-2xl bg-card p-6 shadow-sm overflow-hidden">
                
                {/* SVG Connections Canvas overlay */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" xmlns="http://www.w3.org/2000/svg">
                  {/* Connection lines */}
                  {/* Gateway -> Auth */}
                  <line x1="50%" y1="15%" x2="20%" y2="50%" stroke={services[1]?.status === "critical" ? "#ef4444" : services[1]?.status === "warning" ? "#f59e0b" : "var(--border)"} strokeWidth="1.5" />
                  <line x1="50%" y1="15%" x2="20%" y2="50%" stroke="var(--primary)" strokeWidth="1.5" className="animate-pulse-dash opacity-60" />

                  {/* Gateway -> Order */}
                  <line x1="50%" y1="15%" x2="80%" y2="50%" stroke={services[2]?.status === "critical" ? "#ef4444" : services[2]?.status === "warning" ? "#f59e0b" : "var(--border)"} strokeWidth="1.5" />
                  <line x1="50%" y1="15%" x2="80%" y2="50%" stroke="var(--primary)" strokeWidth="1.5" className="animate-pulse-dash opacity-60" />

                  {/* Order -> Payment */}
                  <line x1="80%" y1="50%" x2="30%" y2="85%" stroke={services[3]?.status === "critical" ? "#ef4444" : services[3]?.status === "warning" ? "#f59e0b" : "var(--border)"} strokeWidth="1.5" />
                  <line x1="80%" y1="50%" x2="30%" y2="85%" stroke="var(--primary)" strokeWidth="1.5" className="animate-pulse-dash opacity-60" />

                  {/* Order -> Database */}
                  <line x1="80%" y1="50%" x2="70%" y2="85%" stroke={services[4]?.status === "critical" ? "#ef4444" : services[4]?.status === "warning" ? "#f59e0b" : "var(--border)"} strokeWidth="1.5" />
                  <line x1="80%" y1="50%" x2="70%" y2="85%" stroke="var(--primary)" strokeWidth="1.5" className="animate-pulse-dash opacity-60" />
                </svg>

                {/* Gateway (Level 1) */}
                <div className="flex flex-col items-center z-10">
                  <div className={`px-4 py-2.5 rounded-lg border font-mono text-xs flex items-center gap-2 bg-background card-glow-hover ${getStatusBadgeClass(services[0]?.status)}`}>
                    <Server className="h-3.5 w-3.5" /> API Gateway
                  </div>
                </div>

                {/* Level 2: Auth and Order */}
                <div className="flex justify-between w-full px-8 z-10">
                  <div className={`px-4 py-2.5 rounded-lg border font-mono text-xs flex items-center gap-2 bg-background card-glow-hover ${getStatusBadgeClass(services[1]?.status)}`}>
                    <Server className="h-3.5 w-3.5" /> Auth Service
                  </div>
                  <div className={`px-4 py-2.5 rounded-lg border font-mono text-xs flex items-center gap-2 bg-background card-glow-hover ${getStatusBadgeClass(services[2]?.status)}`}>
                    <Server className="h-3.5 w-3.5" /> Order Service
                  </div>
                </div>

                {/* Level 3: Payment and Database */}
                <div className="flex justify-around w-full max-w-sm px-4 z-10">
                  <div className={`px-4 py-2.5 rounded-lg border font-mono text-xs flex items-center gap-2 bg-background card-glow-hover ${getStatusBadgeClass(services[3]?.status)}`}>
                    <Server className="h-3.5 w-3.5" /> Payment Service
                  </div>
                  <div className={`px-4 py-2.5 rounded-lg border font-mono text-xs flex items-center gap-2 bg-background card-glow-hover ${getStatusBadgeClass(services[4]?.status)}`}>
                    <Database className="h-3.5 w-3.5" /> Database Service
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: INCIDENT COMMAND CENTER */}
          {activeTab === "incidents" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-200">
              
              {/* Incident List Column */}
              <div className="lg:col-span-1 border border-zinc-800 rounded-xl p-4 flex flex-col gap-3 max-h-[500px] overflow-y-auto">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Incidents log</h3>
                {incidents.length === 0 ? (
                  <div className="text-center py-10 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
                    No active incidents reported.
                  </div>
                ) : (
                  incidents.map(inc => (
                    <button
                      key={inc.id}
                      onClick={() => {
                        setSelectedIncident(inc);
                        fetchIncidentDetails(inc.id);
                      }}
                      className={`text-left p-3 rounded-lg border transition-all flex flex-col gap-1.5 ${selectedIncident?.id === inc.id ? "bg-blue-950/20 border-blue-800/80" : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"}`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-mono text-zinc-500">{inc.id}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${inc.severity === "CRITICAL" ? "bg-red-950 text-red-400 border border-red-800/60" : "bg-yellow-950 text-yellow-400 border border-yellow-800/60"}`}>
                          {inc.severity}
                        </span>
                      </div>
                      <span className="font-semibold text-xs text-zinc-200 block line-clamp-1">{inc.title}</span>
                      <div className="flex justify-between items-center text-[10px] text-zinc-500 mt-1">
                        <span>Target: {inc.service_id}</span>
                        <span className="capitalize text-blue-400 font-mono font-semibold">{inc.status}</span>
                      </div>
                    </button>
                  ))
                )}
              </div>

              {/* Incident Investigation View */}
              <div className="lg:col-span-2 border border-zinc-800 rounded-xl p-6 flex flex-col gap-6">
                {!selectedIncident ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 text-xs py-20">
                    <AlertTriangle className="h-8 w-8 mb-2 opacity-30 text-zinc-400" />
                    Select an incident to view Agent Investigation & root cause hypotheses.
                  </div>
                ) : (
                  <>
                    <div className="border-b border-zinc-850 pb-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="text-xs font-mono text-zinc-500 block">{selectedIncident.id}</span>
                          <h2 className="text-lg font-bold text-zinc-200">{selectedIncident.title}</h2>
                        </div>
                        <span className="px-2.5 py-1 rounded text-xs font-bold bg-red-950 text-red-400 border border-red-800">
                          {selectedIncident.severity}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400">{selectedIncident.description}</p>
                    </div>

                    {/* AI Agent Analysis section */}
                    <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-4 flex flex-col gap-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-blue-400 flex items-center gap-1.5">
                          <Sparkles className="h-4 w-4" /> AI Investigation Hypotheses
                        </span>
                        <span className="text-[10px] font-mono text-zinc-500">Confidence Model: Z-Score</span>
                      </div>
                      
                      {/* Dynamic simulation / real hypothesis */}
                      <div className="flex flex-col gap-3">
                        <div className="p-3 bg-zinc-950/80 border border-zinc-800 rounded-lg">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-semibold text-xs text-zinc-200">
                              {selectedIncident.root_cause || "database_service Connection Pool Exhaustion"}
                            </span>
                            <span className="text-xs font-bold text-emerald-400 font-mono">
                              Confidence: {selectedIncident.confidence?.toFixed(2) || "0.91"}
                            </span>
                          </div>
                          <ul className="text-[10px] text-zinc-400 flex flex-col gap-1 list-disc pl-4">
                            <li>database_service active_connections reached maximum pool size (20/20)</li>
                            <li>database errors occurred first, downstream order_service query latency rose to 4.2s</li>
                            <li>trace_id correlation shows blocked thread execution waiting on database response</li>
                          </ul>
                        </div>
                      </div>
                    </div>

                    {/* Timeline Feed for Incident */}
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">Investigation Timeline</h4>
                      <div className="flex flex-col gap-3 pl-3 border-l border-zinc-850 relative">
                        {selectedIncidentEvents.length === 0 ? (
                          <div className="text-[10px] text-zinc-500">No events logged yet. Triggering investigation...</div>
                        ) : (
                          selectedIncidentEvents.map(evt => (
                            <div key={evt.id} className="relative text-xs">
                              <span className="absolute -left-[16px] top-1.5 h-1.5 w-1.5 rounded-full bg-blue-500"></span>
                              <span className="font-mono text-zinc-500 mr-2">
                                {new Date(evt.timestamp).toLocaleTimeString()}
                              </span>
                              <span className="font-bold text-zinc-300 mr-1.5">[{evt.sender}]</span>
                              <span className="text-zinc-400">{evt.message}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: APPROVALS */}
          {activeTab === "approvals" && (
            <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 animate-in fade-in duration-200">
              <h3 className="text-sm font-semibold mb-4 text-zinc-300">Remediation Approval Center</h3>
              {pendingApprovals.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
                  No actions require approval at this time. All system policies are within parameters.
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  {pendingApprovals.map(plan => (
                    <div key={plan.id} className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-950 text-yellow-400 border border-yellow-800">
                            Risk: {plan.risk}
                          </span>
                          <span className="text-xs text-zinc-500 font-mono">Plan #{plan.id}</span>
                        </div>
                        <h4 className="font-semibold text-sm text-zinc-200">
                          Runbook: <span className="font-mono text-blue-400">{plan.runbook}</span>
                        </h4>
                        <p className="text-xs text-zinc-400 mt-1">Target Service: {plan.target} | Reason: {plan.reason}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleReject(plan.id)}
                          className="px-3 py-1.5 rounded-lg border border-zinc-800 hover:border-red-900 bg-zinc-950 text-xs font-semibold text-zinc-400 hover:text-red-400 transition-all flex items-center gap-1.5"
                        >
                          <X className="h-3.5 w-3.5" /> Reject
                        </button>
                        <button
                          onClick={() => handleApprove(plan.id)}
                          className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-zinc-950 bg-blue-400 hover:bg-blue-300 text-xs font-bold transition-all flex items-center gap-1.5"
                        >
                          <Check className="h-3.5 w-3.5" /> Approve Action
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: REPORTS */}
          {activeTab === "reports" && (
            <div className="flex flex-col lg:flex-row gap-6 animate-in fade-in duration-200">
              {/* Left Column: Post-Mortems */}
              <div className="flex-1 bg-zinc-900/30 border border-zinc-800 rounded-xl p-6">
                <h3 className="text-sm font-bold mb-4 text-zinc-300 flex items-center gap-1.5">
                  <FileText className="h-4.5 w-4.5 text-blue-400" /> SRE Post-Mortem Reports
                </h3>
                {completedReports.length === 0 ? (
                  <div className="text-center py-20 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
                    No post-mortem reports are available yet. Complete an incident to generate reports.
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    {completedReports.map(rep => (
                      <div key={rep.id} className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-zinc-700 transition-colors">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-[10px] font-mono text-zinc-500">Incident #{rep.incident_id}</span>
                          <span className="text-[10px] text-zinc-500">{new Date(rep.created_at).toLocaleDateString()}</span>
                        </div>
                        <h4 className="font-semibold text-sm text-zinc-200 mb-1">Root Cause: {rep.root_cause}</h4>
                        <p className="text-xs text-zinc-400 line-clamp-2 mb-3">Telemetry findings: {rep.evidence}</p>
                        <button 
                          onClick={() => setSelectedReport(rep)}
                          className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center gap-1 cursor-pointer"
                        >
                          <FileText className="h-3.5 w-3.5" /> View Full Report
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Column: Hardware Maintenance Ledger */}
              <div className="w-full lg:w-96 bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 flex flex-col gap-4">
                <h3 className="text-sm font-bold text-zinc-300 flex items-center gap-1.5">
                  <Cpu className="h-4.5 w-4.5 text-orange-400" /> Hardware Maintenance Ledger
                </h3>
                <p className="text-[10px] text-zinc-500 font-sans leading-relaxed">
                  Historical hardware swap, repair, and diagnostic logs parsed from <code className="font-mono text-zinc-400">hardware_management_report.md</code>.
                </p>

                {/* Hardware Graph Section */}
                {isMounted && hardwareLogs.length > 0 && (
                  <div className="bg-zinc-950/45 border border-zinc-900 p-3 rounded-lg flex flex-col gap-2 shadow-sm mb-1">
                    <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider block">Maintenance Events by Node</span>
                    <div className="h-32 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getHardwareNodeChartData()} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a/20" vertical={false} />
                          <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 8 }} tickLine={false} axisLine={false} />
                          <YAxis tick={{ fill: '#71717a', fontSize: 8 }} tickLine={false} axisLine={false} allowDecimals={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#121214', border: '1px solid var(--border)', borderRadius: '6px' }} 
                            labelClassName="text-[9px] text-zinc-400 font-mono"
                            itemStyle={{ fontSize: '9px' }}
                          />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                            {getHardwareNodeChartData().map((entry, idx) => (
                              <Cell key={`cell-${idx}`} fill={getNodeColor(entry.name)} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                <div className="flex flex-col gap-3 overflow-y-auto max-h-[340px] pr-1">
                  {hardwareLogs.length === 0 ? (
                    <div className="text-center py-20 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
                      No hardware logs available.
                    </div>
                  ) : (
                    hardwareLogs.map((log, idx) => (
                      <div key={idx} className="p-3 bg-zinc-900 border border-zinc-850 rounded-lg flex flex-col gap-1.5 hover:border-zinc-700 transition-colors">
                        <div className="flex justify-between items-center">
                          <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-zinc-950 text-zinc-400 border border-zinc-800">
                            {log.service_id}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded text-[8px] font-extrabold ${log.status === "PASS" ? "bg-green-950/40 text-green-400 border border-green-800/40" : "bg-red-950/40 text-red-400 border border-red-800/40"}`}>
                            {log.status}
                          </span>
                        </div>
                        <h4 className="font-bold text-xs text-zinc-200">
                          {log.component} &bull; <span className={log.action === "Replaced" ? "text-orange-400" : log.action === "Repaired" ? "text-green-400" : "text-blue-400"}>{log.action}</span>
                        </h4>
                        <p className="text-[10px] text-zinc-400 leading-normal">{log.description}</p>
                        <div className="flex justify-between items-center text-[8px] text-zinc-500 font-mono border-t border-zinc-850/60 pt-1.5 mt-1">
                          <span>Operator: {log.operator}</span>
                          <span>{log.timestamp ? new Date(log.timestamp).toLocaleDateString() : ""}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: RAG DATABASE GRAPH */}
          {activeTab === "rag" && (
            <div className="flex flex-col gap-6 animate-in fade-in duration-200">
              
              {/* Analytics Header */}
              <div className="flex flex-col gap-1">
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Database className="h-4.5 w-4.5 text-primary" /> RAG Incident Knowledge Base & Analytics
                </h3>
                <p className="text-xs text-muted-foreground">Historical incident distributions, mean resolution velocity metrics, and seeded reference shapes used for vector search matching.</p>
              </div>

              {/* Chart Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Chart 1: Failure Distribution per service */}
                <div className="bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col gap-4">
                  <h4 className="font-bold text-xs text-foreground uppercase tracking-wider">
                    Incident Distribution by Microservice
                  </h4>
                  <div className="h-64 w-full bg-background/50 p-2 rounded-lg border border-border">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={RAG_SERVICE_FREQUENCY_DATA} margin={{ top: 10, right: 10, left: -25, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} vertical={false} />
                        <XAxis dataKey="name" tick={{ fill: theme === 'dark' ? '#71717a' : '#64748b', fontSize: 9 }} />
                        <YAxis tick={{ fill: theme === 'dark' ? '#71717a' : '#64748b', fontSize: 9 }} allowDecimals={false} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: theme === 'dark' ? '#121214' : '#ffffff', border: '1px solid var(--border)', borderRadius: '6px' }}
                          labelClassName="text-xs font-semibold text-muted-foreground"
                        />
                        <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={40}>
                          {RAG_SERVICE_FREQUENCY_DATA.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Chart 2: Resolution Speed (MTTR) */}
                <div className="bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col gap-4">
                  <h4 className="font-bold text-xs text-foreground uppercase tracking-wider">
                    Mean Time to Resolution (MTTR) by Incident (Seconds)
                  </h4>
                  <div className="h-64 w-full bg-background/50 p-2 rounded-lg border border-border">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={RAG_RESOLUTION_MTTR_DATA} margin={{ top: 10, right: 10, left: -25, bottom: 5 }}>
                        <defs>
                          <linearGradient id="colorMttr" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
                        <XAxis dataKey="label" tick={{ fill: theme === 'dark' ? '#71717a' : '#64748b', fontSize: 9 }} />
                        <YAxis tick={{ fill: theme === 'dark' ? '#71717a' : '#64748b', fontSize: 9 }} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: theme === 'dark' ? '#121214' : '#ffffff', border: '1px solid var(--border)', borderRadius: '6px' }}
                          labelClassName="text-xs font-semibold text-muted-foreground"
                        />
                        <Area type="monotone" dataKey="mttr" stroke="var(--primary)" strokeWidth={2} fillOpacity={1} fill="url(#colorMttr)" name="Resolution Speed (s)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </div>

              {/* Table listing the 10 incidents */}
              <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
                <h4 className="font-bold text-xs text-foreground uppercase tracking-wider mb-4">
                  Incident RAG Vector Store Records
                </h4>
                <div className="overflow-x-auto border border-border rounded-lg">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-muted/80 border-b border-border font-semibold text-muted-foreground">
                        <th className="p-3">ID</th>
                        <th className="p-3">Service</th>
                        <th className="p-3">Root Cause</th>
                        <th className="p-3">Symptom Summary</th>
                        <th className="p-3">Runbook Trigger</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {HISTORICAL_INCIDENTS.map((inc) => (
                        <tr key={inc.id} className="hover:bg-muted/30 transition-colors">
                          <td className="p-3 font-mono font-bold text-primary">{inc.id}</td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded-full bg-card border border-border font-semibold text-[10px]">
                              {inc.service}
                            </span>
                          </td>
                          <td className="p-3 font-medium text-foreground">{inc.root_cause}</td>
                          <td className="p-3 text-muted-foreground max-w-xs truncate" title={inc.symptoms}>
                            {inc.symptoms}
                          </td>
                          <td className="p-3">
                            <span className="font-mono text-[10px] text-blue-500 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/25">
                              {inc.runbook}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

              {/* Report Detail Modal Overlay */}
              {selectedReport && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                  <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl">
                    <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block">Incident Post-Mortem</span>
                        <h3 className="text-base font-bold text-zinc-200 mt-1">{selectedReport.root_cause}</h3>
                      </div>
                      <button 
                        onClick={() => setSelectedReport(null)}
                        className="text-zinc-500 hover:text-zinc-350 p-1.5 rounded-lg border border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    
                    <div className="p-6 overflow-y-auto text-xs flex flex-col gap-4 font-sans text-zinc-300">
                      <div>
                        <h4 className="font-bold text-zinc-400 mb-1 text-[10px] uppercase tracking-wider">Incident Overview</h4>
                        <div className="bg-zinc-950/40 p-3 rounded-lg border border-zinc-850 text-zinc-300 flex flex-col gap-1">
                          <p><strong>Incident ID:</strong> {selectedReport.incident_id}</p>
                          <p><strong>Timeline Created:</strong> {new Date(selectedReport.created_at).toLocaleString()}</p>
                          <p><strong>Mean Time to Detect (MTTD):</strong> {selectedReport.mttd}s</p>
                          <p><strong>Mean Time to Resolve (MTTR):</strong> {selectedReport.mttr.toFixed(1)}s</p>
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-bold text-zinc-400 mb-1 text-[10px] uppercase tracking-wider">Telemetry Evidence</h4>
                        <p className="bg-zinc-950/40 p-3 rounded-lg border border-zinc-850 font-mono text-[10px] text-zinc-400">
                          {selectedReport.evidence}
                        </p>
                      </div>

                      <div>
                        <h4 className="font-bold text-zinc-400 mb-2 text-[10px] uppercase tracking-wider">Remediation Steps Executed</h4>
                        <div className="flex flex-col gap-2">
                          {selectedReport.actions_executed.map((act, idx) => (
                            <div key={idx} className="p-3 bg-zinc-950/40 border border-zinc-850 rounded-lg flex justify-between items-center">
                              <span>Runbook: <span className="font-mono text-blue-400 font-semibold">{act.runbook}</span> on target <span className="font-mono text-zinc-400">{act.target}</span></span>
                              <span className="px-2 py-0.5 rounded text-[8px] bg-green-950/40 text-green-400 border border-green-800/40 font-bold uppercase">{act.status}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h4 className="font-bold text-zinc-400 mb-1 text-[10px] uppercase tracking-wider">Preventive Recommendations</h4>
                        <p className="bg-zinc-950/40 p-3 rounded-lg border border-zinc-850 text-zinc-400 leading-relaxed">
                          {selectedReport.preventive_recommendations}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
        
        {/* Right Sidebar: Real-time Event Feed */}
        <aside className="w-80 border border-zinc-900 bg-zinc-950/40 rounded-xl p-4 flex flex-col gap-4 max-h-[calc(100vh-8rem)] sticky top-24 overflow-y-auto">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Terminal className="h-4 w-4 text-zinc-500" /> Agent Activity Feed
            </span>
            <span className="text-[9px] font-mono text-zinc-500 uppercase">Live</span>
          </div>

          <div className="flex flex-col gap-3 overflow-y-auto pr-1">
            {feedEvents.length === 0 ? (
              <div className="text-center py-20 text-zinc-600 text-xs">
                Waiting for system events...
              </div>
            ) : (
              feedEvents.map((evt, idx) => (
                <div key={idx} className="text-xs font-mono border-b border-zinc-900/50 pb-2">
                  <div className="flex justify-between items-center text-[10px] text-zinc-500 mb-1">
                    <span>{evt.time}</span>
                    <span className={`px-1 rounded text-[8px] font-bold ${evt.type === "error" ? "bg-red-950/40 text-red-400" : evt.type === "warn" ? "bg-yellow-950/40 text-yellow-400" : "bg-blue-950/40 text-blue-400"}`}>
                      {evt.sender}
                    </span>
                  </div>
                  <p className="text-zinc-400 leading-normal">{evt.msg}</p>
                </div>
              ))
            )}
          </div>
        </aside>

      </div>
    </div>
  );
}
