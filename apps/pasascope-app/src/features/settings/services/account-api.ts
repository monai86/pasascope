import { apiRequest } from "@/lib/api";

/** Deletes the signed-in account with everything in its workspace. */
export async function deleteOwnAccount(): Promise<void> {
  await apiRequest<{ status: string }>("/account", { method: "DELETE" });
}
