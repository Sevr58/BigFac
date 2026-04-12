"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { Brand } from "@/types/api";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

export default function BrandPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [brand, setBrand] = useState<Brand | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Brand>>({});

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      setForm(r.data);
    });
  }, [ws]);

  const save = async () => {
    if (!ws) return;
    try {
      const res = await api.patch(`/workspaces/${ws.id}/brand`, {
        description: form.description,
        target_audience: form.target_audience,
        tone_of_voice: form.tone_of_voice,
      });
      setBrand(res.data);
      setEditing(false);
    } catch {
      // Keep editing mode open on error
    }
  };

  if (!brand) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">{brand.name}</h1>
        <Button onClick={() => setEditing(!editing)} variant="outline" size="sm">
          {editing ? "Отмена" : "Редактировать"}
        </Button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <div>
          <Label>Описание</Label>
          {editing
            ? <textarea className="mt-1 w-full bg-slate-800 border border-slate-700 rounded p-3 text-sm text-slate-100 resize-none" rows={3}
                value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            : <p className="text-sm text-slate-300 mt-1">{brand.description}</p>}
        </div>
        <div>
          <Label>Целевая аудитория</Label>
          {editing
            ? <textarea className="mt-1 w-full bg-slate-800 border border-slate-700 rounded p-3 text-sm text-slate-100 resize-none" rows={2}
                value={form.target_audience ?? ""} onChange={(e) => setForm({ ...form, target_audience: e.target.value })} />
            : <p className="text-sm text-slate-300 mt-1">{brand.target_audience}</p>}
        </div>
        <div>
          <Label>Соцсети</Label>
          <div className="flex gap-2 mt-1">
            {brand.social_accounts.map((a) => (
              <span key={a.id} className="text-xs px-3 py-1 bg-slate-800 border border-slate-700 rounded-full text-slate-300">
                {a.network}
              </span>
            ))}
          </div>
        </div>
        {editing && <Button onClick={save} className="w-full">Сохранить</Button>}
      </div>
    </div>
  );
}
