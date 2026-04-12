import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";

export default function OnboardingPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Добро пожаловать</h1>
      <p className="text-slate-400 mb-8">Настроим вашу контент-фабрику за 2 минуты</p>
      <OnboardingWizard />
    </div>
  );
}
