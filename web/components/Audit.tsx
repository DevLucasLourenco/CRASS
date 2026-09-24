'use client';

import { useEffect, useState } from 'react';
import { api, dateTime, message } from '@/lib/api';
import type { User } from '@/lib/types';

type Entry = { id: string; actor_id: string | null; action: string; subject: string; subject_id: string; detail: Record<string, unknown>; created_at: string };
const labels: Record<string, string> = {
  user_created: 'Conta criada', user_updated: 'Conta alterada', password_reset: 'Senha redefinida',
  settings_updated: 'Regras alteradas', building_created: 'Prédio cadastrado', room_created: 'Sala cadastrada',
  room_updated: 'Sala alterada', booking_created: 'Reserva criada', booking_updated: 'Reserva alterada',
  booking_approved: 'Reserva aprovada', booking_rejected: 'Reserva rejeitada', booking_cancelled: 'Reserva cancelada',
  no_show: 'Ausência registrada', booking_ended: 'Reunião encerrada', series_created: 'Série criada',
  series_changed: 'Série alterada', series_cancelled: 'Série cancelada', block_created: 'Sala bloqueada',
  block_removed: 'Bloqueio removido', incident_created: 'Ocorrência registrada', incident_updated: 'Ocorrência alterada',
};

export default function AuditView() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    api<Entry[]>('/audit').then(setEntries).catch(cause => setError(message(cause)));
    api<User[]>('/users').then(setUsers).catch(() => {});
  }, []);
  return <div className="view"><div className="view-heading"><h2>Histórico de ações</h2></div>
    {error && <div className="error" role="alert">{error}</div>}
    <div className="panel table-wrap"><table><thead><tr><th>Data</th><th>Ação</th><th>Responsável</th><th>Referência</th></tr></thead>
      <tbody>{entries.map(entry => <tr key={entry.id}><td>{dateTime(entry.created_at)}</td><td>{labels[entry.action] || entry.action}</td><td>{users.find(user => user.id === entry.actor_id)?.name || 'Sistema'}</td><td>{entry.subject} · {entry.subject_id.slice(0, 8)}</td></tr>)}</tbody></table>
      {!entries.length && <p className="empty">Nenhuma ação registrada.</p>}
    </div>
  </div>;
}
