'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { api, dateTime, json, message, zonedLocalToIso } from '@/lib/api';
import type { Building, Dashboard, Room, User } from '@/lib/types';
import Icon from './Icon';

const resources = ['Projetor', 'TV / Monitor', 'Videoconferência', 'Quadro branco', 'Som', 'Microfone'];
function initialParam(name: string) { return typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get(name); }

export default function BookingForm({ user, go, toast }: { user: User; go: (path: string) => void; toast: (text: string) => void }) {
  const [zone, setZone] = useState('America/Sao_Paulo');
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [day, setDay] = useState(() => initialParam('day') || new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()));
  const [start, setStart] = useState(() => initialParam('start') || '10:00'); const [end, setEnd] = useState(() => initialParam('end') || '11:00');
  const [attendees, setAttendees] = useState(4); const [building, setBuilding] = useState('');
  const [features, setFeatures] = useState<string[]>([]);
  const [selected, setSelected] = useState(() => typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('room') || '' : '');
  const [title, setTitle] = useState(''); const [description, setDescription] = useState('');
  const [frequency, setFrequency] = useState('none'); const [interval, setInterval] = useState(1);
  const [until, setUntil] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [createdSeriesId, setCreatedSeriesId] = useState(''); const [skipped, setSkipped] = useState<string[]>([]);
  useEffect(() => { api<Dashboard>('/dashboard').then(data => { setZone(data.timezone); if (!initialParam('day')) setDay(data.date); }).catch(() => {}); api<Building[]>('/buildings').then(setBuildings).catch(() => {}); }, []);
  const times = useMemo(() => { try { if (!day || !start || !end) return null; return { starts_at: zonedLocalToIso(day, start, zone), ends_at: zonedLocalToIso(day, end, zone) }; } catch { return null; } }, [day, start, end, zone]);
  useEffect(() => { if (!times || start >= end) return; const search = new URLSearchParams({ capacity: String(attendees), starts_at: times.starts_at, ends_at: times.ends_at }); if (building) search.set('building_id', building); api<Room[]>(`/rooms?${search}`).then(setRooms).catch(() => setRooms([])); }, [times, attendees, building, start, end]);
  const matching = rooms.filter(room => features.every(feature => room.features.includes(feature)));
  const room = rooms.find(item => item.id === selected);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    if (!room || !times) { setError('Selecione uma sala disponível.'); return; }
    setBusy(true);
    try {
      const base = { room_id: room.id, title, description, attendees, ...times };
      if (frequency === 'none') {
        const result = await api<{ id: string; status: string }>('/bookings', json('POST', base));
        toast(result.status === 'pending' ? 'Solicitação criada e enviada para aprovação.' : 'Reserva confirmada.');
        go(`/reservas/${result.id}`);
      } else {
        const result = await api<{ id: string; created: number; skipped: string[] }>('/series', json('POST', { ...base, frequency, interval, weekdays: [], until: until ? zonedLocalToIso(until, end, zone) : null }));
        toast(`Série criada: ${result.created} datas reservadas${result.skipped.length ? `, ${result.skipped.length} datas em conflito` : ''}.`);
        if (result.skipped.length) { setCreatedSeriesId(result.id); setSkipped(result.skipped); }
        else go(`/reservas?series=${result.id}`);
      }
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  if (createdSeriesId) return <section className="panel form-panel"><h2>Série criada</h2><p>As datas livres foram reservadas. As seguintes datas estavam ocupadas e foram puladas:</p><ul>{skipped.map(value => <li key={value}>{dateTime(value, zone)}</li>)}</ul><button className="button primary" onClick={() => go(`/reservas?series=${createdSeriesId}`)}>Ver reservas da série</button></section>;
  return <form className="booking-layout" onSubmit={submit}><section className="panel booking-main"><div className="booking-step"><span>1</span><strong>Detalhes da reserva</strong><i/><span className="future">2</span><strong className="muted">Confirmar</strong></div><div className="form-section"><h2><Icon name="calendar" size={20}/> Quando será a reunião?</h2><div className="form-grid five"><label>Data<input type="date" required value={day} onChange={e => setDay(e.target.value)}/></label><label>Hora de início<input type="time" required value={start} onChange={e => setStart(e.target.value)}/></label><label>Hora de término<input type="time" required value={end} onChange={e => setEnd(e.target.value)}/></label><label>Número de pessoas<input type="number" required min={1} value={attendees} onChange={e => setAttendees(Number(e.target.value))}/></label></div></div><div className="form-section"><h2><Icon name="room" size={20}/> Em qual prédio?</h2><div className="form-grid two"><label>Prédio<select value={building} onChange={e => setBuilding(e.target.value)}><option value="">Todos os prédios</option>{buildings.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div></div><div className="form-section"><h2><Icon name="users" size={20}/> Recursos necessários</h2><p className="section-help">Selecione os recursos que a sala deve possuir.</p><div className="feature-list">{resources.map(feature => <label className={`feature-option ${features.includes(feature) ? 'selected' : ''}`} key={feature}><input type="checkbox" checked={features.includes(feature)} onChange={e => setFeatures(prev => e.target.checked ? [...prev, feature] : prev.filter(x => x !== feature))}/>{feature}</label>)}</div></div><div className="form-section room-results"><div className="section-heading"><h2><Icon name="room" size={20}/> Salas disponíveis</h2><span>{matching.filter(x => x.available).length} salas encontradas</span></div><div className="table-wrap"><table><thead><tr><th></th><th>Sala</th><th>Localização</th><th>Capacidade</th><th>Recursos</th><th>Disponibilidade</th></tr></thead><tbody>{matching.length ? matching.map(item => <tr key={item.id} className={selected === item.id ? 'selected-row' : ''} onClick={() => setSelected(item.id)}><td><input type="radio" checked={selected === item.id} onChange={() => setSelected(item.id)} disabled={!item.available} aria-label={`Selecionar ${item.name}`}/></td><td><strong>{item.name}</strong></td><td>{item.building_name}{item.floor && ` · ${item.floor}`}</td><td>{item.capacity} pessoas</td><td>{item.features.slice(0, 3).join(', ') || '—'}</td><td><span className={`status ${item.available ? 'available' : 'unavailable'}`}>{item.available ? 'Disponível' : 'Ocupada'}</span></td></tr>) : <tr><td colSpan={6} className="empty-cell">Nenhuma sala corresponde aos filtros.</td></tr>}</tbody></table></div></div></section><aside className="panel booking-summary"><h2><Icon name="booking" size={21}/> Resumo da reserva</h2><p className="section-help">Confira as informações antes de confirmar.</p><div className="selected-room">{room ? <><strong>{room.name}</strong><span>{room.building_name}{room.floor && ` · ${room.floor}`}</span><span>Capacidade: {room.capacity} pessoas</span><span>{room.features.join(', ')}</span></> : <span>Selecione uma sala disponível.</span>}</div><label>Título da reunião<input required minLength={2} maxLength={200} value={title} onChange={e => setTitle(e.target.value)} placeholder="Ex.: Reunião de equipe"/></label><label>Descrição <span className="muted">opcional</span><textarea rows={3} value={description} onChange={e => setDescription(e.target.value)} placeholder="Contexto da reunião"/></label><div className="summary-organizer"><small>Organizador</small><strong>{user.name}</strong><span>{user.email}</span></div><label>Recorrência<select value={frequency} onChange={e => setFrequency(e.target.value)}><option value="none">Não se repete</option><option value="daily">Diariamente</option><option value="weekly">Semanalmente</option><option value="monthly">Mensalmente</option></select></label>{frequency !== 'none' && <div className="form-grid two"><label>Repetir a cada<input type="number" min={1} max={52} value={interval} onChange={e => setInterval(Number(e.target.value))}/></label><label>Data final <span className="muted">opcional</span><input type="date" value={until} onChange={e => setUntil(e.target.value)}/></label></div>}<div className="policy-note"><strong>Política de uso</strong><span>A reserva seguirá as regras da sala. Algumas salas exigem aprovação. Datas em conflito de uma série serão listadas e puladas.</span></div>{error && <div className="error" role="alert">{error}</div>}<button className="button primary wide" type="submit" disabled={busy || !room?.available}>{busy ? 'Salvando…' : frequency === 'none' ? 'Confirmar reserva' : 'Criar série'}</button><button className="button subtle wide" type="button" onClick={() => go('/')}>Cancelar</button></aside></form>;
}
