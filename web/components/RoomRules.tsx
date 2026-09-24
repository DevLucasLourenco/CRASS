'use client';

import { useState, type FormEvent } from 'react';
import { api, json, message } from '@/lib/api';
import type { Room } from '@/lib/types';

type Rule = 'opening_time' | 'closing_time' | 'min_notice_minutes' | 'max_duration_minutes' | 'cancel_notice_minutes';
const fields: { key: Rule; label: string; type: string; min?: number }[] = [
  { key: 'opening_time', label: 'Abertura', type: 'time' },
  { key: 'closing_time', label: 'Fechamento', type: 'time' },
  { key: 'min_notice_minutes', label: 'Antecedência mínima (min)', type: 'number', min: 0 },
  { key: 'max_duration_minutes', label: 'Duração máxima (min)', type: 'number', min: 1 },
  { key: 'cancel_notice_minutes', label: 'Prazo para cancelar (min)', type: 'number', min: 0 },
];

export default function RoomRulesEditor({ rooms, onSaved, toast }: {
  rooms: Room[]; onSaved: () => void; toast: (text: string) => void;
}) {
  const [roomId, setRoomId] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [active, setActive] = useState(true);
  const [error, setError] = useState('');

  function select(id: string) {
    setRoomId(id);
    const room = rooms.find(item => item.id === id);
    setValues(Object.fromEntries(fields.map(field => [field.key, String(room?.rules?.[field.key] ?? '')])));
    setActive(room?.active ?? true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!roomId) return;
    const rules = Object.fromEntries(fields.filter(field => values[field.key] !== '' && values[field.key] !== undefined)
      .map(field => [field.key, field.type === 'number' ? Number(values[field.key]) : values[field.key]]));
    try {
      await api(`/rooms/${roomId}`, json('PATCH', { rules, active }));
      setError(''); toast('Regras da sala salvas.'); onSaved();
    } catch (cause) { setError(message(cause)); }
  }

  return <form className="panel form-panel" onSubmit={save}><h3>Regras por sala</h3>
    <p className="section-help">Deixe um campo vazio para usar a regra geral da instalação.</p>
    {error && <div className="error" role="alert">{error}</div>}
    <label>Sala<select value={roomId} onChange={event => select(event.target.value)} required><option value="">Selecione</option>{rooms.map(room => <option key={room.id} value={room.id}>{room.building_name} · {room.name}</option>)}</select></label>
    {roomId && <><div className="form-grid three">{fields.map(field => <label key={field.key}>{field.label}<input type={field.type} min={field.min} value={values[field.key] ?? ''} onChange={event => setValues(previous => ({ ...previous, [field.key]: event.target.value }))}/></label>)}</div>
      <label className="check-row"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)}/> Sala ativa para novas reservas</label>
      <button className="button primary">Salvar regras da sala</button></>}
  </form>;
}
