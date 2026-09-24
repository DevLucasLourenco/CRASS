'use client';

import { useState, type FormEvent } from 'react';
import { api, json, message } from '@/lib/api';
import type { User } from '@/lib/types';

export default function AccountView({ user, refreshUser, toast }: {
  user: User; refreshUser: () => Promise<void>; toast: (text: string) => void;
}) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [secret, setSecret] = useState('');
  const [code, setCode] = useState('');
  const [recovery, setRecovery] = useState<string[]>([]);
  const [error, setError] = useState('');

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    try {
      await api('/auth/password', json('POST', { current_password: current, new_password: next }));
      setCurrent(''); setNext(''); setError(''); toast('Senha atualizada.');
    } catch (cause) { setError(message(cause)); }
  }

  async function setup() {
    try {
      const result = await api<{ secret: string }>('/auth/totp/setup', { method: 'POST' });
      setSecret(result.secret); setError('');
    } catch (cause) { setError(message(cause)); }
  }

  async function confirm() {
    try {
      const result = await api<{ recovery_codes: string[] }>('/auth/totp/confirm', json('POST', { code }));
      setRecovery(result.recovery_codes); setSecret(''); setCode(''); setError('');
      await refreshUser(); toast('Verificação em duas etapas ativada.');
    } catch (cause) { setError(message(cause)); }
  }

  async function disable() {
    try {
      await api('/auth/totp/disable', json('POST', { code }));
      setCode(''); setError(''); await refreshUser(); toast('Verificação em duas etapas desativada.');
    } catch (cause) { setError(message(cause)); }
  }

  return <div className="view"><div className="view-heading"><h2>Minha conta</h2></div>
    {error && <div className="error" role="alert">{error}</div>}
    <div className="account-grid">
      <section className="panel form-panel"><h3>Dados de acesso</h3><p><strong>{user.name}</strong><br/>{user.email}</p>
        <form className="stack" onSubmit={changePassword}><label>Senha atual<input type="password" autoComplete="current-password" required value={current} onChange={event => setCurrent(event.target.value)}/></label><label>Nova senha, mínimo 12 caracteres<input type="password" autoComplete="new-password" required minLength={12} value={next} onChange={event => setNext(event.target.value)}/></label><button className="button primary">Alterar senha</button></form>
      </section>
      <section className="panel form-panel"><h3>Verificação em duas etapas</h3><p className="section-help">Use um aplicativo autenticador TOTP. Guarde os códigos de recuperação fora do CRASS.</p>
        {!user.totp_enabled && !secret && <button className="button subtle" onClick={setup}>Configurar TOTP</button>}
        {secret && <div className="stack"><p>Cadastre esta chave no autenticador:</p><code>{secret}</code><label>Código de 6 dígitos<input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={event => setCode(event.target.value)}/></label><button className="button primary" onClick={confirm}>Ativar verificação</button></div>}
        {user.totp_enabled && <div className="stack"><p>Verificação ativa.</p><label>Código atual para desativar<input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={event => setCode(event.target.value)}/></label><button className="button subtle" onClick={disable}>Desativar TOTP</button></div>}
        {recovery.length > 0 && <div className="warning" role="status"><strong>Códigos de recuperação, exibidos uma vez:</strong><code>{recovery.join(' · ')}</code></div>}
      </section>
    </div>
  </div>;
}
