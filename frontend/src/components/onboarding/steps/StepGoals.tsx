"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const GOALS = [
  { value: "increase_brand_awareness", label: "Повысить узнаваемость бренда" },
  { value: "generate_leads", label: "Генерировать лиды" },
  { value: "drive_sales", label: "Увеличить продажи" },
  { value: "grow_community", label: "Вырастить сообщество" },
  { value: "establish_expertise", label: "Показать экспертизу" },
  { value: "retain_customers", label: "Удержать клиентов" },
];

export function StepGoals({ onNext }: { onNext: (data: { goals: string[] }) => void }) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (v: string) =>
    setSelected((prev) => prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Цели</h2>
      <p className="text-slate-400 text-sm mb-6">Выберите одну или несколько целей</p>

      <div className="grid grid-cols-1 gap-3 mb-8">
        {GOALS.map((g) => (
          <button
            key={g.value}
            onClick={() => toggle(g.value)}
            className={`p-3 rounded-lg border text-left text-sm transition-all ${
              selected.includes(g.value)
                ? "border-sky-500 bg-sky-500/10 text-sky-400"
                : "border-slate-700 text-slate-300 hover:border-slate-500"
            }`}
          >
            {selected.includes(g.value) ? "✓ " : "  "}{g.label}
          </button>
        ))}
      </div>

      <Button className="w-full" disabled={selected.length === 0} onClick={() => onNext({ goals: selected })}>
        Далее →
      </Button>
    </div>
  );
}
