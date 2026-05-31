import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster, toast } from 'react-hot-toast';
import './index.css';

import LandingPage from './components/Landing/LandingPage';
import Layout from './components/Layout/Layout';
import Dashboard from './components/Dashboard/Dashboard';
import SquadPage from './components/Squad/SquadPage';
import SbcsPage from './pages/SbcsPage';
import SettingsPage from './pages/SettingsPage';
import CalculatorPage from './pages/CalculatorPage';
import { useApi } from './hooks/useApi';
import ShadowOverlay from './components/Layout/ShadowOverlay';
import TransitionGrid from './components/Layout/TransitionGrid';
import ThreeDCard from './components/Dashboard/ThreeDCard';

export default function App() {
  const api = useApi();
  const [showLanding, setShowLanding] = useState(true);
  const [activePage, setActivePage] = useState('sbcs');
  const [squadStats, setSquadStats] = useState(null);
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [squadPlayers, setSquadPlayers] = useState([]);

  // Carregar dados iniciais ao entrar no app
  const loadInitialData = async () => {
    try {
      const [statsData, scrapeData, squadData] = await Promise.all([
        api.get('/api/squad/stats'),
        api.get('/api/scrape/status'),
        api.get('/api/squad'),
      ]);
      setSquadStats(statsData);
      setScrapeStatus(scrapeData);
      setSquadPlayers(squadData || []);
    } catch (e) {
      console.error('Erro ao carregar dados:', e);
    }
  };

  const handleStart = () => {
    setShowLanding(false);
    loadInitialData();
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    const refreshToast = toast.loading('Sincronizando Futbin...');
    try {
      await api.post('/api/scrape/start', {});
      // Polling do status até finalizar
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const data = await api.get('/api/scrape/status');
        setScrapeStatus(data);
        if (data.status !== 'running' || attempts > 60) {
          clearInterval(poll);
          setIsRefreshing(false);
          loadInitialData();
          if (data.status === 'completed' || data.status === 'idle') {
            toast.success('Sincronização concluída!', { id: refreshToast });
          } else {
            toast.error('Erro na sincronização.', { id: refreshToast });
          }
        }
      }, 3000);
    } catch (e) {
      setIsRefreshing(false);
      toast.error('Erro ao iniciar sincronização.', { id: refreshToast });
    }
  };

  const handleImportCSV = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const loadingToast = toast.loading('Importando elenco...');
    try {
      const data = await api.post('/api/squad/import', formData, true);
      toast.success(data.message || 'Elenco importado com sucesso!', { id: loadingToast });
      loadInitialData();
    } catch (e) {
      toast.error('Erro ao importar CSV', { id: loadingToast });
    }
  };

  // Títulos das páginas
  const PAGE_TITLES = {
    dashboard: 'Dashboard',
    sbcs: 'DMEs / SBCs',
    squad: 'Elenco',
    calculator: 'Calculador',
    settings: 'Configurações',
  };

  const renderPage = () => {
    const pageAnimation = {
      initial: { opacity: 0, y: 10 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -10 },
      transition: { duration: 0.2 }
    };

    switch (activePage) {
      case 'dashboard':
        return <motion.div key={activePage} {...pageAnimation}><Dashboard squadStats={squadStats} scrapeStatus={scrapeStatus} onNavigate={setActivePage} /></motion.div>;
      case 'squad':
        return <motion.div key={activePage} {...pageAnimation}><SquadPage squadStats={squadStats} onImportCSV={handleImportCSV} onNavigate={setActivePage} /></motion.div>;
      case 'sbcs':
        return <motion.div key={activePage} {...pageAnimation}><SbcsPage onNavigate={setActivePage} /></motion.div>;
      case 'calculator':
        return <motion.div key={activePage} {...pageAnimation}><CalculatorPage onNavigate={setActivePage} /></motion.div>;
      case 'settings':
        return <motion.div key={activePage} {...pageAnimation}><SettingsPage onNavigate={setActivePage} /></motion.div>;
      default:
        return <motion.div key={activePage} {...pageAnimation}><Dashboard squadStats={squadStats} scrapeStatus={scrapeStatus} onNavigate={setActivePage} /></motion.div>;
    }
  };

  return (
    <>
      <ShadowOverlay
        animation={{ scale: 50, speed: 50 }}
        noise={{ opacity: 0.4, scale: 1 }}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />
      {!showLanding && <ThreeDCard squadPlayers={squadPlayers} />}
      <TransitionGrid pageKey={activePage} />
      <Toaster 
        position="top-right" 
        toastOptions={{ 
          style: { 
            background: 'var(--bg-secondary)', 
            color: 'var(--text-primary)',
            border: '1px solid var(--border-primary)'
          } 
        }} 
      />
      <AnimatePresence>
        {showLanding && (
          <motion.div
            key="landing"
            initial={{ opacity: 1 }}
            exit={{ 
              opacity: 0, 
              scale: 1.08, 
              filter: 'blur(15px)',
              transition: { duration: 0.9, ease: [0.16, 1, 0.3, 1] } 
            }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              zIndex: 9999,
              background: '#000000',
              overflow: 'hidden'
            }}
          >
            <LandingPage onStart={handleStart} />
          </motion.div>
        )}
      </AnimatePresence>

      {!showLanding && (
        <motion.div
          key="app-main"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
          style={{ width: '100%', height: '100%' }}
        >
          <Layout
            activePage={activePage}
            onNavigate={setActivePage}
            title={PAGE_TITLES[activePage] || 'Dashboard'}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
          >
            <AnimatePresence mode="wait">
              {renderPage()}
            </AnimatePresence>
          </Layout>
        </motion.div>
      )}
    </>
  );
}
