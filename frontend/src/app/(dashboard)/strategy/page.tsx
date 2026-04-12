"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { ContentPillars } from "@/components/strategy/ContentPillars";
import { ContentCalendar } from "@/components/strategy/ContentCalendar";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { ContentPillar, ContentPlanItem } from "@/types/api";

export default function StrategyPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [pillars, setPillars] = useState<ContentPillar[]>([]);
  const [plan, setPlan] = useState<ContentPlanItem[]>([]);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ws) return;
    Promise.all([
      api.get(`/strategy/workspaces/${ws.id}/pillars`),
      api.get(`/strategy/workspaces/${ws.id}/plan`),
    ]).then(([p, pl]) => {
      setPillars(p.data);
      setPlan(pl.data);
    }).finally(() => setLoading(false));
  }, [ws?.id]);

  const regenerate = async () => {
    if (!ws) return;
    setGenerating(true);
    try {
      const res = await api.post(`/strategy/workspaces/${ws.id}/generate`);
      setPillars(res.data.pillars);
      setPlan(res.data.plan_items);
    } finally {
      setGenerating(false);
    }
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Стратегия</h1>
        <Button onClick={regenerate} disabled={generating} variant="outline">
          {generating ? "Генерируем..." : "Перегенерировать"}
        </Button>
      </div>

      {pillars.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-400 mb-4">Стратегия ещё не создана</p>
          <Button onClick={regenerate} disabled={generating}>
            {generating ? "Агент думает..." : "Создать стратегию"}
          </Button>
        </div>
      ) : (
        <div className="space-y-8">
          <ContentPillars pillars={pillars} />
          <ContentCalendar items={plan} />
        </div>
      )}
    </div>
  );
}
