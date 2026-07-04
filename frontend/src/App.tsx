import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { StrategyWorkspace } from './pages/StrategyWorkspace';
import { AdjustmentView } from './pages/AdjustmentView';

function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-primary">
      <div className="text-center">
        <h1 className="text-4xl font-bold">404</h1>
        <p className="mt-2 text-secondary">Page not found</p>
        <a href="/" className="mt-4 inline-block rounded-xl bg-accent px-4 py-2 text-white">Go Home</a>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<StrategyWorkspace />} />
        <Route path="/adjustment" element={<AdjustmentView />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;