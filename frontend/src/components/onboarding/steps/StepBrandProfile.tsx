"use client";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface BrandProfileData {
  name: string;
  description: string;
  target_audience: string;
}

export function StepBrandProfile({ onNext }: { onNext: (data: BrandProfileData) => void }) {
  const { register, handleSubmit } = useForm<BrandProfileData>();

  return (
    <form onSubmit={handleSubmit(onNext)}>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Профиль бренда</h2>
      <p className="text-slate-400 text-sm mb-6">Агент использует это для создания контента</p>

      <div className="space-y-4">
        <div>
          <Label>Название бренда</Label>
          <Input className="mt-1" {...register("name", { required: true })} placeholder="Acme Corp" />
        </div>
        <div>
          <Label>Описание бизнеса</Label>
          <textarea
            {...register("description", { required: true })}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-md p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 resize-none"
            rows={3}
            placeholder="Чем занимается компания, что продаёт, в чём уникальность..."
          />
        </div>
        <div>
          <Label>Целевая аудитория</Label>
          <textarea
            {...register("target_audience", { required: true })}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-md p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 resize-none"
            rows={2}
            placeholder="Кто ваш клиент: возраст, интересы, боли, география..."
          />
        </div>
      </div>

      <Button type="submit" className="w-full mt-6">Далее →</Button>
    </form>
  );
}
