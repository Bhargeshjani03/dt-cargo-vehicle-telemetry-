
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  AlertTriangle,
  ChartNoAxesCombined,
  Truck,
  Route,
  Database,
  Search,
  Filter,
  Network,
  BrainCircuit,
  ClipboardCheck,
  ChevronRight,
  Activity,
} from "lucide-react";


const operationalLinks = [
  { label: "Overview", path: "/", icon: LayoutDashboard },
  { label: "Anomaly Intelligence", path: "/anomalies", icon: AlertTriangle },
  { label: "Operational Insights", path: "/insights", icon: Activity },
  { label: "Tour Regression", path: "/regression/validation", icon: ChartNoAxesCombined },
  { label: "Vehicles", path: "/vehicles", icon: Truck },
  { label: "Track Analytics", path: "/tracks", icon: Route },
  { label: "Data Quality", path: "/data-quality", icon: Database },
];


const methodologyLinks = [
  { label: "Exploratory Analysis", path: "/methodology/eda", icon: Search },
  { label: "Preprocessing", path: "/methodology/preprocessing", icon: Filter },
  { label: "Clustering", path: "/methodology/clustering", icon: Network },
  { label: "Model Development", path: "/methodology/models", icon: BrainCircuit },
  { label: "Evaluation", path: "/methodology/evaluation", icon: ClipboardCheck },
];

function NavigationGroup({ title, links }) {
  return (
    <div className="nav-group">
      <p className="nav-group-title">{title}</p>

      {links.map(({ label, path, icon: Icon }) => (
        <NavLink
          key={path}
          to={path}
          end={path === "/"}
          className={({ isActive }) =>
            `nav-link ${isActive ? "active" : ""}`
          }
        >
          <Icon size={17} strokeWidth={1.8} />
          <span>{label}</span>
          {label === "Overview" && <ChevronRight size={14} className="nav-chevron" />}
        </NavLink>
      ))}
    </div>
  );
}

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <Activity size={23} />
        </div>
        <div>
          <h1>DT-CARGO</h1>
          <span>FLEET INTELLIGENCE</span>
          <span className="sidebar-version">DT-CARGO v2.0</span>
        </div>
      </div>

      <div className="sidebar-content">
        <NavigationGroup
          title="OPERATIONAL INTELLIGENCE"
          links={operationalLinks}
        />

        <NavigationGroup
          title="PROJECT METHODOLOGY"
          links={methodologyLinks}
        />
      </div>

      <div className="sidebar-footer">
        <div className="status-dot" />
        <div>
          <p>System workspace</p>
          <span>Development environment</span>
        </div>
      </div>
    </aside>
  );
}
