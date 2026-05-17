import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Toaster from './components/Toaster'
import Dashboard from './views/Dashboard'
import NewAnalysis from './views/NewAnalysis'
import InventoryView from './views/InventoryView'
import RiskHeatmap from './views/RiskHeatmap'
import DocsLibrary from './views/DocsLibrary'
import EnforcementLog from './views/EnforcementLog'
import { useInventory } from './store/inventory'

export default function App() {
  const startPolling = useInventory((s) => s.startPolling)
  const stopPolling = useInventory((s) => s.stopPolling)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  return (
    <BrowserRouter>
      <Toaster />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="analyze" element={<NewAnalysis />} />
          <Route path="inventory" element={<InventoryView />} />
          <Route path="heatmap" element={<RiskHeatmap />} />
          <Route path="docs" element={<DocsLibrary />} />
          <Route path="enforcement" element={<EnforcementLog />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
