'use client';

import { useState, type FormEvent } from 'react';
import { api, json, message, setCsrf } from '@/lib/api';
import type { User } from '@/lib/types';

export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await api<{ user: User; csrf: string }>('/auth/login', json('POST', { email, password, code: code || undefined }));
      setCsrf(result.csrf); onLogin(result.user);
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  return <main className="auth-page"><div className="auth-side"><strong>CRASS</strong><p>Central de Reserva e Agendamento de Salas e Serviços</p><div className="auth-graphic"><div className="graphic-line"/><div className="graphic-block"/><div className="graphic-block second"/></div><small>Salas organizadas. Reservas sem complicação.</small></div><form className="auth-form" onSubmit={submit}><h1>Entre no CRASS</h1><p>Acesse a agenda e encontre o espaço certo para sua reunião.</p><label>E-mail<input type="email" required autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} /></label><label>Senha<input type="password" required autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} /></label><label>Código de verificação <span className="muted">se ativado</span><input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={e => setCode(e.target.value)} /></label>{error && <div className="error" role="alert">{error}</div>}<button className="button primary wide" disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button></form></main>;
}

export function ChangePassword({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState(''); const [next, setNext] = useState('');
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { await api('/auth/password', json('POST', { current_password: current, new_password: next })); onDone(); }
    catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  return <main className="auth-page simple"><form className="auth-form" onSubmit={submit}><h1>Crie sua senha</h1><p>Troque a senha temporária antes de usar o CRASS.</p><label>Senha temporária<input type="password" required value={current} onChange={e => setCurrent(e.target.value)} /></label><label>Nova senha <span className="muted">mínimo 12 caracteres</span><input type="password" required minLength={12} value={next} onChange={e => setNext(e.target.value)} /></label>{error && <div className="error" role="alert">{error}</div>}<button className="button primary wide" disabled={busy}>{busy ? 'Salvando…' : 'Salvar nova senha'}</button></form></main>;
}
