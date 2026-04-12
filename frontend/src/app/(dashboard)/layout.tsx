"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";

const NAV = [
  { href: "/", label: "Календарь" },
  { href: "/strategy", label: "Стратегия" },
  { href: "/brand", label: "Бренд" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, clearAuth } = useAuthStore();
  const router = useRouter();

  const logout = () => { clearAuth(); router.push("/login"); };

  return (
    <div className="min-h-screen bg-slate-950 flex">
      <aside className="w-48 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <span className="text-sky-400 font-bold text-sm">SCF</span>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href}
              className={`block px-3 py-2 rounded text-sm ${pathname === item.href ? "bg-slate-800 text-sky-400" : "text-slate-400 hover:text-slate-200"}`}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          <button onClick={logout} className="text-xs text-slate-500 hover:text-red-400 mt-1">Выйти</button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}
