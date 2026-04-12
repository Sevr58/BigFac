import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Workspace } from "@/types/api";

interface WorkspaceState {
  current: Workspace | null;
  setCurrent: (ws: Workspace) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      current: null,
      setCurrent: (ws) => set({ current: ws }),
    }),
    { name: "workspace-storage" }
  )
);
