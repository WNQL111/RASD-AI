import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Events from './pages/Events';
import Settings from './pages/Settings';
import Health from './pages/Health';
import Replay from './pages/Replay';
import Cases from './pages/Cases';
import Confidence from './pages/Confidence';

function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<Upload />} />
            <Route path="events" element={<Events />} />
            <Route path="settings" element={<Settings />} />
            <Route path="health" element={<Health />} />
            <Route path="video-replay" element={<Replay />} />
            <Route path="cases" element={<Cases />} />
            <Route path="confidence" element={<Confidence />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  );
}

export default App;
