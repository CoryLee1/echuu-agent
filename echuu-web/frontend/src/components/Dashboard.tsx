import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, MessageSquare, Heart, Brain, 
  Send, Activity, Volume2, VolumeX, Download, 
  ChevronRight, Sparkles, History, Settings, 
  LayoutDashboard, Users, FileText, Bell, Search
} from 'lucide-react';

const Dashboard = () => {
  // 状态管理
  const [status, setStatus] = useState('idle'); 
  const [logs, setLogs] = useState([]);
  const [reasoning, setReasoning] = useState([]);
  const [steps, setSteps] = useState([]);
  const [autoPlay, setAutoPlay] = useState(true);
  const [currentSession, setCurrentSession] = useState(null);
  const [memory, setMemory] = useState({ story_points: [], promises: [], emotion_trend: [] });
  const [config, setConfig] = useState({
    character_name: '六螺',
    topic: '关于上司的超劲爆八卦',
    tts_voice: 'Cherry'
  });
  const [inputDanmaku, setInputDanmaku] = useState('');
  
  const scrollRef = useRef(null);
  const reasoningRef = useRef(null);
  const audioRef = useRef(new Audio());
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);

  // WebSocket 逻辑
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'step') {
        const stepData = msg.data;
        setSteps(prev => [...prev, stepData]);
        if (stepData.memory_snapshot) setMemory(stepData.memory_snapshot);
        if (autoPlay && stepData.audio_url) {
          enqueueAudio(stepData.audio_url);
        }
      } else if (msg.type === 'reasoning') {
        setReasoning(prev => [...prev, msg.content]);
      } else if (msg.type === 'finish') {
        setStatus('idle');
        setCurrentSession(msg.session_id);
      }
    };
    return () => ws.close();
  }, [autoPlay]);

  // 滚动处理
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [steps]);
  useEffect(() => {
    if (reasoningRef.current) reasoningRef.current.scrollTop = reasoningRef.current.scrollHeight;
  }, [reasoning]);

  const playNextAudio = () => {
    const nextUrl = audioQueueRef.current.shift();
    if (!nextUrl) {
      isPlayingRef.current = false;
      return;
    }
    isPlayingRef.current = true;
    audioRef.current.src = `http://localhost:8000${nextUrl}`;
    audioRef.current
      .play()
      .catch(() => {
        isPlayingRef.current = false;
      });
  };

  const enqueueAudio = (audioUrl) => {
    audioQueueRef.current.push(audioUrl);
    if (!isPlayingRef.current) {
      playNextAudio();
    }
  };

  useEffect(() => {
    const audio = audioRef.current;
    audio.onended = () => playNextAudio();
    audio.onerror = () => playNextAudio();
    return () => {
      audio.onended = null;
      audio.onerror = null;
    };
  }, []);

  useEffect(() => {
    if (!autoPlay) {
      audioQueueRef.current = [];
      audioRef.current.pause();
      isPlayingRef.current = false;
    }
  }, [autoPlay]);

  const startLive = async () => {
    setStatus('running');
    setSteps([]);
    setReasoning([]);
    setMemory({ story_points: [], promises: [], emotion_trend: [] });
    await fetch('http://localhost:8000/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        char: { name: config.character_name, persona: '性格古怪、碎碎念', background: '直播间' },
        config: { topic: config.topic, tts_voice: config.tts_voice }
      }),
    });
  };

  const sendDanmaku = async () => {
    if (!inputDanmaku) return;
    await fetch(`http://localhost:8000/api/danmaku?text=${encodeURIComponent(inputDanmaku)}&user=我`, { method: 'POST' });
    setInputDanmaku('');
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-900 font-sans overflow-hidden">
      
      {/* 1. Sidebar - 侧边栏 */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col hidden lg:flex">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold">E</div>
          <span className="text-xl font-bold tracking-tight text-slate-800">ECHUU AI</span>
        </div>
        
        <nav className="flex-1 px-4 space-y-1 mt-4">
          <NavItem icon={<LayoutDashboard size={20}/>} label="Dashboard" active />
          <NavItem icon={<Users size={20}/>} label="Characters" />
          <NavItem icon={<FileText size={20}/>} label="Sessions" />
          <NavItem icon={<History size={20}/>} label="History" />
          <div className="pt-4 pb-2 px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Settings</div>
          <NavItem icon={<Settings size={20}/>} label="Configurations" />
        </nav>

        <div className="p-4 border-t border-slate-100">
          <div className="bg-slate-50 p-4 rounded-xl flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-bold">AD</div>
            <div className="text-xs">
              <div className="font-bold">Admin Mode</div>
              <div className="text-slate-500">Connected</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content - 主体 */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* 2. Top Header - 顶部导航 */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 z-10">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative w-96 max-w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input 
                placeholder="Search sessions, memory points..." 
                className="w-full bg-slate-100 border-none rounded-full py-2 pl-10 pr-4 text-sm focus:ring-2 ring-indigo-500/20 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <button 
              onClick={() => setAutoPlay(!autoPlay)}
              className={`p-2 rounded-full transition-all ${autoPlay ? 'text-indigo-600 bg-indigo-50' : 'text-slate-400 bg-slate-100'}`}
            >
              {autoPlay ? <Volume2 size={20}/> : <VolumeX size={20}/>}
            </button>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-slate-300'}`} />
              <span className="text-sm font-semibold text-slate-600 uppercase tracking-tighter">
                {status === 'running' ? 'Streaming' : 'Ready'}
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-slate-200 border border-slate-300" />
          </div>
        </header>

        {/* 3. Dashboard Grid - 栅格系统内容区 */}
        <div className="flex-1 overflow-y-auto p-8 bg-[#F8FAFC]">
          <div className="max-w-[1600px] mx-auto space-y-8">
            
            {/* Row 1: Quick Stats & Config */}
            <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-12 gap-8">
              
              {/* Reasoning Engine (Thought Process) */}
              <section className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[400px]">
                <div className="px-6 py-4 border-b border-slate-50 flex justify-between items-center bg-white">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2">
                    <Brain className="text-indigo-500" size={18} /> AI Reasoning Engine
                  </h3>
                  <div className="flex gap-1 h-4 items-end">
                    {memory.emotion_trend.map((l, i) => (
                      <div key={i} className="w-1 bg-indigo-400 rounded-full" style={{height: `${l*4 + 4}px`}} />
                    ))}
                  </div>
                </div>
                <div ref={reasoningRef} className="flex-1 p-6 overflow-y-auto font-mono text-[12px] text-slate-600 space-y-2 leading-relaxed">
                  {reasoning.map((r, i) => (
                    <div key={i} className="flex gap-3 py-1 border-b border-slate-50 last:border-0">
                      <ChevronRight size={14} className="text-indigo-300 mt-0.5 flex-shrink-0" />
                      <span className="whitespace-pre-wrap">{r}</span>
                    </div>
                  ))}
                  {reasoning.length === 0 && <div className="h-full flex items-center justify-center text-slate-300 italic">Standing by for next creation...</div>}
                </div>
              </section>

              {/* Memory & Status Panel */}
              <section className="lg:col-span-4 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[400px]">
                <div className="px-6 py-4 border-b border-slate-50 flex justify-between items-center">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2">
                    <History className="text-indigo-500" size={18} /> Live Memory
                  </h3>
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Realtime</div>
                </div>
                <div className="p-6 space-y-6 overflow-y-auto">
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase mb-3 tracking-widest">Mentioned Points</div>
                    <div className="flex flex-wrap gap-2">
                      {memory.story_points.map((p, i) => (
                        <span key={i} className="px-3 py-1 bg-indigo-50 text-indigo-600 text-[11px] font-bold rounded-full border border-indigo-100 italic">
                          # {p}
                        </span>
                      ))}
                      {memory.story_points.length === 0 && <span className="text-xs text-slate-300 italic">No points recorded yet</span>}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase mb-3 tracking-widest">Active Promises</div>
                    <div className="space-y-2">
                      {memory.promises.map((p, i) => (
                        <div key={i} className="text-xs text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100 flex items-start gap-2">
                          <Sparkles size={14} className="text-amber-500 mt-0.5" />
                          <span>{p.content}</span>
                        </div>
                      ))}
                      {memory.promises.length === 0 && <span className="text-xs text-slate-300 italic">No pending promises</span>}
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {/* Row 2: Live Stream & Control */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Configuration Sidebar */}
              <aside className="lg:col-span-3 space-y-6">
                <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                  <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2">
                    <Settings className="text-indigo-500" size={18}/> Configuration
                  </h3>
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Character Name</label>
                      <input 
                        className="w-full bg-slate-50 border border-slate-100 rounded-xl p-3 text-sm outline-none focus:ring-2 ring-indigo-500/10 transition-all font-semibold"
                        value={config.character_name}
                        onChange={(e) => setConfig({...config, character_name: e.target.value})}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Story Topic</label>
                      <textarea 
                        className="w-full bg-slate-50 border border-slate-100 rounded-xl p-3 text-sm h-32 resize-none outline-none focus:ring-2 ring-indigo-500/10 transition-all font-medium"
                        value={config.topic}
                        onChange={(e) => setConfig({...config, topic: e.target.value})}
                      />
                    </div>
                    <button 
                      onClick={startLive}
                      disabled={status === 'running'}
                      className="w-full bg-indigo-600 hover:bg-indigo-700 py-4 rounded-xl font-bold text-white shadow-lg shadow-indigo-200 transition-all active:scale-95 disabled:grayscale disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {status === 'running' ? <Activity size={18} className="animate-spin"/> : <Play size={18} fill="currentColor"/>}
                      {status === 'running' ? 'AGENT ACTIVE' : 'INITIALIZE LIVE'}
                    </button>
                  </div>
                </section>

                {currentSession && (
                  <section className="bg-indigo-600 p-6 rounded-2xl shadow-xl text-white">
                    <h3 className="font-bold mb-2 flex items-center gap-2">
                      <Download size={18}/> Export Results
                    </h3>
                    <p className="text-xs text-indigo-100 mb-4 opacity-80">Download the complete session package (Scripts + Audio)</p>
                    <a 
                      href={`http://localhost:8000/api/download/${currentSession}`}
                      className="block w-full bg-white/20 hover:bg-white/30 py-3 rounded-xl text-center text-sm font-bold backdrop-blur-md transition-all border border-white/20"
                    >
                      Download Bundle (.zip)
                    </a>
                  </section>
                )}
              </aside>

              {/* Main Live Feed */}
              <section className="lg:col-span-9 bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[700px]">
                <div className="px-8 py-5 border-b border-slate-50 flex justify-between items-center">
                  <h3 className="font-bold text-slate-800 text-lg flex items-center gap-3">
                    <MessageSquare className="text-indigo-500" size={22}/> Live Performance Stream
                  </h3>
                  <div className="flex gap-2">
                    <span className="px-3 py-1 bg-slate-100 rounded-full text-[10px] font-bold text-slate-400">SESSION ID: {currentSession || 'NEW'}</span>
                  </div>
                </div>

                {/* Speech Area */}
                <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-10 scroll-smooth bg-slate-50/30">
                  {steps.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-slate-200">
                      <Activity size={120} strokeWidth={1}/>
                      <p className="mt-4 text-slate-300 font-bold uppercase tracking-[1em]">IDLE_STATE</p>
                    </div>
                  )}

                  {steps.map((step, i) => (
                    <div key={i} className="animate-in fade-in slide-in-from-bottom-6 duration-700">
                      <div className="flex gap-6 items-start">
                        <div className="relative">
                          <div className="w-14 h-14 bg-indigo-100 rounded-2xl border-2 border-indigo-200 flex items-center justify-center text-indigo-600 font-black text-xl overflow-hidden shadow-sm">
                            {config.character_name[0]}
                          </div>
                          {step.emotion_break?.level > 0 && (
                            <div className="absolute -top-2 -right-2 bg-rose-500 text-[10px] px-2 py-0.5 rounded-full font-black text-white shadow-lg border-2 border-white animate-bounce">
                              L{step.emotion_break.level}
                            </div>
                          )}
                        </div>

                        <div className="flex-1 space-y-4">
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-black text-slate-800 uppercase">{config.character_name}</span>
                            <span className="text-[10px] font-bold text-slate-400 bg-white border border-slate-200 px-2 py-0.5 rounded uppercase tracking-widest">{step.stage}</span>
                            {step.audio_url && (
                              <button
                                onClick={() => enqueueAudio(step.audio_url)}
                                className="text-indigo-300 hover:text-indigo-600 transition-colors"
                              >
                                <Volume2 size={16} />
                              </button>
                            )}
                          </div>

                          <div className="bg-white p-6 rounded-3xl rounded-tl-none shadow-sm border border-slate-100 text-slate-700 text-lg leading-relaxed max-w-[90%]">
                            {step.speech}
                          </div>

                          <div className="flex items-start gap-2 text-slate-400 text-xs italic ml-2">
                            <Brain size={14} className="mt-0.5 opacity-50 text-indigo-400" />
                            <span>Inner Thought: {step.inner_monologue || 'Maintaining narrative flow...'}</span>
                          </div>

                          {step.danmaku && (
                            <div className="flex items-center gap-2 text-[11px] font-bold text-indigo-500 bg-indigo-50/50 px-4 py-2 rounded-full border border-indigo-100 self-start shadow-sm">
                              <MessageSquare size={14} />
                              <span>Interaction: "{step.danmaku}"</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footer Interaction Input */}
                <div className="p-6 bg-white border-t border-slate-100">
                  <div className="relative flex items-center group">
                    <input 
                      placeholder="Inject realtime message to influence the Agent..."
                      className="w-full bg-slate-50 border border-slate-200 rounded-2xl pl-6 pr-16 py-4 text-sm outline-none focus:bg-white focus:border-indigo-600 focus:ring-4 ring-indigo-500/5 transition-all placeholder:text-slate-300 font-medium"
                      value={inputDanmaku}
                      onChange={(e) => setInputDanmaku(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendDanmaku()}
                    />
                    <button 
                      onClick={sendDanmaku}
                      className="absolute right-3 bg-indigo-600 hover:bg-indigo-700 p-3 rounded-xl text-white shadow-lg shadow-indigo-100 transition-all active:scale-90"
                    >
                      <Send size={20} />
                    </button>
                  </div>
                </div>
              </section>

            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

// 侧边栏子项组件
const NavItem = ({ icon, label, active = false }) => (
  <div className={`flex items-center gap-4 px-4 py-3 rounded-xl cursor-pointer transition-all ${active ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'}`}>
    {icon}
    <span className="text-sm font-bold">{label}</span>
  </div>
);

export default Dashboard;
