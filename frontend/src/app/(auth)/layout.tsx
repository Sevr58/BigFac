export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-sky-400">Social Content Factory</h1>
          <p className="text-slate-400 mt-1 text-sm">Автоматизация SMM для вашего бизнеса</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
