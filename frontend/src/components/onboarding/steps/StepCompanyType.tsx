"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const COMPANY_TYPES = [
  { value: "ecommerce", label: "Интернет-магазин" },
  { value: "services", label: "Услуги" },
  { value: "agency", label: "Агентство" },
  { value: "personal_brand", label: "Личный бренд" },
  { value: "saas", label: "SaaS / IT" },
  { value: "other", label: "Другое" },
];

export function StepCompanyType({ onNext }: { onNext: (data: { company_type: string; workspaceName: string }) => void }) {
  const [selected, setSelected] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Тип компании</h2>
      <p className="text-slate-400 text-sm mb-6">Это поможет агенту выбрать правильную стратегию</p>

      <div className="mb-6">
        <Label>Название воркспейса</Label>
        <Input
          className="mt-1"
          placeholder="Например: Моё агентство"
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-8">
        {COMPANY_TYPES.map((t) => (
          <button
            key={t.value}
            onClick={() => setSelected(t.value)}
            className={`p-4 rounded-lg border text-left text-sm transition-all ${
              selected === t.value
                ? "border-sky-500 bg-sky-500/10 text-sky-400"
                : "border-slate-700 text-slate-300 hover:border-slate-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Button
        className="w-full"
        disabled={!selected || !workspaceName.trim()}
        onClick={() => onNext({ company_type: selected, workspaceName: workspaceName.trim() })}
      >
        Далее →
      </Button>
    </div>
  );
}
