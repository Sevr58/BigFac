"use client";
import { ContentPillar } from "@/types/api";

const FUNNEL_COLORS: Record<string, string> = {
  tofu: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  mofu: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  bofu: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  retention: "bg-green-500/20 text-green-400 border-green-500/30",
};

export function ContentPillars({ pillars }: { pillars: ContentPillar[] }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-100 mb-4">Контент-столбы</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {pillars.map((p) => (
          <div key={p.id} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-slate-100 mb-1">{p.title}</h3>
            <p className="text-xs text-slate-400 mb-3">{p.description}</p>
            <div className="flex flex-wrap gap-1">
              {p.funnel_stages.split(",").map((stage) => (
                <span key={stage} className={`text-xs px-2 py-0.5 rounded border ${FUNNEL_COLORS[stage.trim()] ?? ""}`}>
                  {stage.trim().toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
