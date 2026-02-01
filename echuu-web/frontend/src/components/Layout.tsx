import type { ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Radio,
  History,
  Settings,
  Search,
  LogOut,
  Sparkles,
  ChevronRight,
  Shield
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/", label: "仪表盘", icon: <LayoutDashboard size={18} /> },
  { to: "/characters", label: "角色管理", icon: <Users size={18} /> },
  { to: "/live", label: "直播监控", icon: <Radio size={18} /> },
  { to: "/history", label: "历史记录", icon: <History size={18} /> },
  { to: "/settings", label: "系统设置", icon: <Settings size={18} /> },
];

const NavItem = ({ to, label, icon }: { to: string; label: string; icon: ReactNode }) => (
  <NavLink
    to={to}
    end={to === "/"}
    className={({ isActive }) =>
      `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
        isActive
          ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`
    }
  >
    {icon}
    <span>{label}</span>
    <ChevronRight size={14} className="ml-auto opacity-50" />
  </NavLink>
);

const Layout = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 hidden lg:flex flex-col">
        {/* Logo */}
        <div className="p-6 flex items-center gap-3 border-b border-slate-100">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white flex items-center justify-center shadow-lg shadow-indigo-200">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="font-bold text-slate-800">ECHUU</div>
            <div className="text-xs text-slate-400">AI VTuber Agent</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>

        {/* User Info */}
        <div className="p-4 border-t border-slate-100 space-y-3">
          <div className="bg-gradient-to-r from-slate-50 to-slate-100 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm shadow-md">
                {user?.username?.[0]?.toUpperCase() || "U"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-slate-800 truncate">{user?.username}</div>
                <div className="flex items-center gap-1 text-xs">
                  {isAdmin && <Shield size={10} className="text-amber-500" />}
                  <span className={isAdmin ? "text-amber-600" : "text-slate-500"}>
                    {isAdmin ? "管理员" : "用户"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200"
          >
            <LogOut size={16} />
            <span>退出登录</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
          <div className="relative w-96 max-w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              placeholder="搜索角色、直播记录..."
              className="w-full bg-slate-50 border border-slate-200 rounded-full py-2.5 pl-11 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-xs font-medium">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              后端已连接
            </div>
            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <div className="text-sm font-medium text-slate-700">{user?.username}</div>
                <div className="text-xs text-slate-400">{user?.email || "未设置邮箱"}</div>
              </div>
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm shadow-md">
                {user?.username?.[0]?.toUpperCase() || "U"}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
