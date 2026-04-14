"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { SourceAsset } from "@/types/api";
import api from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  uploaded: "Загружен",
  processing: "Обработка...",
  ready: "Готов",
  failed: "Ошибка",
};

const TYPE_ICON: Record<string, string> = {
  video: "🎬",
  audio: "🎙️",
  image: "🖼️",
  text: "📄",
};

export default function AssetsPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [assets, setAssets] = useState<SourceAsset[]>([]);
  const [brand, setBrand] = useState<{ id: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      return api.get(`/assets/?brand_id=${r.data.id}`);
    }).then((r) => {
      setAssets(r.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const handleDelete = async (assetId: number) => {
    await api.delete(`/assets/${assetId}`);
    setAssets((prev) => prev.filter((a) => a.id !== assetId));
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Asset Library</h1>

      {assets.length === 0 ? (
        <p className="text-slate-400 text-center py-12">Нет загруженных файлов</p>
      ) : (
        <div className="grid gap-3">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{TYPE_ICON[asset.asset_type] ?? "📁"}</span>
                <div>
                  <p className="text-slate-100 font-medium">{asset.name}</p>
                  <p className="text-slate-500 text-xs">
                    {STATUS_LABEL[asset.status] ?? asset.status}
                    {asset.file_size && ` · ${(asset.file_size / 1024 / 1024).toFixed(1)} MB`}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(asset.id)}
                className="text-slate-500 hover:text-red-400 transition-colors text-sm"
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
