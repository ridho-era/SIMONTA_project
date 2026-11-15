const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function getCookie(name: string): string | null {
  const baris = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
  return baris ? decodeURIComponent(baris.slice(name.length + 1)) : null;
}

async function pastikanTokenCsrf(): Promise<string> {
  const ada = getCookie("csrftoken");
  if (ada) return ada;
  const res = await fetch(`${BASE}/auth/csrf/`, { credentials: "include" });
  const body = (await res.json()) as { csrfToken?: string };
  return getCookie("csrftoken") ?? body.csrfToken ?? "";
}

function pesanGalat(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return status >= 500
    ? "Terjadi gangguan pada server. Coba lagi nanti."
    : "Permintaan tidak dapat diproses.";
}

interface Opsi {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Objek biasa dikirim sebagai JSON; FormData dikirim sebagai multipart (unggah berkas). */
  body?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, { method = "GET", body, signal }: Opsi = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const multipart = body instanceof FormData;
  // Untuk multipart, Content-Type (beserta boundary) diisi otomatis oleh browser.
  if (body !== undefined && !multipart) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = await pastikanTokenCsrf();

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    signal,
    body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  });

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) throw new ApiError(res.status, data, pesanGalat(data, res.status));
  return data as T;
}

/** Mengumpulkan semua teks galat dari respons validasi DRF ({field: [pesan]} atau {detail}). */
export function kumpulkanGalat(data: unknown): string[] {
  const hasil: string[] = [];
  const telusuri = (nilai: unknown) => {
    if (typeof nilai === "string") hasil.push(nilai);
    else if (Array.isArray(nilai)) nilai.forEach(telusuri);
    else if (nilai && typeof nilai === "object") Object.values(nilai).forEach(telusuri);
  };
  telusuri(data);
  return hasil;
}