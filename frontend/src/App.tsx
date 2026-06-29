import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { StrategyWorkspace } from './pages/StrategyWorkspace';
import { AdjustmentView } from './pages/AdjustmentView';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<StrategyWorkspace />} />
        <Route path="/adjustment" element={<AdjustmentView />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
