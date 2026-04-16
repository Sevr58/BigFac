"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";
import type { DraftQueue, PublishedPost } from "@/types/api";

const STATUS_LABEL: Record<string, string> = {
  approved: "Одобрен",
  scheduled: "Запланирован",
  publishing: "Публикуется…",
  published: "Опубликован",
  failed: "Ошибка",
};

const STATUS_COLOR: Record<string, string> = {
  approved: "text-sky-400",
  scheduled: "text-amber-400",
  publishing: "text-purple-400",
  published: "text-green-400",
  failed: "text-red-400",
};

const NETWORK_LABEL: Record<string, string> = {
  instagram: "Instagram",
  vk: "VK",
  telegram: "Telegram",
};

function formatDatetimeLocal(iso: string): string {
  return iso.slice(0, 16);
}

export default function PublishingPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [brandId, setBrandId] = useState<number | null>(null);
  const [queue, setQueue] = useState<DraftQueue[]>([]);
  const [log, setLog] = useState<PublishedPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [scheduleMap, setScheduleMap] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = async (bid: number) => {
    setLoading(true);
    try {
      const [qRes, lRes] = await Promise.all([
        api.get<DraftQueue[]>(`/publishing/queue?brand_id=${bid}`),
        api.get<PublishedPost[]>(`/publishing/log?brand_id=${bid}`),
      ]);
      setQueue(qRes.data);
      setLog(lRes.data);
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

  const handleSchedule = async (draftId: number) => {
    if (!brandId) return;
    const at = scheduleMap[draftId];
    if (!at) { setError("Выберите дату и время"); return; }
    setError(null);
    await api.post("/publishing/schedule", {
      draft_id: draftId,
      scheduled_at: new Date(at).toISOString(),
    });
    load(brandId);
  };

  const handleCancel = async (draftId: number) => {
    if (!brandId) return;
    await api.post(`/publishing/cancel/${draftId}`);
    load(brandId);
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-100">Очередь публикаций</h1>

      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded px-4 py-2 text-red-300 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-slate-400">Загрузка…</p>
      ) : (
        <>
          {/* Queue */}
          <section>
            <h2 className="text-lg font-semibold text-slate-300 mb-3">
              Одобренные и запланированные
            </h2>
            {queue.length === 0 ? (
              <p className="text-slate-500 text-sm">Нет постов в очереди</p>
            ) : (
              <div className="space-y-3">
                {queue.map((d) => (
                  <div
                    key={d.id}
                    className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-slate-400 uppercase">
                          {NETWORK_LABEL[d.network] ?? d.network}
                        </span>
                        <span className="text-xs text-slate-600">·</span>
                        <span className="text-xs text-slate-400">{d.format}</span>
                        <span className="text-xs text-slate-600">·</span>
                        <span className={`text-xs font-medium ${STATUS_COLOR[d.status] ?? "text-slate-400"}`}>
                          {STATUS_LABEL[d.status] ?? d.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300 truncate">{d.text ?? "(нет текста)"}</p>
                      {d.scheduled_at && (
                        <p className="text-xs text-amber-400 mt-1">
                          {new Date(d.scheduled_at).toLocaleString("ru-RU")}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {d.status === "approved" && (
                        <>
                          <input
                            type="datetime-local"
                            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
                            value={scheduleMap[d.id] ?? ""}
                            min={formatDatetimeLocal(new Date().toISOString())}
                            onChange={(e) =>
                              setScheduleMap((prev) => ({ ...prev, [d.id]: e.target.value }))
                            }
                          />
                          <button
                            onClick={() => handleSchedule(d.id)}
                            className="px-3 py-1 text-xs bg-sky-600 hover:bg-sky-500 text-white rounded"
                          >
                            Запланировать
                          </button>
                        </>
                      )}
                      {d.status === "scheduled" && (
                        <button
                          onClick={() => handleCancel(d.id)}
                          className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
                        >
                          Отменить
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Log */}
          <section>
            <h2 className="text-lg font-semibold text-slate-300 mb-3">
              История публикаций
            </h2>
            {log.length === 0 ? (
              <p className="text-slate-500 text-sm">Публикаций ещё нет</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-slate-300">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                      <th className="pb-2 pr-4">Сеть</th>
                      <th className="pb-2 pr-4">ID поста</th>
                      <th className="pb-2 pr-4">Дата</th>
                      <th className="pb-2">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {log.map((pp) => (
                      <tr key={pp.id} className="border-b border-slate-800/50">
                        <td className="py-2 pr-4">{NETWORK_LABEL[pp.network] ?? pp.network}</td>
                        <td className="py-2 pr-4 font-mono text-xs text-slate-400">
                          {pp.network_post_id ?? "—"}
                        </td>
                        <td className="py-2 pr-4 text-slate-400">
                          {new Date(pp.published_at).toLocaleString("ru-RU")}
                        </td>
                        <td className="py-2">
                          {pp.error ? (
                            <span className="text-red-400 text-xs" title={pp.error}>
                              Ошибка
                            </span>
                          ) : (
                            <span className="text-green-400 text-xs">Успешно</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
