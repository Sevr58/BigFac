import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Введите корректный email"),
  password: z.string().min(1, "Введите пароль"),
});

export const registerSchema = z.object({
  full_name: z.string().min(2, "Введите имя"),
  email: z.string().email("Введите корректный email"),
  password: z.string().min(6, "Пароль минимум 6 символов"),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
