"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { HumanTask } from "@/types/api";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-slate-700 text-slate-300",
  in_progress: "bg-amber-900 text-amber-300",
  completed: "bg-emerald-900 text-emerald-300",
  cancelled: "bg-red-900 text-red-300",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Ожидает",
  in_progress: "В работе",
  completed: "Выполнено",
  cancelled: "Отменено",
};

export default function TasksPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [tasks, setTasks] = useState<HumanTask[]>([]);
  const [brand, setBrand] = useState<{ id: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      return api.get(`/human-tasks/?brand_id=${r.data.id}`);
    }).then((r) => {
      setTasks(r.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const createTask = async () => {
    if (!brand || !newTitle.trim()) return;
    setCreating(true);
    try {
      const res = await api.post("/human-tasks/", {
        brand_id: brand.id,
        title: newTitle,
        description: newDesc || undefined,
      });
      setTasks((prev) => [res.data, ...prev]);
      setNewTitle("");
      setNewDesc("");
    } finally {
      setCreating(false);
    }
  };

  const completeTask = async (taskId: number) => {
    const res = await api.patch(`/human-tasks/${taskId}/complete`, {});
    setTasks((prev) => prev.map((t) => (t.id === taskId ? res.data : t)));
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Задачи команде</h1>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6 space-y-3">
        <h2 className="text-slate-300 font-medium">Новая задача</h2>
        <div>
          <Label>Название</Label>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Снять вводное видео"
          />
        </div>
        <div>
          <Label>Описание</Label>
          <Input
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Детали задачи..."
          />
        </div>
        <Button onClick={createTask} disabled={creating || !newTitle.trim()}>
          {creating ? "Создаём..." : "Создать задачу"}
        </Button>
      </div>

      {tasks.length === 0 ? (
        <p className="text-slate-400 text-center py-12">Нет задач</p>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
            >
              <div>
                <p className="text-slate-100 font-medium">{task.title}</p>
                {task.description && (
                  <p className="text-slate-400 text-sm mt-0.5">{task.description}</p>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${STATUS_COLOR[task.status]}`}>
                  {STATUS_LABEL[task.status] ?? task.status}
                </span>
              </div>
              {task.status === "pending" && (
                <Button size="sm" onClick={() => completeTask(task.id)} variant="outline">
                  Выполнено
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
