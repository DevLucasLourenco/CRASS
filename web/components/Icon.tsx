type Name = 'home' | 'calendar' | 'booking' | 'room' | 'chart' | 'settings' | 'chevron' | 'plus' | 'search' | 'bell' | 'clock' | 'alert' | 'menu' | 'close' | 'users' | 'user' | 'check' | 'logout';

const paths: Record<Name, React.ReactNode> = {
  home: <><path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-7h6v7"/></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/></>,
  booking: <><path d="M6 3h9l3 3v15H6z"/><path d="M9 11h6M9 15h6"/></>,
  room: <><path d="M4 21V4h16v17M2 21h20M8 8h2M14 8h2M8 12h2M14 12h2M10 21v-5h4v5"/></>,
  chart: <><path d="M4 20V12M10 20V5M16 20v-9M22 20H2"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="m10 2-.5 2.1-2 .9-1.9-1.1-2 2 1.1 1.9-.9 2L2 10v4l2.1.5.9 2-1.1 1.9 2 2 1.9-1.1 2 .9.5 2.1h4l.5-2.1 2-.9 1.9 1.1 2-2-1.1-1.9.9-2L22 14v-4l-2.1-.5-.9-2 1.1-1.9-2-2-1.9 1.1-2-.9L14 2z"/></>,
  chevron: <path d="m6 9 6 6 6-6"/>,
  plus: <path d="M12 4v16M4 12h16"/>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  alert: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
  close: <path d="M5 5l14 14M19 5 5 19"/>,
  users: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M17 14a5 5 0 0 1 4 5v1"/></>,
  user: <><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></>,
  check: <path d="m4 12 5 5L20 6"/>,
  logout: <><path d="M9 4H4v16h5M14 7l5 5-5 5M19 12H8"/></>,
};

export default function Icon({ name, size = 18 }: { name: Name; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
