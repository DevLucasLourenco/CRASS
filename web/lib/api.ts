let csrfToken = '';

export function setCsrf(token: string) { csrfToken = token; }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (options.method && options.method !== 'GET') headers.set('X-CSRF-Token', csrfToken);
  const response = await fetch(`/api${path}`, { ...options, headers, credentials: 'same-origin', cache: 'no-store' });
  if (!response.ok) {
    let detail = `Erro ${response.status}`;
    try { const value = await response.json(); detail = typeof value.detail === 'string' ? value.detail : detail; }
    catch { /* Non-JSON response. */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function json(method: 'POST' | 'PATCH' | 'PUT', body: unknown): RequestInit {
  return { method, body: JSON.stringify(body) };
}

export function localIso(date: Date, timezone: string) {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date);
}

export function dateTime(value: string, timezone = 'America/Sao_Paulo') {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: timezone, dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}

export function timeOnly(value: string, timezone = 'America/Sao_Paulo') {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: timezone, hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export function message(error: unknown) { return error instanceof Error ? error.message : 'Não foi possível concluir a ação.'; }

export function zonedLocalToIso(day: string, clock: string, zone: string) {
  const [year, month, date] = day.split('-').map(Number);
  const [hour, minute] = clock.split(':').map(Number);
  const desired = Date.UTC(year, month - 1, date, hour, minute);
  let guess = desired;
  for (let attempt = 0; attempt < 3; attempt++) {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(guess));
    const values = Object.fromEntries(parts.map(part => [part.type, Number(part.value)]));
    const shown = Date.UTC(values.year, values.month - 1, values.day, values.hour, values.minute);
    const delta = desired - shown;
    guess += delta;
    if (delta === 0) break;
  }
  return new Date(guess).toISOString();
}
