import Link from "next/link";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-100 mb-6">Войти в аккаунт</h2>
      <LoginForm />
      <p className="text-sm text-slate-400 mt-4 text-center">
        Нет аккаунта?{" "}
        <Link href="/register" className="text-sky-400 hover:underline">Зарегистрироваться</Link>
      </p>
    </>
  );
}
