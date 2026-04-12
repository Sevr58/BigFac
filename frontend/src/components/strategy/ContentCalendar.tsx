"use client";
import { ContentPlanItem } from "@/types/api";

const NETWORK_COLORS: Record<string, string> = {
  instagram: "text-pink-400",
  vk: "text-blue-400",
  telegram: "text-purple-400",
};

const FUNNEL_DOT: Record<string, string> = {
  tofu: "bg-blue-500",
  mofu: "bg-purple-500",
  bofu: "bg-amber-500",
  retention: "bg-green-500",
};

export function ContentCalendar({ items }: { items: ContentPlanItem[] }) {
  const byDate = items.reduce<Record<string, ContentPlanItem[]>>((acc, item) => {
    if (!acc[item.planned_date]) acc[item.planned_date] = [];
    acc[item.planned_date].push(item);
    return acc;
  }, {});

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-100 mb-4">Контент-план на 4 недели</h2>
      <div className="space-y-3">
        {Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b)).map(([date, dayItems]) => (
          <div key={date} className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <div className="bg-slate-800 px-4 py-2 text-xs font-medium text-slate-400">
              {new Date(date + "T00:00:00").toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
            </div>
            <div className="divide-y divide-slate-800">
              {dayItems.map((item) => (
                <div key={item.id} className="px-4 py-3 flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${FUNNEL_DOT[item.funnel_stage]}`} />
                  <span className={`text-xs font-medium w-20 flex-shrink-0 ${NETWORK_COLORS[item.network] ?? ""}`}>
                    {item.network} · {item.format}
                  </span>
                  <span className="text-sm text-slate-200 flex-1">{item.topic}</span>
                  <span className="text-xs text-slate-500 uppercase">{item.funnel_stage}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
