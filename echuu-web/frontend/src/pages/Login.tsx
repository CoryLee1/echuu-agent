import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Sparkles, User, Mail, Lock, ArrowRight, Loader2 } from "lucide-react";

const Login = () => {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        await login({ username: form.username, password: form.password });
      } else {
        await register({
          username: form.username,
          email: form.email,
          password: form.password,
        });
      }
      navigate("/");
    } catch (err: any) {
      setError(err.message || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-indigo-600 via-indigo-700 to-purple-800 p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
              <Sparkles className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">ECHUU</h1>
              <p className="text-indigo-200 text-sm">AI VTuber Agent</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-4xl font-bold text-white leading-tight">
            让 AI 主播<br />
            像真人一样<br />
            自然地讲故事
          </h2>
          <p className="text-indigo-200 text-lg max-w-md">
            基于真实主播表演模式学习，生成自然、有情感、会跑题的直播内容。
          </p>
          <div className="flex gap-4">
            <div className="bg-white/10 backdrop-blur rounded-xl px-4 py-3">
              <div className="text-2xl font-bold text-white">6</div>
              <div className="text-indigo-200 text-sm">故事模式</div>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-xl px-4 py-3">
              <div className="text-2xl font-bold text-white">30+</div>
              <div className="text-indigo-200 text-sm">真实切片</div>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-xl px-4 py-3">
              <div className="text-2xl font-bold text-white">∞</div>
              <div className="text-indigo-200 text-sm">创意可能</div>
            </div>
          </div>
        </div>

        <div className="text-indigo-300 text-sm">
          © 2024 ECHUU Agent. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-8">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardContent className="p-8">
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center">
                <Sparkles className="text-white" size={20} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-800">ECHUU</h1>
                <p className="text-slate-500 text-xs">AI VTuber Agent</p>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-bold text-slate-800">
                {isLogin ? "欢迎回来" : "创建账户"}
              </h2>
              <p className="text-slate-500 mt-1">
                {isLogin ? "登录到 ECHUU 控制台" : "开始你的 AI 主播之旅"}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full" />
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">用户名</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <Input
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    className="pl-10"
                    placeholder="输入用户名"
                    required
                  />
                </div>
              </div>

              {!isLogin && (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">邮箱</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <Input
                      type="email"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      className="pl-10"
                      placeholder="you@example.com"
                      required
                    />
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">密码</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <Input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className="pl-10"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>

              <Button type="submit" className="w-full h-12 text-base" disabled={loading}>
                {loading ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <>
                    {isLogin ? "登录" : "注册"}
                    <ArrowRight className="ml-2" size={18} />
                  </>
                )}
              </Button>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-slate-500">
                    {isLogin ? "还没有账户？" : "已有账户？"}
                  </span>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError("");
                }}
                className="w-full"
              >
                {isLogin ? "创建新账户" : "返回登录"}
              </Button>
            </form>

            {isLogin && (
              <div className="mt-6 p-4 bg-slate-50 rounded-xl">
                <p className="text-xs text-slate-500 mb-2">默认管理员账户：</p>
                <div className="flex gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">用户名：</span>
                    <code className="text-indigo-600 font-mono">admin</code>
                  </div>
                  <div>
                    <span className="text-slate-400">密码：</span>
                    <code className="text-indigo-600 font-mono">admin123</code>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
