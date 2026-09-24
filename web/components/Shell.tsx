'use client';

import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { api } from '@/lib/api';
import type { Notice, User } from '@/lib/types';
import Icon from './Icon';

type Props = { user: User; path: string; location: string; go: (path: string) => void; logout: () => void; children: ReactNode };
const titles: Record<string, string> = { '/': 'Visão geral', '/agenda': 'Agenda', '/reservas': 'Reservas', '/reservas/nova': 'Nova reserva', '/salas': 'Salas', '/bloqueios': 'Bloqueios', '/ocorrencias': 'Ocorrências', '/relatorios': 'Relatórios', '/usuarios': 'Usuários e perfis', '/regras': 'Regras de reserva', '/integracoes': 'Integrações', '/comunicacao': 'Comunicação', '/avisos': 'Avisos', '/conta': 'Minha conta', '/historico': 'Histórico' };

export default function Shell({ user, path, location, go, logout, children }: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>({ Agenda: true, Reservas: true, Salas: true, Administração: true });
  const [mobile, setMobile] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState('');
  const [unread, setUnread] = useState(0);
  const elevated = user.role !== 'user';
  useEffect(() => { api<Notice[]>('/notifications').then(items => setUnread(items.filter(x => !x.read_at).length)).catch(() => {}); }, [path]);
  function navigate(target: string) { go(target); setMobile(false); }
  function item(label: string, target: string, icon?: Parameters<typeof Icon>[0]['name']) {
    const active = location === target || (target === '/reservas' && path.startsWith('/reservas/') && path !== '/reservas/nova');
    return <button type="button" className={`nav-item ${active ? 'active' : ''} ${icon ? '' : 'child'}`} onClick={() => navigate(target)} aria-current={active ? 'page' : undefined}>{icon && <Icon name={icon} size={19} />}<span>{label}</span></button>;
  }
  function group(label: string, icon: Parameters<typeof Icon>[0]['name'], children: ReactNode) {
    return <div className="nav-group"><button type="button" className="nav-item nav-parent" aria-expanded={open[label]} onClick={() => setOpen(prev => ({ ...prev, [label]: !prev[label] }))}><Icon name={icon} size={19}/><span>{label}</span><span className={`chevron ${open[label] ? 'up' : ''}`}><Icon name="chevron" size={14}/></span></button>{open[label] && <div className="nav-children">{children}</div>}</div>;
  }
  function find(event: FormEvent) { event.preventDefault(); navigate(`/salas?q=${encodeURIComponent(search)}`); }
  const title = titles[path] || (path.startsWith('/reservas/') ? 'Reservas' : 'Visão geral');
  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
    {mobile && <button className="mobile-scrim" onClick={() => setMobile(false)} aria-label="Fechar menu" />}
    <aside className={`sidebar ${mobile ? 'mobile-open' : ''}`}>
      <div className="brand"><div><strong>CRASS</strong><small>Central de Reserva e<br/>Agendamento de Salas e Serviços</small></div><button className="sidebar-toggle" onClick={() => { setCollapsed(!collapsed); setMobile(false); }} aria-label="Recolher barra lateral"><Icon name="chevron" size={16}/></button></div>
      <nav aria-label="Navegação principal">{item('Visão geral', '/', 'home')}{group('Agenda', 'calendar', <>{item('Hoje', '/agenda')}{item('Calendário', '/agenda?view=calendar')}</>)}{group('Reservas', 'booking', <>{item('Minhas reservas', '/reservas?mine=1')}{item('Todas as reservas', '/reservas')}</>)}{group('Salas', 'room', <>{item('Catálogo', '/salas')}{elevated && item('Bloqueios', '/bloqueios')}{item('Ocorrências', '/ocorrencias')}</>)}{elevated && item('Relatórios', '/relatorios', 'chart')}{user.role === 'admin' && group('Administração', 'settings', <>{item('Usuários e perfis', '/usuarios')}{item('Regras de reserva', '/regras')}{item('Integrações', '/integracoes')}{item('Comunicação', '/comunicacao')}{item('Histórico', '/historico')}</>)}{item('Minha conta', '/conta', 'user')}</nav>
      <div className="sidebar-footer"><span>CRASS</span><small>Salas no lugar certo.</small></div>
    </aside>
    <div className="workspace"><header className="topbar"><button className="mobile-menu icon-button" onClick={() => setMobile(true)} aria-label="Abrir menu"><Icon name="menu"/></button><div className="page-title"><h1>{title}</h1><span>{path === '/' ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date()) : 'Central de reserva de salas'}</span></div><form className="global-search" onSubmit={find}><Icon name="search" size={18}/><input aria-label="Buscar salas" placeholder="Buscar salas..." value={search} onChange={e => setSearch(e.target.value)}/></form><button className="button primary top-new" onClick={() => navigate('/reservas/nova')}><Icon name="plus" size={17}/> Nova reserva</button><button className="icon-button notification-trigger" onClick={() => navigate('/avisos')} aria-label={`Avisos${unread ? `, ${unread} não lidos` : ''}`}><Icon name="bell" size={20}/>{unread > 0 && <b>{unread}</b>}</button><div className="account"><span className="avatar">{user.name.split(' ').map(part => part[0]).slice(0, 2).join('').toUpperCase()}</span><span><strong>{user.name}</strong><small>{user.role === 'admin' ? 'Administrador' : user.role === 'manager' ? 'Responsável' : 'Usuário'}</small></span><button className="icon-button" onClick={logout} aria-label="Sair"><Icon name="logout" size={17}/></button></div></header><main className="content">{children}</main></div>
  </div>;
}

