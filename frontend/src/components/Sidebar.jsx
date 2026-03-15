import { Activity, SquarePen, LayoutDashboard } from "lucide-react";

export default function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: "analytics", label: "Analytics", icon: Activity },
    { id: "metrics", label: "Metrics", icon: LayoutDashboard },
    { id: "create", label: "Create Post", icon: SquarePen },
    { id: "feed", label: "Feed", icon: LayoutDashboard },
  ];

  return (
    <div className="w-64 h-screen fixed left-0 top-0 bg-gradient-to-b from-[#5c4033] to-[#3e2723] text-white flex flex-col py-8 px-4 shadow-xl z-20">
      <div className="flex items-center gap-3 px-4 mb-12">
        <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-md shadow-inner">
          <div className="w-6 h-6 rounded-full bg-white animate-pulse" style={{ animationDuration: '3s' }} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight">LOOPS</h1>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 ease-out group
                ${
                  isActive
                    ? "bg-white/20 shadow-lg backdrop-blur-md translate-x-2"
                    : "hover:bg-white/10 hover:translate-x-1 opacity-80 hover:opacity-100"
                }
              `}
            >
              <Icon
                className={`w-5 h-5 transition-transform duration-300 ${
                  isActive ? "scale-110" : "group-hover:scale-110"
                }`}
              />
              <span className="font-medium">{item.label}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-6 bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.8)]" />
              )}
            </button>
          );
        })}
      </nav>


    </div>
  );
}
