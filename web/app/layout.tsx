import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'CRASS — Salas e Serviços', description: 'Central de Reserva e Agendamento de Salas e Serviços' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
