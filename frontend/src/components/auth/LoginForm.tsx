"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginSchema, LoginInput } from "@/lib/validations/auth";
import { useAuthStore } from "@/store/auth";
import api from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginInput) => {
    try {
      const tokenRes = await api.post("/auth/login", data);
      const token = tokenRes.data.access_token;
      const userRes = await api.get("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
      setAuth(userRes.data, token);
      router.push("/");
    } catch {
      setError("root", { message: "Неверный email или пароль" });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" {...register("email")} />
        {errors.email && <p className="text-sm text-red-500 mt-1">{errors.email.message}</p>}
      </div>
      <div>
        <Label htmlFor="password">Пароль</Label>
        <Input id="password" type="password" {...register("password")} />
        {errors.password && <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>}
      </div>
      {errors.root && <p className="text-sm text-red-500">{errors.root.message}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Входим..." : "Войти"}
      </Button>
    </form>
  );
}
