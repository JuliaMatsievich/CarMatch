import React from 'react';
import { Car } from 'lucide-react';
import './Dashboard.css';

interface DashboardProps {
  onLogout: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onLogout }) => {
  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="logo">
          <div className="logo-with-icon">
            <div className="car-icon-bg">
              <Car className="car-icon" />
            </div>
            <h1>CarMatch</h1>
          </div>
        </div>
        <nav className="main-nav">
          <button>Профиль</button>
          <button onClick={onLogout}>Выйти</button>
        </nav>
      </header>

      <main className="dashboard-main">
        <div className="welcome-section">
          <h2>Добро пожаловать в CarMatch!</h2>
          <p>Это интерактивный AI-консультант по подбору автомобилей.</p>
          <p>В настоящий момент эта страница находится в разработке</p>
        </div>
        
      </main>
    </div>
  );
};

export default Dashboard;