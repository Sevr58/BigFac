"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const NETWORKS = [
  { value: "instagram", label: "Instagram", icon: "📸" },
  { value: "vk", label: "VKontakte", icon: "💙" },
  { value: "telegram", label: "Telegram", icon: "✈️" },
];

export function StepNetworks({ onNext }: { onNext: (data: { networks: string[] }) => void }) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (v: string) =>
    setSelected((prev) => prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Соцсети</h2>
      <p className="text-slate-400 text-sm mb-6">Выберите где будете публиковать контент</p>

      <div className="space-y-3 mb-8">
        {NETWORKS.map((n) => (
          <button
            key={n.value}
            onClick={() => toggle(n.value)}
            className={`w-full p-4 rounded-lg border text-left flex items-center gap-3 transition-all ${
              selected.includes(n.value)
                ? "border-sky-500 bg-sky-500/10"
                : "border-slate-700 hover:border-slate-500"
            }`}
          >
            <span className="text-2xl">{n.icon}</span>
            <span className={`text-sm font-medium ${selected.includes(n.value) ? "text-sky-400" : "text-slate-300"}`}>
              {n.label}
            </span>
            {selected.includes(n.value) && <span className="ml-auto text-sky-400">✓</span>}
          </button>
        ))}
      </div>

      <Button className="w-full" disabled={selected.length === 0} onClick={() => onNext({ networks: selected })}>
        Далее →
      </Button>
    </div>
  );
}
