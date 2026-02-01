import { useState, useEffect } from "react";
import { Plus, Pencil, Trash2, Volume2, X } from "lucide-react";
import { useCharacters } from "../hooks/useCharacters";
import type { CharacterProfile, CharacterCreate, VoiceConfig, VoiceConfigCreate } from "../types";
import { Card, CardContent, CardHeader } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Select } from "../components/ui/select";
import {
  addVoiceConfig,
  updateVoiceConfig,
  deleteVoiceConfig,
} from "../api/charactersApi";
import { fetchLLMModels, fetch3DModels } from "../api/modelsApi";
import type { LLMModel, VTuber3DModel } from "../types";
import { AVAILABLE_VOICES, TTS_MODELS } from "../data/voices";

const emptyForm: CharacterCreate = {
  name: "",
  persona: "",
  background: "",
  voice_configs: [],
};

const Characters = () => {
  const { characters, loading, createCharacter, updateCharacter, deleteCharacter, refresh } = useCharacters();
  const [editing, setEditing] = useState<CharacterProfile | null>(null);
  const [form, setForm] = useState<CharacterCreate>(emptyForm);
  const [llmModels, setLlmModels] = useState<LLMModel[]>([]);
  const [vtuber3DModels, setVtuber3DModels] = useState<VTuber3DModel[]>([]);
  const [showVoiceForm, setShowVoiceForm] = useState(false);
  const [editingVoice, setEditingVoice] = useState<VoiceConfig | null>(null);
  const [voiceForm, setVoiceForm] = useState<VoiceConfigCreate>({
    voice_name: "Cherry",
    tts_model: "qwen3-tts-flash-realtime",
    is_default: false,
    priority: 0,
  });

  useEffect(() => {
    // 加载模型列表
    fetchLLMModels().then(setLlmModels).catch(console.error);
    fetch3DModels().then(setVtuber3DModels).catch(console.error);
  }, []);

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.persona.trim()) {
      alert("请填写角色名称和人设描述");
      return;
    }
    try {
      if (editing) {
        await updateCharacter(editing.id, form);
      } else {
        await createCharacter(form);
      }
      setForm(emptyForm);
      setEditing(null);
      setShowVoiceForm(false);
      refresh();
    } catch (err: any) {
      alert(err.message || "操作失败");
    }
  };

  const handleEdit = (profile: CharacterProfile) => {
    setEditing(profile);
    setForm({
      name: profile.name,
      persona: profile.persona,
      background: profile.background || "",
      avatar_url: profile.avatar_url,
      default_llm_model_id: profile.default_llm_model_id,
      default_3d_model_id: profile.default_3d_model_id,
      voice_configs: profile.voice_configs || [],
    });
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个角色吗？")) return;
    try {
      await deleteCharacter(id);
      refresh();
    } catch (err: any) {
      alert(err.message || "删除失败");
    }
  };

  const handleAddVoice = async () => {
    if (!editing || !voiceForm.voice_name) return;
    try {
      await addVoiceConfig(editing.id, voiceForm);
      setVoiceForm({
        voice_name: "Cherry",
        tts_model: "qwen3-tts-flash-realtime",
        is_default: false,
        priority: 0,
      });
      setShowVoiceForm(false);
      refresh();
    } catch (err: any) {
      alert(err.message || "添加声音失败");
    }
  };

  const handleUpdateVoice = async (voice: VoiceConfig) => {
    if (!editing) return;
    try {
      await updateVoiceConfig(editing.id, voice.id, {
        voice_name: voice.voice_name,
        tts_model: voice.tts_model,
        is_default: voice.is_default,
        priority: voice.priority,
      });
      refresh();
    } catch (err: any) {
      alert(err.message || "更新声音失败");
    }
  };

  const handleDeleteVoice = async (voiceId: string) => {
    if (!editing) return;
    if (!confirm("确定要删除这个声音配置吗？")) return;
    try {
      await deleteVoiceConfig(editing.id, voiceId);
      refresh();
    } catch (err: any) {
      alert(err.message || "删除声音失败");
    }
  };

  const handleSetDefaultVoice = async (voice: VoiceConfig) => {
    if (!editing) return;
    // 先取消所有默认
    const currentVoices = editing.voice_configs || [];
    for (const v of currentVoices) {
      if (v.is_default && v.id !== voice.id) {
        await handleUpdateVoice({ ...v, is_default: false });
      }
    }
    // 设置新的默认
    await handleUpdateVoice({ ...voice, is_default: true });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">角色管理</h1>
        <p className="text-slate-500 text-sm mt-1">管理 VTuber 角色的基本信息、声音配置和模型关联。</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 space-y-4">
          {characters.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center text-slate-500">
                还没有角色，创建一个吧！
              </CardContent>
            </Card>
          ) : (
            characters.map((character) => (
              <Card key={character.id}>
                <CardContent className="p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <div className="text-lg font-bold text-slate-800">{character.name}</div>
                        {!character.is_active && (
                          <span className="text-xs bg-slate-100 text-slate-500 px-2 py-1 rounded">已禁用</span>
                        )}
                      </div>
                      <div className="text-sm text-slate-600 mt-1">{character.persona}</div>
                      {character.background && (
                        <div className="text-xs text-slate-400 mt-3">{character.background}</div>
                      )}
                      
                      {/* 声音列表 */}
                      {character.voice_configs && character.voice_configs.length > 0 && (
                        <div className="mt-4 space-y-2">
                          <div className="text-xs font-bold text-slate-400 uppercase">声音配置</div>
                          <div className="flex flex-wrap gap-2">
                            {character.voice_configs.map((voice) => (
                              <div
                                key={voice.id}
                                className={`text-xs px-2 py-1 rounded ${
                                  voice.is_default
                                    ? "bg-indigo-100 text-indigo-700 border border-indigo-200"
                                    : "bg-slate-100 text-slate-600"
                                }`}
                              >
                                {voice.voice_name}
                                {voice.is_default && " (默认)"}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => handleEdit(character)}
                        className="h-10 px-4 gap-2"
                      >
                        <Pencil size={14} /> 编辑
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => handleDelete(character.id)}
                        className="h-10 px-4 text-red-600 hover:text-red-700"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        <div className="space-y-6">
          {/* 角色表单 */}
          <Card className="h-fit">
            <CardHeader className="flex items-center justify-between mb-2">
              <h2 className="font-semibold text-slate-800">
                {editing ? "编辑角色" : "创建新角色"}
              </h2>
              <Plus size={16} className="text-indigo-500" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">名称 *</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">人设描述 *</label>
                <Textarea
                  value={form.persona}
                  onChange={(e) => setForm({ ...form, persona: e.target.value })}
                  className="mt-1 h-28"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">背景故事</label>
                <Textarea
                  value={form.background || ""}
                  onChange={(e) => setForm({ ...form, background: e.target.value })}
                  className="mt-1 h-24"
                />
              </div>

              {/* 模型选择 */}
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">默认 LLM 模型</label>
                <Select
                  value={form.default_llm_model_id || ""}
                  onChange={(e) => setForm({ ...form, default_llm_model_id: e.target.value || undefined })}
                  className="mt-1"
                >
                  <option value="">使用系统默认</option>
                  {llmModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} {model.is_default && "(默认)"}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">默认 3D 模型</label>
                <Select
                  value={form.default_3d_model_id || ""}
                  onChange={(e) => setForm({ ...form, default_3d_model_id: e.target.value || undefined })}
                  className="mt-1"
                >
                  <option value="">不使用</option>
                  {vtuber3DModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} {model.is_default && "(默认)"}
                    </option>
                  ))}
                </Select>
              </div>

              <Button onClick={handleSubmit} className="w-full">
                {editing ? "保存修改" : "创建角色"}
              </Button>
              {editing && (
                <Button
                  onClick={() => {
                    setEditing(null);
                    setForm(emptyForm);
                    setShowVoiceForm(false);
                  }}
                  variant="outline"
                  className="w-full"
                >
                  取消编辑
                </Button>
              )}
            </CardContent>
          </Card>

          {/* 声音配置管理 */}
          {editing && (
            <Card>
              <CardHeader className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-slate-800">声音配置</h2>
                <Button
                  size="sm"
                  onClick={() => setShowVoiceForm(!showVoiceForm)}
                  className="h-8 px-3"
                >
                  <Plus size={14} /> 添加
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {editing.voice_configs && editing.voice_configs.length > 0 ? (
                  editing.voice_configs.map((voice) => (
                    <div
                      key={voice.id}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Volume2 size={14} className="text-slate-400" />
                          <span className="text-sm font-medium text-slate-700">{voice.voice_name}</span>
                          {voice.is_default && (
                            <span className="text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">默认</span>
                          )}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">{voice.tts_model}</div>
                      </div>
                      <div className="flex gap-1">
                        {!voice.is_default && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSetDefaultVoice(voice)}
                            className="h-7 px-2 text-xs"
                          >
                            设默认
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDeleteVoice(voice.id)}
                          className="h-7 px-2 text-red-600"
                        >
                          <Trash2 size={12} />
                        </Button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-slate-500 text-center py-4">
                    暂无声音配置
                  </div>
                )}

                {showVoiceForm && (
                  <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-indigo-900">添加声音</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowVoiceForm(false)}
                        className="h-6 w-6 p-0"
                      >
                        <X size={14} />
                      </Button>
                    </div>
                    <Select
                      value={voiceForm.voice_name}
                      onChange={(e) => setVoiceForm({ ...voiceForm, voice_name: e.target.value })}
                    >
                      {AVAILABLE_VOICES.map((v) => (
                        <option key={v.value} value={v.value}>
                          {v.label}
                        </option>
                      ))}
                    </Select>
                    <Select
                      value={voiceForm.tts_model}
                      onChange={(e) => setVoiceForm({ ...voiceForm, tts_model: e.target.value })}
                    >
                      {TTS_MODELS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </Select>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="is_default"
                        checked={voiceForm.is_default}
                        onChange={(e) => setVoiceForm({ ...voiceForm, is_default: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="is_default" className="text-sm text-slate-700">
                        设为默认
                      </label>
                    </div>
                    <Button onClick={handleAddVoice} className="w-full" size="sm">
                      添加
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default Characters;
