'use client';

import { useEffect, useState } from 'react';
import { api, message, setCsrf } from '@/lib/api';
import type { User } from '@/lib/types';
import { Login, ChangePassword } from './Auth';
import Shell from './Shell';
import DashboardView from './Dashboard';
import BookingForm from './BookingForm';
import RoomCatalog from './RoomCatalog';
import AccountView from './Account';
import AuditView from './Audit';
import { AgendaView, BookingsView, BlocksView, IncidentsView, ReportsView, UsersView, RulesView, IntegrationsView, NoticesView } from './Views';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [location, setLocation] = useState('/');
  const path = location.split('?')[0];
  const [toast, setToast] = useState('');
  useEffect(() => {
    setLocation(window.location.pathname + window.location.search);
    const pop = () => setLocation(window.location.pathname + window.location.search);
    window.addEventListener('popstate', pop);
    api<{ user: User; csrf: string }>('/auth/me').then(result => { setCsrf(result.csrf); setUser(result.user); }).catch(() => {}).finally(() => setLoading(false));
    return () => window.removeEventListener('popstate', pop);
  }, []);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 5000); return () => clearTimeout(t); }, [toast]);
  function go(target: string) { window.history.pushState({}, '', target); setLocation(new URL(target, window.location.origin).pathname + new URL(target, window.location.origin).search); window.scrollTo({ top: 0 }); }
  async function refreshUser() { const result = await api<{ user: User; csrf: string }>('/auth/me'); setCsrf(result.csrf); setUser(result.user); }
  async function logout() { try { await api('/auth/logout', { method: 'POST' }); } catch { /* Clear local UI regardless. */ } setUser(null); go('/'); }
  if (loading) return <div className="boot">Carregando CRASS…</div>;
  if (!user) return <Login onLogin={setUser} />;
  if (user.must_change_password) return <ChangePassword onDone={() => refreshUser().catch(e => setToast(message(e)))} />;
  let content: React.ReactNode;
  if (path === '/reservas/nova') content = <BookingForm user={user} go={go} toast={setToast} />;
  else if (path.startsWith('/reservas')) content = <BookingsView key={location} user={user} toast={setToast} go={go} selectedId={path.split('/')[2]} />;
  else if (path === '/agenda') content = <AgendaView key={location} go={go} calendar={new URLSearchParams(location.split('?')[1] || '').get('view') === 'calendar'} />;
  else if (path === '/salas') content = <RoomCatalog user={user} toast={setToast} go={go} />;
  else if (path === '/bloqueios') content = <BlocksView user={user} toast={setToast} />;
  else if (path === '/ocorrencias') content = <IncidentsView user={user} toast={setToast} go={go} />;
  else if (path === '/relatorios') content = <ReportsView />;
  else if (path === '/usuarios') content = <UsersView user={user} toast={setToast} />;
  else if (path === '/regras') content = <RulesView user={user} toast={setToast} />;
  else if (path === '/integracoes' || path === '/comunicacao') content = <IntegrationsView />;
  else if (path === '/avisos') content = <NoticesView go={go} />;
  else if (path === '/conta') content = <AccountView user={user} refreshUser={refreshUser} toast={setToast} />;
  else if (path === '/historico') content = <AuditView />;
  else content = <DashboardView user={user} go={go} />;
  return <Shell user={user} path={path} location={location} go={go} logout={logout}>{content}{toast && <div className="toast" role="status" onClick={() => setToast('')}>{toast}</div>}</Shell>;
}
