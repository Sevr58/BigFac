"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { Draft } from "@/types/api";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";

const STATUS_COLOR: Record<string, string> = {
  draft: "bg-slate-700 text-slate-300",
  needs_review: "bg-amber-900 text-amber-300",
  approved: "bg-emerald-900 text-emerald-300",
  rejected: "bg-red-900 text-red-300",
  published: "bg-sky-900 text-sky-300",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Черновик",
  needs_review: "На проверке",
  approved: "Одобрен",
  rejected: "Отклонён",
  published: "Опубликован",
};

const NETWORKS = ["instagram", "vk", "telegram"];
const FORMATS: Record<string, string[]> = {
  instagram: ["carousel", "reels", "static_post", "story"],
  vk: ["clip", "long_post", "poll", "long_video"],
  telegram: ["longread", "image_post", "poll", "voice", "link"],
};
const STAGES = ["tofu", "mofu", "bofu", "retention"];

function DraftCard({ draft, onUpdated }: { draft: Draft; onUpdated: (d: Draft) => void }) {
  const canSubmit = draft.status === "draft" || draft.status === "rejected";
  const canApprove = draft.status === "needs_review";

  const submit = async () => {
    const res = await api.post(`/drafts/${draft.id}/submit`);
    onUpdated(res.data);
  };

  const approve = async () => {
    const res = await api.post(`/approvals/${draft.id}/approve`, { comment: "" });
    onUpdated(res.data);
  };

  const reject = async () => {
    const comment = prompt("Причина отклонения:");
    if (comment === null) return;
    const res = await api.post(`/approvals/${draft.id}/reject`, { comment });
    onUpdated(res.data);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-sm">{draft.network} · {draft.format} · {draft.funnel_stage}</span>
        <span className={`text-xs px-2 py-1 rounded-full ${STATUS_COLOR[draft.status] ?? "bg-slate-700 text-slate-300"}`}>
          {STATUS_LABEL[draft.status] ?? draft.status}
        </span>
      </div>

      {draft.text && (
        <p className="text-slate-200 text-sm whitespace-pre-wrap">{draft.text}</p>
      )}

      {draft.hashtags.length > 0 && (
        <p className="text-sky-400 text-sm">{draft.hashtags.map((h) => `#${h}`).join(" ")}</p>
      )}

      <div className="flex gap-2 pt-1">
        {canSubmit && (
          <Button size="sm" onClick={submit}>На проверку</Button>
        )}
        {canApprove && (
          <>
            <Button size="sm" onClick={approve} className="bg-emerald-600 hover:bg-emerald-700">Одобрить</Button>
            <Button size="sm" onClick={reject} variant="outline" className="border-red-700 text-red-400 hover:bg-red-950">Отклонить</Button>
          </>
        )}
      </div>
    </div>
  );
}

export default function DraftsPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [brand, setBrand] = useState<{ id: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [network, setNetwork] = useState("instagram");
  const [format, setFormat] = useState("carousel");
  const [stage, setStage] = useState("tofu");

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      return api.get(`/drafts/?brand_id=${r.data.id}`);
    }).then((r) => {
      setDrafts(r.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const generate = async () => {
    if (!brand) return;
    setGenerating(true);
    try {
      await api.post("/drafts/generate", {
        brand_id: brand.id,
        network,
        format,
        funnel_stage: stage,
      });
      setTimeout(async () => {
        const r = await api.get(`/drafts/?brand_id=${brand.id}`);
        setDrafts(r.data);
        setGenerating(false);
      }, 3000);
    } catch {
      setGenerating(false);
    }
  };

  const handleUpdated = (updated: Draft) => {
    setDrafts((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Черновики</h1>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-slate-400 text-xs block mb-1">Сеть</label>
          <select
            value={network}
            onChange={(e) => { setNetwork(e.target.value); setFormat(FORMATS[e.target.value][0]); }}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm"
          >
            {NETWORKS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="text-slate-400 text-xs block mb-1">Формат</label>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm"
          >
            {(FORMATS[network] ?? []).map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <label className="text-slate-400 text-xs block mb-1">Воронка</label>
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm"
          >
            {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <Button onClick={generate} disabled={generating}>
          {generating ? "Генерируем..." : "Сгенерировать"}
        </Button>
      </div>

      {drafts.length === 0 ? (
        <p className="text-slate-400 text-center py-12">Нет черновиков</p>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} onUpdated={handleUpdated} />
          ))}
        </div>
      )}
    </div>
  );
}
