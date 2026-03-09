import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Car, ShieldCheck } from "lucide-react";
import { login } from "../../api/auth";
import { useAdminAuth } from "../contexts/AdminAuthContext";
import styles from "./AdminLoginPage.module.css";

export default function AdminLoginPage() {
  const [formData, setFormData] = useState({
    email: "admin@mail.ru",
    password: "admin1234",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login: setAdminLogin } = useAdminAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await login(formData.email, formData.password);
      if (!res.user.is_admin) {
        setError("Этот пользователь не является администратором.");
        return;
      }
      setAdminLogin(res.access_token, res.user);
      navigate("/admin/cars", { replace: true });
    } catch (err: unknown) {
      const ax = err as {
        response?: {
          data?: { detail?: string | { msg?: string }[] };
          status?: number;
        };
      };
      const detail = ax.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        const msg =
          typeof first === "object" && first?.msg
            ? first.msg
            : "Ошибка валидации данных";
        setError(msg);
      } else {
        setError("Не удалось войти в админ-панель");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.authContainer}>
      <div className={styles.authCard}>
        <div className={styles.logoSection}>
          <div className={styles.badge}>
            <ShieldCheck size={14} />
            Admin
          </div>
          <div className={styles.logoWithIcon}>
            <div className={styles.carIconBg}>
              <Car className={styles.carIcon} />
            </div>
            <h1>CarMatch Admin</h1>
          </div>
          <p>Закрытая панель управления сервисом подбора авто</p>
        </div>

        {error && <div className={styles.errorMessage}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className={styles.inputGroup}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>
          <div className={styles.inputGroup}>
            <label htmlFor="password">Пароль</label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className={styles.submitBtn}
          >
            {loading ? "Входим..." : "Войти в админ-панель"}
          </button>
        </form>

        <div className={styles.hint}>
          По умолчанию: <strong>admin@mail.ru / admin1234</strong>
        </div>
      </div>
    </div>
  );
}

