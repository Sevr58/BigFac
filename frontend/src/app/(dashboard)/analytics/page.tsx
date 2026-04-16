"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";
import type { AnalyticsSummary, PostAnalyticsItem } from "@/types/api";

const NETWORK_LABEL: Record<string, string> = {
  instagram: "Instagram",
  vk: "VK",
  telegram: "Telegram",
};

const FUNNEL_LABEL: Record<string, string> = {
  tofu: "TOFU",
  mofu: "MOFU",
  bofu: "BOFU",
  retention: "Retention",
};

function BarChart({
  data,
  label,
}: {
  data: { name: string; value: number }[];
  label: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div>
      <p className="text-xs text-slate-400 mb-2 uppercase tracking-wide">{label}</p>
      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-2">
            <span className="w-24 text-xs text-slate-400 truncate">{d.name}</span>
            <div className="flex-1 bg-slate-800 rounded-full h-3">
              <div
                className="bg-sky-500 h-3 rounded-full transition-all"
                style={{ width: `${(d.value / max) * 100}%` }}
              />
            </div>
            <span className="w-12 text-right text-xs text-slate-400">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-100">{value}</p>
    </div>
  );
}

export default function AnalyticsPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [brandId, setBrandId] = useState<number | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [posts, setPosts] = useState<PostAnalyticsItem[]>([]);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [loopLoading, setLoopLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = async (bid: number) => {
    setLoading(true);
    try {
      const [sRes, pRes] = await Promise.all([
        api.get<AnalyticsSummary>(`/analytics/summary?brand_id=${bid}`),
        api.get<PostAnalyticsItem[]>(`/analytics/posts?brand_id=${bid}`),
      ]);
      setSummary(sRes.data);
      setPosts(pRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ws) return;
    api.get<{ id: number }>(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrandId(r.data.id);
      load(r.data.id);
    });
  }, [ws]);

  const runFeedbackLoop = async () => {
    if (!brandId) return;
    setLoopLoading(true);
    setSuggestion(null);
    try {
      const res = await api.post<{ suggestion: string }>(
        `/analytics/feedback-loop?brand_id=${brandId}`
      );
      setSuggestion(res.data.suggestion);
    } finally {
      setLoopLoading(false);
    }
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;

  if (loading || !summary) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-slate-100">Аналитика</h1>
        <p className="text-slate-400">Загрузка…</p>
      </div>
    );
  }

  const networkChartData = Object.entries(summary.by_network).map(([net, v]) => ({
    name: NETWORK_LABEL[net] ?? net,
    value: v.views,
  }));

  const formatChartData = Object.entries(summary.by_format).map(([fmt, v]) => ({
    name: fmt,
    value: v.views,
  }));

  const funnelChartData = Object.entries(summary.by_funnel).map(([stage, v]) => ({
    name: FUNNEL_LABEL[stage] ?? stage,
    value: v.total_posts,
  }));

  const topPosts = [...posts]
    .filter((p) => p.metrics?.views != null)
    .sort((a, b) => (b.metrics!.views ?? 0) - (a.metrics!.views ?? 0))
    .slice(0, 5);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-100">Аналитика</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Постов опубликовано" value={summary.total_posts} />
        <StatCard label="Просмотры" value={summary.total_views.toLocaleString("ru-RU")} />
        <StatCard label="Лиды" value={summary.total_leads} />
        <StatCard
          label="Активных сетей"
          value={Object.keys(summary.by_network).length}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {networkChartData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <BarChart data={networkChartData} label="По сетям (просмотры)" />
          </div>
        )}
        {formatChartData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <BarChart data={formatChartData} label="По форматам (просмотры)" />
          </div>
        )}
        {funnelChartData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <BarChart data={funnelChartData} label="По воронке (постов)" />
          </div>
        )}
      </div>

      {/* Top posts */}
      {topPosts.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-slate-300 mb-3">
            Топ постов по просмотрам
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-slate-300">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                  <th className="pb-2 pr-4">Сеть</th>
                  <th className="pb-2 pr-4">Дата</th>
                  <th className="pb-2 pr-4 text-right">Просмотры</th>
                  <th className="pb-2 pr-4 text-right">Лайки</th>
                  <th className="pb-2 text-right">Репосты</th>
                </tr>
              </thead>
              <tbody>
                {topPosts.map((p) => (
                  <tr key={p.id} className="border-b border-slate-800/50">
                    <td className="py-2 pr-4">{NETWORK_LABEL[p.network] ?? p.network}</td>
                    <td className="py-2 pr-4 text-slate-400">
                      {new Date(p.published_at).toLocaleDateString("ru-RU")}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono">
                      {p.metrics?.views?.toLocaleString("ru-RU") ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono">
                      {p.metrics?.likes?.toLocaleString("ru-RU") ?? "—"}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {p.metrics?.shares?.toLocaleString("ru-RU") ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Feedback loop */}
      <section className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">AI-анализ стратегии</h2>
            <p className="text-sm text-slate-400 mt-1">
              Клод проанализирует последние результаты и предложит скорректировать контент-план.
            </p>
          </div>
          <button
            onClick={runFeedbackLoop}
            disabled={loopLoading}
            className="shrink-0 px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm rounded"
          >
            {loopLoading ? "Анализирую…" : "Запустить анализ"}
          </button>
        </div>

        {suggestion && (
          <div className="bg-slate-800 rounded p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {suggestion}
          </div>
        )}
      </section>
    </div>
  );
}
