import { useEffect, useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import { downloadSessionUrl, fetchHistory } from "../api/echuuApi";
import type { LiveSession } from "../types";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";

const History = () => {
  const [sessions, setSessions] = useState<LiveSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchHistory()
      .then(setSessions)
      .catch((err) => {
        console.error("加载历史记录失败:", err);
        setSessions([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">History</h1>
        <p className="text-sm text-slate-500 mt-1">查看历史直播与下载档案。</p>
      </div>

      <Card>
        <CardContent className="grid grid-cols-1 gap-4">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <Loader2 size={20} className="animate-spin mr-2" />
              加载中...
            </div>
          ) : (
            <>
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className="flex items-center justify-between border border-slate-100 rounded-xl p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600">
                      <FileText size={18} />
                    </div>
                    <div>
                      <div className="font-semibold text-slate-800">{session.topic}</div>
                      <div className="text-xs text-slate-400 mt-1">
                        {session.name} · {session.timestamp || session.session_id}
                        {session.status && (
                          <span className={`ml-2 px-2 py-0.5 rounded ${
                            session.status === "completed" ? "bg-green-100 text-green-700" :
                            session.status === "running" ? "bg-blue-100 text-blue-700" :
                            session.status === "failed" ? "bg-red-100 text-red-700" :
                            "bg-slate-100 text-slate-600"
                          }`}>
                            {session.status === "completed" ? "已完成" :
                             session.status === "running" ? "进行中" :
                             session.status === "failed" ? "失败" : "待处理"}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    className="gap-2"
                    onClick={() => {
                      window.location.href = downloadSessionUrl(session.session_id);
                    }}
                  >
                    <Download size={14} /> 下载
                  </Button>
                </div>
              ))}
              {sessions.length === 0 && (
                <div className="text-slate-300 text-sm text-center py-8">暂无历史记录。</div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default History;
