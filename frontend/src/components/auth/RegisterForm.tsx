"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { registerSchema, RegisterInput } from "@/lib/validations/auth";
import api from "@/lib/api";

export function RegisterForm() {
  const router = useRouter();
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterInput) => {
    try {
      await api.post("/auth/register", data);
      router.push("/login?registered=1");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } };
      const msg = axiosErr.response?.status === 409 ? "Email уже зарегистрирован" : "Ошибка регистрации";
      setError("root", { message: msg });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="full_name">Имя</Label>
        <Input id="full_name" {...register("full_name")} />
        {errors.full_name && <p className="text-sm text-red-500 mt-1">{errors.full_name.message}</p>}
      </div>
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
        {isSubmitting ? "Регистрируем..." : "Создать аккаунт"}
      </Button>
    </form>
  );
}
