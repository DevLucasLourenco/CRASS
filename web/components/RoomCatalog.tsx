'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { api, json, message, zonedLocalToIso } from '@/lib/api';
import type { Building, Dashboard, Room, User } from '@/lib/types';
import Icon from './Icon';
import RoomRulesEditor from './RoomRules';

type Props = { user: User; toast: (text: string) => void; go: (path: string) => void };

export default function RoomCatalog({ user, toast, go }: Props) {
  const elevated = user.role !== 'user';
  const [rooms, setRooms] = useState<Room[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [zone, setZone] = useState('America/Sao_Paulo');
  const [reload, setReload] = useState(0);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [filterBuilding, setFilterBuilding] = useState('');
  const [filterFloor, setFilterFloor] = useState('');
  const [filterFeature, setFilterFeature] = useState('');
  const [filterCapacity, setFilterCapacity] = useState('');
  const [day, setDay] = useState('');
  const [start, setStart] = useState('10:00');
  const [end, setEnd] = useState('11:00');
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [editing, setEditing] = useState<Room | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formBuilding, setFormBuilding] = useState('');
  const [name, setName] = useState('');
  const [floor, setFloor] = useState('');
  const [location, setLocation] = useState('');
  const [capacity, setCapacity] = useState(8);
  const [features, setFeatures] = useState('');
  const [approval, setApproval] = useState(false);
  const [active, setActive] = useState(true);
  const [photoIndexes, setPhotoIndexes] = useState<Record<string, number>>({});
  const [newBuilding, setNewBuilding] = useState('');
  const [newAddress, setNewAddress] = useState('');

  useEffect(() => {
    setQuery(new URLSearchParams(window.location.search).get('q') || '');
    api<Dashboard>('/dashboard').then(data => setZone(data.timezone)).catch(() => {});
    api<Building[]>('/buildings').then(setBuildings).catch(error => setError(message(error)));
  }, []);

  useEffect(() => {
    let current = true;
    let path = '/rooms';
    if (day && start && end) {
      try {
        const params = new URLSearchParams({
          starts_at: zonedLocalToIso(day, start, zone),
          ends_at: zonedLocalToIso(day, end, zone),
        });
        path += `?${params}`;
      } catch {
        setError('Confira a data e o horário da consulta.');
        return;
      }
    }
    api<Room[]>(path).then(items => { if (current) { setRooms(items); setError(''); } })
      .catch(error => { if (current) setError(message(error)); });
    return () => { current = false; };
  }, [day, start, end, zone, reload]);

  const floors = useMemo(() => [...new Set(rooms.map(room => room.floor).filter(Boolean))].sort(), [rooms]);
  const resources = useMemo(() => [...new Set(rooms.flatMap(room => room.features))].sort(), [rooms]);
  const filtered = rooms.filter(room =>
    (!query || `${room.name} ${room.building_name} ${room.floor} ${room.location} ${room.features.join(' ')}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())) &&
    (!filterBuilding || room.building_id === filterBuilding) &&
    (!filterFloor || room.floor === filterFloor) &&
    (!filterFeature || room.features.includes(filterFeature)) &&
    (!filterCapacity || room.capacity >= Number(filterCapacity)) &&
    (!onlyAvailable || !day || room.available === true));

  function openForm(room: Room | null) {
    setEditing(room);
    setFormBuilding(room?.building_id || buildings[0]?.id || '');
    setName(room?.name || '');
    setFloor(room?.floor || '');
    setLocation(room?.location || '');
    setCapacity(room?.capacity || 8);
    setFeatures(room?.features.join(', ') || '');
    setApproval(room?.approval_required || false);
    setActive(room?.active ?? true);
    setFormOpen(true);
  }

  async function saveRoom(event: FormEvent) {
    event.preventDefault();
    try {
      const body = { building_id: formBuilding, name, floor, location, capacity,
        features: features.split(',').map(value => value.trim()).filter(Boolean),
        ...(user.role === 'admin' ? { approval_required: approval } : {}), active };
      if (editing) await api(`/rooms/${editing.id}`, json('PATCH', body));
      else await api('/rooms', json('POST', body));
      setFormOpen(false);
      setReload(value => value + 1);
      toast(editing ? 'Sala atualizada.' : 'Sala cadastrada.');
    } catch (error) { setError(message(error)); }
  }

  async function addBuilding(event: FormEvent) {
    event.preventDefault();
    try {
      const created = await api<Building>('/buildings', json('POST', { name: newBuilding, address: newAddress }));
      setBuildings(items => [...items, created].sort((a, b) => a.name.localeCompare(b.name)));
      setFormBuilding(created.id);
      setNewBuilding('');
      setNewAddress('');
      toast('Prédio cadastrado.');
    } catch (error) { setError(message(error)); }
  }

  async function upload(roomId: string, file: File) {
    const body = new FormData();
    body.append('file', file);
    try {
      const updated = await api<Room>(`/rooms/${roomId}/photo`, { method: 'POST', body });
      setEditing(updated);
      setReload(value => value + 1);
      toast('Foto atualizada.');
    } catch (error) { setError(message(error)); }
  }

  function reserve(room: Room) {
    const params = new URLSearchParams({ room: room.id });
    if (day) { params.set('day', day); params.set('start', start); params.set('end', end); }
    go(`/reservas/nova?${params}`);
  }

  return <div className="view">
    <div className="view-heading"><h2>Catálogo de salas</h2>{elevated && <button className="button primary" onClick={() => openForm(null)}><Icon name="plus"/> Nova sala</button>}</div>
    <div className="toolbar">
      <label>Buscar<input placeholder="Sala, andar ou recurso" value={query} onChange={event => setQuery(event.target.value)}/></label>
      <label>Prédio<select value={filterBuilding} onChange={event => setFilterBuilding(event.target.value)}><option value="">Todos</option>{buildings.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label>Andar<select value={filterFloor} onChange={event => setFilterFloor(event.target.value)}><option value="">Todos</option>{floors.map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Capacidade mínima<input type="number" min={1} value={filterCapacity} onChange={event => setFilterCapacity(event.target.value)}/></label>
      <label>Recurso<select value={filterFeature} onChange={event => setFilterFeature(event.target.value)}><option value="">Todos</option>{resources.map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Data<input type="date" value={day} onChange={event => setDay(event.target.value)}/></label>
      {day && <><label>Início<input type="time" value={start} onChange={event => setStart(event.target.value)}/></label><label>Fim<input type="time" value={end} onChange={event => setEnd(event.target.value)}/></label></>}
      <label className="check-row"><input type="checkbox" checked={onlyAvailable} disabled={!day} onChange={event => setOnlyAvailable(event.target.checked)}/> Somente disponíveis</label>
    </div>
    {error && <div className="error" role="alert">{error}</div>}
    {elevated && formOpen && <form className="panel form-panel" onSubmit={saveRoom}>
      <h3>{editing ? `Editar ${editing.name}` : 'Nova sala'}</h3>
      <div className="form-grid three">
        <label>Prédio<select required value={formBuilding} onChange={event => setFormBuilding(event.target.value)}><option value="">Selecione</option>{buildings.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Nome<input required minLength={2} value={name} onChange={event => setName(event.target.value)}/></label>
        <label>Andar<input value={floor} onChange={event => setFloor(event.target.value)}/></label>
        <label>Localização<input value={location} onChange={event => setLocation(event.target.value)}/></label>
        <label>Capacidade<input type="number" min={1} required value={capacity} onChange={event => setCapacity(Number(event.target.value))}/></label>
        <label>Recursos <span className="muted">separados por vírgula</span><input value={features} onChange={event => setFeatures(event.target.value)}/></label>
      </div>
      {user.role === 'admin' && <label className="check-row"><input type="checkbox" checked={approval} onChange={event => setApproval(event.target.checked)}/> Reservas exigem aprovação</label>}
      <label className="check-row"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)}/> Sala ativa</label>
      <div className="form-actions"><button className="button primary">Salvar sala</button><button type="button" className="button subtle" onClick={() => setFormOpen(false)}>Cancelar</button></div>
      {editing && <div className="room-photo-manager"><label className="upload-label">Fotos da sala<input type="file" accept="image/*" multiple onChange={async event => { for (const file of Array.from(event.target.files || [])) await upload(editing.id, file); }}/></label><div className="room-photo-list">{editing.photos.map(path => <img key={path} src={path} alt={`Foto da sala ${editing.name}`}/>)}</div></div>}
    </form>}
    {user.role === 'admin' && <form className="inline-building" onSubmit={addBuilding}><label>Novo prédio<input required minLength={2} value={newBuilding} onChange={event => setNewBuilding(event.target.value)} placeholder="Nome do prédio"/></label><label>Endereço<input value={newAddress} onChange={event => setNewAddress(event.target.value)}/></label><button className="button subtle">Adicionar prédio</button></form>}
    <div className="room-grid">{filtered.map(room => { const photos = room.photos.length ? room.photos : room.photo ? [room.photo] : []; const index = photoIndexes[room.id] === undefined ? photos.length - 1 : photoIndexes[room.id] % photos.length; return <article className="room-card" key={room.id}>
      <div className="room-card-media">{photos.length ? <img src={photos[index]} alt={`Foto ${index + 1} de ${photos.length} da ${room.name}`}/> : <div className="room-photo"><Icon name="room" size={42}/></div>}{photos.length > 1 && <div className="room-photo-controls"><button type="button" aria-label={`Foto anterior da ${room.name}`} onClick={() => setPhotoIndexes(previous => ({ ...previous, [room.id]: (index - 1 + photos.length) % photos.length }))}>‹</button><span>{index + 1}/{photos.length}</span><button type="button" aria-label={`Próxima foto da ${room.name}`} onClick={() => setPhotoIndexes(previous => ({ ...previous, [room.id]: (index + 1) % photos.length }))}>›</button></div>}</div>
      <div className="room-card-body"><div className="room-card-title"><h3>{room.name}</h3><span className={`status ${!room.active || (day && !room.available) ? 'unavailable' : 'available'}`}>{!room.active ? 'Indisponível' : day ? room.available ? 'Disponível' : 'Ocupada ou fora das regras' : 'Ativa'}</span></div>
        <p>{room.building_name} · {room.floor || 'Andar não informado'}</p>
        <p>{room.capacity} pessoas · {room.features.join(', ') || 'Sem recursos cadastrados'}</p>
        {room.approval_required && <small>Aprovação necessária</small>}
        <div className="room-card-actions"><button className="button primary small" disabled={!room.active || Boolean(day && !room.available)} onClick={() => reserve(room)}>Reservar</button>{elevated && <button className="button subtle small" onClick={() => openForm(room)}>Editar</button>}</div>
      </div>
    </article>; })}</div>
    {!filtered.length && <p className="empty">Nenhuma sala encontrada.</p>}
    {user.role === 'admin' && <RoomRulesEditor rooms={rooms} onSaved={() => setReload(value => value + 1)} toast={toast}/>}
  </div>;
}
