import { useState, useEffect } from "react";
import { Plus, Pencil, Trash2, Upload, Brain, Box, Settings as SettingsIcon } from "lucide-react";
import { Card, CardContent, CardHeader } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Select } from "../components/ui/select";
import { useAuth } from "../hooks/useAuth";
import {
  fetchLLMModels,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
} from "../api/modelsApi";
import {
  fetch3DModels,
  upload3DModel,
  create3DModel,
  update3DModel,
  delete3DModel,
} from "../api/modelsApi";
import {
  fetchSettings,
  createSetting,
  updateSetting,
  deleteSetting,
} from "../api/settingsApi";
import type { LLMModel, VTuber3DModel, SystemSetting } from "../types";

const Settings = () => {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState<"llm" | "3d" | "system">("llm");
  const [llmModels, setLlmModels] = useState<LLMModel[]>([]);
  const [vtuber3DModels, setVtuber3DModels] = useState<VTuber3DModel[]>([]);
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingLLM, setEditingLLM] = useState<LLMModel | null>(null);
  const [editing3D, setEditing3D] = useState<VTuber3DModel | null>(null);
  const [llmForm, setLlmForm] = useState<Partial<LLMModel>>({
    name: "",
    provider: "anthropic",
    model_id: "",
    api_key_env: "ANTHROPIC_API_KEY",
    is_default: false,
    config: {},
  });
  const [d3Form, set3dForm] = useState<Partial<VTuber3DModel>>({
    name: "",
    model_path: "",
    provider: "vrm",
    is_default: false,
    config: {},
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [llmData, d3Data, settingsData] = await Promise.all([
        fetchLLMModels(),
        fetch3DModels(),
        fetchSettings(),
      ]);
      setLlmModels(llmData);
      setVtuber3DModels(d3Data);
      setSettings(settingsData);
    } catch (err) {
      console.error("加载数据失败:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleLLMSubmit = async () => {
    try {
      if (editingLLM) {
        await updateLLMModel(editingLLM.id, llmForm);
      } else {
        await createLLMModel(llmForm as LLMModel);
      }
      setEditingLLM(null);
      setLlmForm({
        name: "",
        provider: "anthropic",
        model_id: "",
        api_key_env: "ANTHROPIC_API_KEY",
        is_default: false,
        config: {},
      });
      loadData();
    } catch (err: any) {
      alert(err.message || "操作失败");
    }
  };

  const handle3DSubmit = async () => {
    try {
      if (editing3D) {
        await update3DModel(editing3D.id, d3Form);
      } else {
        await create3DModel(d3Form as VTuber3DModel);
      }
      setEditing3D(null);
      set3dForm({
        name: "",
        model_path: "",
        provider: "vrm",
        is_default: false,
        config: {},
      });
      loadData();
    } catch (err: any) {
      alert(err.message || "操作失败");
    }
  };

  const handle3DUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await upload3DModel(file, d3Form.name, d3Form.provider || "vrm");
      set3dForm({
        name: "",
        model_path: "",
        provider: "vrm",
        is_default: false,
        config: {},
      });
      loadData();
    } catch (err: any) {
      alert(err.message || "上传失败");
    }
  };

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">系统设置</h1>
          <p className="text-sm text-slate-500 mt-1">需要管理员权限才能访问。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">系统设置</h1>
        <p className="text-sm text-slate-500 mt-1">管理 AI 模型、3D 模型和系统配置。</p>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab("llm")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "llm"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Brain size={16} className="inline mr-2" />
          LLM 模型
        </button>
        <button
          onClick={() => setActiveTab("3d")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "3d"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Box size={16} className="inline mr-2" />
          3D 模型
        </button>
        <button
          onClick={() => setActiveTab("system")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "system"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <SettingsIcon size={16} className="inline mr-2" />
          系统配置
        </button>
      </div>

      {/* LLM 模型管理 */}
      {activeTab === "llm" && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            {llmModels.map((model) => (
              <Card key={model.id}>
                <CardContent className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-800">{model.name}</span>
                        {model.is_default && (
                          <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">默认</span>
                        )}
                      </div>
                      <div className="text-sm text-slate-600 mt-1">
                        {model.provider} / {model.model_id}
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        API Key: {model.api_key_env}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setEditingLLM(model);
                          setLlmForm(model);
                        }}
                      >
                        <Pencil size={14} />
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={async () => {
                          if (confirm("确定要删除这个模型吗？")) {
                            try {
                              await deleteLLMModel(model.id);
                              loadData();
                            } catch (err: any) {
                              alert(err.message || "删除失败");
                            }
                          }
                        }}
                        className="text-red-600"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="h-fit">
            <CardHeader>
              <h2 className="font-semibold text-slate-800">
                {editingLLM ? "编辑模型" : "添加 LLM 模型"}
              </h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">名称</label>
                <Input
                  value={llmForm.name || ""}
                  onChange={(e) => setLlmForm({ ...llmForm, name: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">提供商</label>
                <Select
                  value={llmForm.provider || "anthropic"}
                  onChange={(e) => setLlmForm({ ...llmForm, provider: e.target.value as any })}
                  className="mt-1"
                >
                  <option value="anthropic">Anthropic</option>
                  <option value="openai">OpenAI</option>
                  <option value="custom">自定义</option>
                </Select>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">模型 ID</label>
                <Input
                  value={llmForm.model_id || ""}
                  onChange={(e) => setLlmForm({ ...llmForm, model_id: e.target.value })}
                  className="mt-1"
                  placeholder="如: claude-sonnet-4-20250514"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">API Key 环境变量</label>
                <Input
                  value={llmForm.api_key_env || ""}
                  onChange={(e) => setLlmForm({ ...llmForm, api_key_env: e.target.value })}
                  className="mt-1"
                  placeholder="ANTHROPIC_API_KEY"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="llm_default"
                  checked={llmForm.is_default || false}
                  onChange={(e) => setLlmForm({ ...llmForm, is_default: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="llm_default" className="text-sm text-slate-700">
                  设为默认
                </label>
              </div>
              <Button onClick={handleLLMSubmit} className="w-full">
                {editingLLM ? "保存" : "添加"}
              </Button>
              {editingLLM && (
                <Button
                  onClick={() => {
                    setEditingLLM(null);
                    setLlmForm({
                      name: "",
                      provider: "anthropic",
                      model_id: "",
                      api_key_env: "ANTHROPIC_API_KEY",
                      is_default: false,
                      config: {},
                    });
                  }}
                  variant="outline"
                  className="w-full"
                >
                  取消
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 3D 模型管理 */}
      {activeTab === "3d" && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            {vtuber3DModels.map((model) => (
              <Card key={model.id}>
                <CardContent className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-800">{model.name}</span>
                        {model.is_default && (
                          <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">默认</span>
                        )}
                      </div>
                      <div className="text-sm text-slate-600 mt-1">
                        {model.provider} / {model.model_path}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setEditing3D(model);
                          set3dForm(model);
                        }}
                      >
                        <Pencil size={14} />
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={async () => {
                          if (confirm("确定要删除这个模型吗？")) {
                            try {
                              await delete3DModel(model.id);
                              loadData();
                            } catch (err: any) {
                              alert(err.message || "删除失败");
                            }
                          }
                        }}
                        className="text-red-600"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="h-fit">
            <CardHeader>
              <h2 className="font-semibold text-slate-800">
                {editing3D ? "编辑模型" : "添加 3D 模型"}
              </h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">名称</label>
                <Input
                  value={d3Form.name || ""}
                  onChange={(e) => set3dForm({ ...d3Form, name: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">文件路径/URL</label>
                <Input
                  value={d3Form.model_path || ""}
                  onChange={(e) => set3dForm({ ...d3Form, model_path: e.target.value })}
                  className="mt-1"
                  placeholder="/path/to/model.vrm"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">类型</label>
                <Select
                  value={d3Form.provider || "vrm"}
                  onChange={(e) => set3dForm({ ...d3Form, provider: e.target.value })}
                  className="mt-1"
                >
                  <option value="vrm">VRM</option>
                  <option value="glb">GLB</option>
                  <option value="custom">自定义</option>
                </Select>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">上传文件</label>
                <div className="mt-1">
                  <input
                    type="file"
                    accept=".vrm,.glb,.gltf"
                    onChange={handle3DUpload}
                    className="hidden"
                    id="3d-upload"
                  />
                  <label
                    htmlFor="3d-upload"
                    className="flex items-center justify-center gap-2 w-full px-4 py-2 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50"
                  >
                    <Upload size={16} />
                    <span className="text-sm">选择文件</span>
                  </label>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="3d_default"
                  checked={d3Form.is_default || false}
                  onChange={(e) => set3dForm({ ...d3Form, is_default: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="3d_default" className="text-sm text-slate-700">
                  设为默认
                </label>
              </div>
              <Button onClick={handle3DSubmit} className="w-full">
                {editing3D ? "保存" : "添加"}
              </Button>
              {editing3D && (
                <Button
                  onClick={() => {
                    setEditing3D(null);
                    set3dForm({
                      name: "",
                      model_path: "",
                      provider: "vrm",
                      is_default: false,
                      config: {},
                    });
                  }}
                  variant="outline"
                  className="w-full"
                >
                  取消
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 系统配置 */}
      {activeTab === "system" && (
        <div className="space-y-4">
          {settings.map((setting) => (
            <Card key={setting.id}>
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{setting.key}</span>
                      <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
                        {setting.category}
                      </span>
                    </div>
                    <div className="text-sm text-slate-600 mt-1">{setting.value}</div>
                    {setting.description && (
                      <div className="text-xs text-slate-400 mt-1">{setting.description}</div>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={async () => {
                      const newValue = prompt("输入新值:", setting.value);
                      if (newValue !== null) {
                        try {
                          await updateSetting(setting.key, newValue);
                          loadData();
                        } catch (err: any) {
                          alert(err.message || "更新失败");
                        }
                      }
                    }}
                  >
                    <Pencil size={14} />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default Settings;
