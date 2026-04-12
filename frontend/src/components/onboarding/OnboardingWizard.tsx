"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { StepCompanyType } from "./steps/StepCompanyType";
import { StepBrandProfile } from "./steps/StepBrandProfile";
import { StepNetworks } from "./steps/StepNetworks";
import { StepGoals } from "./steps/StepGoals";
import { StepTone } from "./steps/StepTone";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";

export interface OnboardingData {
  workspaceName: string;
  company_type: string;
  name: string;
  description: string;
  target_audience: string;
  networks: string[];
  goals: string[];
  tone_of_voice: string;
  posting_frequency: string;
}

const STEPS = ["Компания", "Бренд", "Соцсети", "Цели", "Тон"];

export function OnboardingWizard() {
  const router = useRouter();
  const setCurrent = useWorkspaceStore((s) => s.setCurrent);
  const [step, setStep] = useState(0);
  const [data, setData] = useState<Partial<OnboardingData>>({});
  const [loading, setLoading] = useState(false);

  const next = (patch: Partial<OnboardingData>) => {
    const updated = { ...data, ...patch };
    setData(updated);
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      submit(updated as OnboardingData);
    }
  };

  const submit = async (final: OnboardingData) => {
    setLoading(true);
    try {
      const ws = await api.post("/workspaces/", { name: final.workspaceName });
      const wsId = ws.data.id;
      setCurrent(ws.data);
      await api.post(`/workspaces/${wsId}/brand`, {
        name: final.name,
        company_type: final.company_type,
        description: final.description,
        target_audience: final.target_audience,
        goals: final.goals,
        tone_of_voice: final.tone_of_voice,
        posting_frequency: final.posting_frequency,
        networks: final.networks,
      });
      router.push("/strategy");
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              i < step ? "bg-sky-500 text-white" : i === step ? "bg-sky-400 text-slate-950" : "bg-slate-800 text-slate-400"
            }`}>{i + 1}</div>
            <span className={`text-sm ${i === step ? "text-slate-100" : "text-slate-500"}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="flex-1 h-px bg-slate-800 mx-2" />}
          </div>
        ))}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
        {step === 0 && <StepCompanyType onNext={next} />}
        {step === 1 && <StepBrandProfile onNext={next} />}
        {step === 2 && <StepNetworks onNext={next} />}
        {step === 3 && <StepGoals onNext={next} />}
        {step === 4 && <StepTone onNext={next} loading={loading} />}
      </div>
    </div>
  );
}
