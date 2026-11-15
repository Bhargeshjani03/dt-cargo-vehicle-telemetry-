import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import {
  Activity, AlertTriangle, Boxes, ClipboardList, Gauge, LayoutDashboard,
  MapPinned, Menu, Radio, Route, ShieldCheck, Truck, X,
} from 'lucide-react';
import { useApi } from './api.js';
const OverviewPage = lazy(() => import('./pages/OverviewPage.jsx'));
const AnomalyPage = lazy(() => import('./pages/AnomalyPage.jsx'));
const VehiclePage = lazy(() => import('./pages/VehiclePage.jsx'));
const TrackPage = lazy(() => import('./pages/TrackPage.jsx'));
const DurationPage = lazy(() => import('./pages/DurationPage.jsx'));
const ClustersPage = lazy(() => import('./pages/ClustersPage.jsx'));
const QualityPage = lazy(() => import('./pages/QualityPage.jsx'));
const MethodologyPage = lazy(() => import('./pages/MethodologyPage.jsx'));
const SimulatorPage = lazy(() => import('./pages/SimulatorPage.jsx'));

const groups = [
  { title: 'OPERATIONS', items: [
    { id: 'overview', label: 'Fleet Overview', icon: LayoutDashboard },
    { id: 'anomalies', label: 'Anomaly Monitoring', icon: AlertTriangle },
    { id: 'vehicles', label: 'Vehicle Explorer', icon: Truck },
    { id: 'tracks', label: 'Track Explorer', icon: Activity },
  ] },
  { title: 'ANALYSIS', items: [
    { id: 'duration', label: 'Tour Duration', icon: Gauge },
    { id: 'clusters', label: 'Behaviour Clusters', icon: Boxes },
    { id: 'quality', label: 'Data Quality', icon: ShieldCheck },
    { id: 'methodology', label: 'Model Insights', icon: ClipboardList },
  ] },
  { title: 'SIMULATION', items: [
    { id: 'simulator', label: 'Route Simulator', icon: Route },
  ] },
];

const pageTitles = {
  overview: 'Fleet Overview', anomalies: 'Anomaly Monitoring', vehicles: 'Vehicle Explorer',
  tracks: 'Track Explorer', duration: 'Tour Duration Prediction', clusters: 'Behaviour Clusters',
  quality: 'Data Quality & Insights', methodology: 'Model Insights & Methodology',
  simulator: 'Mission Simulator',
};

export default function App() {
  const [active, setActive] = useState('overview');
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileViewport, setMobileViewport] = useState(() => window.matchMedia('(max-width: 820px)').matches);
  const [vehicleId, setVehicleId] = useState('');
  const [trackId, setTrackId] = useState('');
  const menuToggleRef = useRef(null);
  const health = useApi('/api/health');

  const navigate = (page) => {
    setActive(page);
    setMenuOpen(false);
    if (mobileViewport) window.requestAnimationFrame(() => menuToggleRef.current?.focus());
  };
  const closeMenu = () => {
    setMenuOpen(false);
    if (mobileViewport) window.requestAnimationFrame(() => menuToggleRef.current?.focus());
  };
  const openTrack = (id) => {
    setTrackId(String(id));
    navigate('tracks');
  };
  const openVehicle = (id) => {
    setVehicleId(String(id));
    navigate('vehicles');
  };

  useEffect(() => {
    const media = window.matchMedia('(max-width: 820px)');
    const syncViewport = () => setMobileViewport(media.matches);
    syncViewport();
    media.addEventListener?.('change', syncViewport);
    return () => media.removeEventListener?.('change', syncViewport);
  }, []);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') closeMenu();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [menuOpen, mobileViewport]);

  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion || !('IntersectionObserver' in window)) return undefined;
    document.documentElement.classList.add('scroll-motion');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -20px 0px' });
    const observe = (root) => {
      if (root.matches?.('[data-reveal]')) observer.observe(root);
      root.querySelectorAll?.('[data-reveal]').forEach((node) => observer.observe(node));
    };
    const main = document.getElementById('main-content');
    if (main) observe(main);
    const mutations = new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => { if (node.nodeType === Node.ELEMENT_NODE) observe(node); })));
    if (main) mutations.observe(main, { childList: true, subtree: true });
    return () => {
      mutations.disconnect();
      observer.disconnect();
      document.documentElement.classList.remove('scroll-motion');
    };
  }, [active]);

  let content;
  if (active === 'overview') content = <OverviewPage onNavigate={navigate} />;
  if (active === 'anomalies') content = <AnomalyPage onOpenTrack={openTrack} onOpenVehicle={openVehicle} />;
  if (active === 'vehicles') content = <VehiclePage initialVehicleId={vehicleId} onOpenTrack={openTrack} />;
  if (active === 'tracks') content = <TrackPage initialTrackId={trackId} />;
  if (active === 'duration') content = <DurationPage />;
  if (active === 'clusters') content = <ClustersPage />;
  if (active === 'quality') content = <QualityPage onOpenTrack={openTrack} />;
  if (active === 'methodology') content = <MethodologyPage onNavigate={navigate} />;
  if (active === 'simulator') content = <SimulatorPage />;

  return (
    <div className={'app-shell ' + (menuOpen ? 'menu-open' : '')}>
      <button className="mobile-backdrop" aria-label="Close navigation" aria-hidden={!menuOpen} onClick={closeMenu} tabIndex={menuOpen ? 0 : -1} />
      <aside className="sidebar" id="primary-navigation" aria-label="Primary navigation" aria-hidden={mobileViewport && !menuOpen} inert={mobileViewport && !menuOpen}>
        <div className="brand">
          <div className="brand-mark"><Truck size={21} aria-hidden="true" /></div>
          <div><strong>DT-CARGO</strong><span>FLEET INTELLIGENCE</span></div>
          <button className="icon-button sidebar-close" aria-label="Close navigation" onClick={closeMenu}><X size={18} /></button>
        </div>
        <div className="sidebar-status"><span className="signal-dot" /><span>ANALYST WORKSPACE</span></div>
        <nav>
          {groups.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-heading">{group.title}</div>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <button key={item.id} className={'nav-item ' + (active === item.id ? 'active' : '')} onClick={() => navigate(item.id)} aria-current={active === item.id ? 'page' : undefined}>
                    <Icon size={18} strokeWidth={1.8} aria-hidden="true" /><span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="footer-mark"><Radio size={15} aria-hidden="true" /><span>{health.data?.database === 'connected' ? 'MongoDB connected' : 'Local data mode'}</span></div>
          <small>Telemetry stays in this app environment.</small>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button ref={menuToggleRef} className="icon-button menu-toggle" aria-label="Open navigation" aria-controls="primary-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Menu size={20} /></button>
          <div className="breadcrumb"><span>DT-CARGO</span><span className="breadcrumb-slash">/</span><strong>{pageTitles[active]}</strong></div>
          <div className="topbar-meta"><span className="live-dot" /> LOCAL DATA <span className="topbar-separator" /> ANALYST VIEW</div>
        </header>
        <main className="main-content" id="main-content"><Suspense fallback={<div className="state-panel" role="status">Opening the analyst workspace…</div>}>{content}</Suspense></main>
      </div>
    </div>
  );
}
