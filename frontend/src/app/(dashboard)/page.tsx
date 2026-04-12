"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWorkspaceStore } from "@/store/workspace";
import { useAuthStore } from "@/store/auth";

export default function DashboardPage() {
  const router = useRouter();
  const ws = useWorkspaceStore((s) => s.current);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!user) { router.push("/login"); return; }
    if (!ws) { router.push("/onboarding"); return; }
    router.push("/strategy");
  }, [user, ws, router]);

  return null;
}
