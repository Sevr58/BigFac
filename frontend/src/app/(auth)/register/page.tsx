import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-100 mb-6">Создать аккаунт</h2>
      <RegisterForm />
      <p className="text-sm text-slate-400 mt-4 text-center">
        Уже есть аккаунт?{" "}
        <Link href="/login" className="text-sky-400 hover:underline">Войти</Link>
      </p>
    </>
  );
}
