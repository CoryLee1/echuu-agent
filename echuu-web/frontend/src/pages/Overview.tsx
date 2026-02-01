import { useEffect, useState } from "react";
import { Activity, PlayCircle, Radio, FileText, Loader2 } from "lucide-react";
import { fetchHistory, fetchStatus } from "../api/echuuApi";
import { useCharacters } from "../hooks/useCharacters";
import type { LiveSession, LiveStatus } from "../types";
import { Card, CardContent } from "../components/ui/card";

const StatCard = ({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
}) => (
  <Card>
    <CardContent className="p-6">
    <div className="flex items-center justify-between">
      <div>
        <div className="text-xs uppercase tracking-widest text-slate-400 font-bold">{label}</div>
        <div className="text-2xl font-bold text-slate-800 mt-2">{value}</div>
      </div>
      <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
        {icon}
      </div>
    </div>
    </CardContent>
  </Card>
);

const Overview = () => {
  const { characters, loading: charactersLoading } = useCharacters();
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [history, setHistory] = useState<LiveSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchStatus().then(setStatus).catch(() => setStatus(null)),
      fetchHistory().then(setHistory).catch(() => setHistory([]))
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Overview</h1>
        <p className="text-slate-500 text-sm mt-1">
          ECHUU Agent 管理后台总览：角色、直播、推理监控与历史归档。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatCard 
          label="Live Status" 
          value={loading ? "..." : (status?.is_running ? "Running" : "Idle")} 
          icon={<Radio size={20} />} 
        />
        <StatCard 
          label="Active Session" 
          value={status?.session_id || "—"} 
          icon={<Activity size={20} />} 
        />
        <StatCard 
          label="Total Sessions" 
          value={loading ? "..." : history.length} 
          icon={<FileText size={20} />} 
        />
        <StatCard 
          label="Characters" 
          value={charactersLoading ? "..." : characters.length} 
          icon={<PlayCircle size={20} />} 
        />
      </div>

      <Card>
        <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-800">Latest Sessions</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {history.slice(0, 5).map((item) => (
            <div key={item.session_id} className="py-3 flex items-center justify-between">
              <div>
                <div className="font-semibold text-slate-700">{item.topic}</div>
                <div className="text-xs text-slate-400">{item.name} · {item.timestamp}</div>
              </div>
              <span className="text-xs font-semibold text-slate-500">{item.session_id}</span>
            </div>
          ))}
          {history.length === 0 && (
            <div className="py-6 text-sm text-slate-400">暂无历史记录。</div>
          )}
        </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Overview;
