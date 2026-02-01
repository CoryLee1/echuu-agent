import { useEffect, useRef, useState } from "react";
import { Activity, Brain, MessageSquare, Volume2, VolumeX, Play, Download } from "lucide-react";
import { audioUrl, downloadSessionUrl, sendDanmaku, startLive } from "../api/echuuApi";
import type { MemorySnapshot } from "../types";
import { useCharacters } from "../hooks/useCharacters";

type StepPayload = {
  speech: string;
  stage: string;
  step: number;
  danmaku?: string;
  audio_url?: string;
  memory_snapshot?: MemorySnapshot;
  inner_monologue?: string;
  emotion_break?: { level: number };
};

const LiveMonitor = () => {
  const { characters, loading: charactersLoading } = useCharacters();
  const [selectedCharId, setSelectedCharId] = useState("");
  const [topic, setTopic] = useState("关于上司的超劲爆八卦");
  const [status, setStatus] = useState<"idle" | "running">("idle");
  
  // 当角色加载完成后，设置默认选中第一个角色
  useEffect(() => {
    if (!charactersLoading && characters.length > 0 && !selectedCharId) {
      setSelectedCharId(characters[0].id);
    }
  }, [characters, charactersLoading, selectedCharId]);
  const [reasoning, setReasoning] = useState<string[]>([]);
  const [steps, setSteps] = useState<StepPayload[]>([]);
  const [memory, setMemory] = useState<MemorySnapshot>({
    story_points: [],
    promises: [],
    emotion_trend: [],
  });
  const [danmakuInput, setDanmakuInput] = useState("");
  const [autoPlay, setAutoPlay] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const reasoningRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);

  useEffect(() => {
    audioRef.current = new Audio();
  }, []);

  const playNext = () => {
    const next = audioQueueRef.current.shift();
    if (!next || !audioRef.current) {
      isPlayingRef.current = false;
      return;
    }
    isPlayingRef.current = true;
    audioRef.current.src = audioUrl(next);
    audioRef.current.play().catch(() => {
      isPlayingRef.current = false;
    });
  };

  const enqueueAudio = (url?: string) => {
    if (!url) return;
    audioQueueRef.current.push(url);
    if (!isPlayingRef.current) {
      playNext();
    }
  };

  useEffect(() => {
    if (!audioRef.current) return;
    const audio = audioRef.current;
    audio.onended = () => playNext();
    audio.onerror = () => playNext();
    return () => {
      audio.onended = null;
      audio.onerror = null;
    };
  }, []);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "reasoning") {
        setReasoning((prev) => [...prev, msg.content]);
      }
      if (msg.type === "step") {
        const data = msg.data as StepPayload;
        setSteps((prev) => [...prev, data]);
        if (data.memory_snapshot) {
          setMemory(data.memory_snapshot);
        }
        if (autoPlay && data.audio_url) {
          enqueueAudio(data.audio_url);
        }
      }
      if (msg.type === "finish") {
        setStatus("idle");
        setSessionId(msg.session_id);
      }
    };
    return () => ws.close();
  }, [autoPlay]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps]);

  useEffect(() => {
    if (reasoningRef.current) {
      reasoningRef.current.scrollTop = reasoningRef.current.scrollHeight;
    }
  }, [reasoning]);

  const handleStart = async () => {
    const char = characters.find((c) => c.id === selectedCharId);
    if (!char) return;
    setStatus("running");
    setReasoning([]);
    setSteps([]);
    setSessionId(null);
    setMemory({ story_points: [], promises: [], emotion_trend: [] });
    const defaultVoice = char.voice_configs?.find((v) => v.is_default) || char.voice_configs?.[0];
    
    await startLive({
      topic,
      character_id: char.id,
      voice_config_id: defaultVoice?.id,
      max_steps: 15,
    });
  };

  const handleSend = async () => {
    if (!danmakuInput.trim()) return;
    await sendDanmaku(danmakuInput, "管理台");
    setDanmakuInput("");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Live Monitor</h1>
        <p className="text-sm text-slate-500 mt-1">启动直播、查看推理过程和实时台词。</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <section className="xl:col-span-4 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase">角色选择</div>
            {charactersLoading ? (
              <div className="mt-2 text-sm text-slate-400">加载中...</div>
            ) : characters.length === 0 ? (
              <div className="mt-2 text-sm text-slate-400">
                暂无角色，请先<a href="/characters" className="text-indigo-600 hover:underline">创建角色</a>
              </div>
            ) : (
              <select
                value={selectedCharId}
                onChange={(e) => setSelectedCharId(e.target.value)}
                className="w-full mt-2 bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm"
              >
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase">直播主题</div>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full mt-2 bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm h-28 resize-none"
            />
          </div>
          <div className="flex items-center justify-between">
            <button
              onClick={() => setAutoPlay(!autoPlay)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${
                autoPlay ? "bg-indigo-50 text-indigo-600 border-indigo-200" : "bg-slate-100 text-slate-400 border-slate-200"
              }`}
            >
              {autoPlay ? <Volume2 size={16} /> : <VolumeX size={16} />}
              自动播报
            </button>
            <button
              onClick={handleStart}
              disabled={status === "running" || !selectedCharId || charactersLoading}
              className="px-5 py-3 rounded-xl bg-indigo-600 text-white font-semibold flex items-center gap-2 disabled:opacity-50"
            >
              {status === "running" ? <Activity size={16} className="animate-spin" /> : <Play size={16} />}
              {status === "running" ? "进行中" : "启动直播"}
            </button>
          </div>
          {sessionId && (
            <a
              href={downloadSessionUrl(sessionId)}
              className="w-full flex items-center justify-center gap-2 bg-slate-900 text-white py-3 rounded-xl text-sm font-semibold"
            >
              <Download size={16} /> 下载本次 Session
            </a>
          )}
        </section>

        <section className="xl:col-span-8 grid grid-cols-1 gap-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm h-[250px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-slate-700 font-semibold">
                <Brain size={18} className="text-indigo-500" />
                推理过程
              </div>
              <div className="flex items-end gap-1">
                {memory.emotion_trend.map((level, idx) => (
                  <div
                    key={idx}
                    className="w-1.5 bg-rose-400 rounded-full"
                    style={{ height: `${level * 4 + 4}px` }}
                  />
                ))}
              </div>
            </div>
            <div ref={reasoningRef} className="flex-1 overflow-y-auto text-xs font-mono text-slate-600 space-y-1">
              {reasoning.map((line, idx) => (
                <div key={idx} className="border-l-2 border-slate-100 pl-3 py-1">
                  {line}
                </div>
              ))}
              {reasoning.length === 0 && <div className="text-slate-300">等待创作...</div>}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm h-[430px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-slate-700 font-semibold">
                <MessageSquare size={18} className="text-indigo-500" />
                实时台词
              </div>
              <span className="text-xs text-slate-400">{steps.length} lines</span>
            </div>
            <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4">
              {steps.map((step, idx) => (
                <div key={idx} className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <div className="text-xs text-slate-500 flex items-center gap-2">
                    <span className="font-semibold text-slate-700">{step.stage}</span>
                    {step.emotion_break?.level ? (
                      <span className="text-rose-500 font-semibold">破防 L{step.emotion_break.level}</span>
                    ) : null}
                  </div>
                  <div className="mt-2 text-sm text-slate-700 leading-relaxed">{step.speech}</div>
                  {step.danmaku && (
                    <div className="mt-2 text-xs text-indigo-500 font-semibold">弹幕：{step.danmaku}</div>
                  )}
                </div>
              ))}
              {steps.length === 0 && <div className="text-slate-300 text-sm">暂无内容</div>}
            </div>

            <div className="mt-4 flex items-center gap-3">
              <input
                value={danmakuInput}
                onChange={(e) => setDanmakuInput(e.target.value)}
                placeholder="发送实时弹幕..."
                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
              />
              <button
                onClick={handleSend}
                className="px-4 py-3 rounded-xl bg-indigo-600 text-white font-semibold"
              >
                发送
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default LiveMonitor;
