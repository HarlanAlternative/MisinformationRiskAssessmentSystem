import { NavLink } from "react-router-dom";

const navigation = [
  { to: "/analyzer", label: "Analyzer" },
  { to: "/history", label: "History" },
  { to: "/about", label: "About" },
];

export default function AppShell({ children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Production ML System</p>
          <h1>Misinformation Risk Assessment System</h1>
          <p className="muted">
            Hybrid inference across Logistic Regression, Random Forest, and DistilBERT.
          </p>
        </div>

        <nav className="nav">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-card">
          <span className="sidebar-label">Hybrid Score</span>
          <p>0.5 Logistic Regression + 0.3 Random Forest + 0.2 DistilBERT</p>
        </div>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
