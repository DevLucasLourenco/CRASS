'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { api, json, message } from '@/lib/api';

type Channel = { available: boolean; enabled: boolean; provider?: string | null };
type CalendarRoom = { room_id: string; room_name: string; building_name: string; calendar_id: string | null };
const channelLabels: Record<string, string> = { sms: 'SMS', email: 'E-mail', whatsapp: 'WhatsApp' };

export default function IntegrationsView() {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [calendarRooms, setCalendarRooms] = useState<CalendarRoom[]>([]);
  const [selectedRoom, setSelectedRoom] = useState('');
  const [calendarId, setCalendarId] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api<Record<string, Channel>>('/integrations').then(data => {
      setDrafts(Object.fromEntries(Object.entries(channelLabels).map(([key]) => [key, data[key]?.provider || ''])));
    }).catch(reason => setError(message(reason)));
    api<CalendarRoom[]>('/integrations/calendar/rooms').then(data => {
      setCalendarRooms(data);
      if (data.length) { setSelectedRoom(data[0].room_id); setCalendarId(data[0].calendar_id || ''); }
    }).catch(reason => setError(message(reason)));
  }, []);

  async function saveProvider(event: FormEvent, channel: string) {
    event.preventDefault(); setError(''); setFeedback('');
    try {
      await api<Channel>(`/integrations/channels/${channel}`, json('PATCH', { provider: drafts[channel] || null }));
      setFeedback(`Preferência de ${channelLabels[channel]} salva. O envio continua desativado.`);
    } catch (reason) { setError(message(reason)); }
  }

  async function saveCalendar(event: FormEvent) {
    event.preventDefault(); setError(''); setFeedback('');
    try {
      const updated = await api<{ calendar_id: string | null }>(`/integrations/calendar/rooms/${selectedRoom}`,
        json('PATCH', { calendar_id: calendarId || null }));
      setCalendarRooms(previous => previous.map(room => room.room_id === selectedRoom ? { ...room, calendar_id: updated.calendar_id } : room));
      setFeedback('Vínculo futuro salvo. Nenhuma sincronização foi ativada.');
    } catch (reason) { setError(message(reason)); }
  }

  function chooseRoom(roomId: string) {
    setSelectedRoom(roomId);
    setCalendarId(calendarRooms.find(room => room.room_id === roomId)?.calendar_id || '');
  }

  return <div className="view">
    <div className="view-heading"><h2>Comunicação e integrações</h2></div>
    <p className="section-help">Configure as referências para uma ativação futura. SMS, e-mail, WhatsApp e Google Calendar ainda não enviam nem sincronizam dados.</p>
    {error && <div className="error" role="alert">{error}</div>}
    {feedback && <div className="warning" role="status">{feedback}</div>}
    <div className="integration-list">
      <article className="panel integration-row"><div><h3>Notificações no CRASS</h3><p>Avisos e lembretes dentro do sistema.</p></div><span className="status available">Ativo</span></article>
      {Object.entries(channelLabels).map(([key, label]) => <form className="panel integration-row" key={key} onSubmit={event => saveProvider(event, key)}>
        <div><h3>{label}</h3><p>{key === 'whatsapp' ? 'Futuros avisos automáticos, sem conversas ou comandos.' : 'Futuro canal de envio configurável.'}</p><label>Provedor planejado<input value={drafts[key] || ''} onChange={event => setDrafts(previous => ({ ...previous, [key]: event.target.value }))} maxLength={80} placeholder="Nome do provedor"/></label></div>
        <div className="stack"><span className="status unavailable">Desativado</span><button className="button subtle small">Salvar referência</button></div>
      </form>)}
      <form className="panel form-panel" onSubmit={saveCalendar}><h3>Google Calendar por sala</h3><p className="section-help">Registre o identificador do calendário que será usado após a conexão OAuth. O CRASS continua como agenda principal.</p>
        <div className="form-grid two"><label>Sala<select value={selectedRoom} onChange={event => chooseRoom(event.target.value)} required>{calendarRooms.map(room => <option key={room.room_id} value={room.room_id}>{room.building_name} · {room.room_name}</option>)}</select></label><label>ID do calendário<input value={calendarId} onChange={event => setCalendarId(event.target.value)} maxLength={255} placeholder="ID do calendário"/></label></div>
        <button className="button subtle" disabled={!selectedRoom}>Salvar vínculo futuro</button>
      </form>
    </div>
  </div>;
}
