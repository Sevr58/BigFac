"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

const TONES = [
  { value: "professional", label: "Профессиональный", desc: "Экспертный, уважительный, без сленга" },
  { value: "casual", label: "Дружелюбный", desc: "Живой, тёплый, как общение с другом" },
  { value: "bold", label: "Смелый", desc: "Провокационный, прямой, запоминающийся" },
  { value: "educational", label: "Образовательный", desc: "Обучающий, структурированный, понятный" },
];

const FREQUENCIES = [
  { value: "daily", label: "Ежедневно" },
  { value: "3x_week", label: "3 раза в неделю" },
  { value: "weekly", label: "Еженедельно" },
];

export function StepTone({ onNext, loading }: { onNext: (data: { tone_of_voice: string; posting_frequency: string }) => void; loading: boolean }) {
  const [tone, setTone] = useState("");
  const [freq, setFreq] = useState("");

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Тон и частота</h2>
      <p className="text-slate-400 text-sm mb-6">Последний шаг — агент готов к работе</p>

      <div className="space-y-3 mb-6">
        {TONES.map((t) => (
          <button
            key={t.value}
            onClick={() => setTone(t.value)}
            className={`w-full p-4 rounded-lg border text-left transition-all ${
              tone === t.value ? "border-sky-500 bg-sky-500/10" : "border-slate-700 hover:border-slate-500"
            }`}
          >
            <div className={`text-sm font-medium ${tone === t.value ? "text-sky-400" : "text-slate-200"}`}>{t.label}</div>
            <div className="text-xs text-slate-400 mt-0.5">{t.desc}</div>
          </button>
        ))}
      </div>

      <Label className="mb-2 block">Частота публикаций</Label>
      <div className="flex gap-3 mb-8">
        {FREQUENCIES.map((f) => (
          <button
            key={f.value}
            onClick={() => setFreq(f.value)}
            className={`flex-1 py-2 rounded-lg border text-sm transition-all ${
              freq === f.value ? "border-sky-500 bg-sky-500/10 text-sky-400" : "border-slate-700 text-slate-300 hover:border-slate-500"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Button
        className="w-full"
        disabled={!tone || !freq || loading}
        onClick={() => onNext({ tone_of_voice: tone, posting_frequency: freq })}
      >
        {loading ? "Создаём стратегию..." : "Запустить агента →"}
      </Button>
    </div>
  );
}
