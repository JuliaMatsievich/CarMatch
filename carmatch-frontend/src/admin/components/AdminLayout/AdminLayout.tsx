import { ReactNode } from "react";
import { Car, LogOut, Users, Warehouse } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../../contexts/AuthContext";
import styles from "./AdminLayout.module.css";

interface AdminLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

interface NavItem {
  label: string;
  path: string;
  icon: ReactNode;
}

export function AdminLayout({ title, subtitle, children }: AdminLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const navItems: NavItem[] = [
    {
      label: "Каталог автомобилей",
      path: "/admin/cars",
      icon: <Warehouse className={styles.navItemIcon} />,
    },
    {
      label: "Пользователи",
      path: "/admin/users",
      icon: <Users className={styles.navItemIcon} />,
    },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logoWithIcon}>
            <div className={styles.carIconBg}>
              <Car className={styles.carIcon} />
            </div>
            <div className={styles.logoText}>
              <h1>CarMatch Admin</h1>
              <span>панель управления</span>
            </div>
          </div>
        </div>
        <nav className={styles.nav}>
          <div className={styles.navSectionTitle}>Навигация</div>
          <ul className={styles.navList}>
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              return (
                <li key={item.path}>
                  <button
                    type="button"
                    className={`${styles.navItemButton} ${
                      isActive ? styles.navItemActive : ""
                    }`}
                    onClick={() => navigate(item.path)}
                  >
                    {item.icon}
                    <span className={styles.navItemLabel}>{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className={styles.sidebarFooter}>
          {user && (
            <div className={styles.adminEmail}>
              Вошли как: <strong>{user.email}</strong>
            </div>
          )}
          <button
            type="button"
            className={styles.logoutBtn}
            onClick={handleLogout}
          >
            <LogOut size={16} />
            Выйти
          </button>
        </div>
      </aside>
      <div className={styles.main}>
        <header className={styles.mainHeader}>
          <h2 className={styles.mainTitle}>{title}</h2>
          {subtitle && <p className={styles.mainSubtitle}>{subtitle}</p>}
        </header>
        <main className={styles.mainContent}>{children}</main>
      </div>
    </div>
  );
}

