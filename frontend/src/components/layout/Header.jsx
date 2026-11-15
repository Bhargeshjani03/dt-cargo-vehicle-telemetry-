
import { useLocation } from "react-router-dom";
import { Bell, ChevronRight } from "lucide-react";

const pageTitles = {
  "/": "Fleet Overview",
  "/anomalies": "Anomaly Intelligence",
  "/regression": "Tour Regression",
  "/vehicles": "Vehicle Analytics",
  "/tracks": "Track Analytics",
  "/data-quality": "Data Quality",
  "/methodology/eda": "Exploratory Data Analysis",
  "/methodology/preprocessing": "Data Preprocessing",
  "/methodology/clustering": "Clustering Analysis",
  "/methodology/models": "Model Development",
  "/methodology/evaluation": "Model Evaluation",
};

export default function Header() {
  const location = useLocation();
  const title = pageTitles[location.pathname] || "DT-CARGO";

  const isMethodology = location.pathname.startsWith("/methodology");

  return (
    <header className="top-header">
      <div className="header-heading">
        <div className="breadcrumb">
          <span>DT-CARGO</span>
          <ChevronRight size={14} />
          <span>{isMethodology ? "Methodology" : "Workspace"}</span>
        </div>
        <h2>{title}</h2>
      </div>

      <div className="header-actions">
        <span className="environment-label">
          <span className="status-dot" />
          Local environment
        </span>

        <button className="icon-button" aria-label="Notifications">
          <Bell size={19} />
        </button>

        <div className="user-avatar">BC</div>
      </div>
    </header>
  );
}
