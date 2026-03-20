import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import AboutPage from "./pages/AboutPage";
import AnalyzerPage from "./pages/AnalyzerPage";
import HistoryPage from "./pages/HistoryPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/analyzer" replace />} />
        <Route path="/analyzer" element={<AnalyzerPage />} />
        <Route path="/result/:id" element={<ResultPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
    </AppShell>
  );
}
