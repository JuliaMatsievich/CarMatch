import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Car } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { register, login } from "../api/auth";
import styles from "./AuthPage.module.css";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login: setLogin, register: setRegister } = useAuth();
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
      if (isLogin) {
        const res = await login(formData.email, formData.password);
        setLogin(res.access_token, res.user);
      } else {
        const res = await register(formData.email, formData.password);
        setRegister(res.access_token, res.user);
      }
      navigate("/chat", { replace: true });
    } catch (err: unknown) {
      const ax = err as {
        response?: {
          data?: { detail?: string | { msg?: string }[] };
          status?: number;
        };
        code?: string;
      };
      const detail = ax.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        setError(
          typeof first === "object" && first?.msg
            ? first.msg
            : "Ошибка валидации"
        );
      } else if (!ax.response) {
        setError(
          "Не удалось подключиться к серверу. Проверьте, что бэкенд запущен (порт 8000) и CORS разрешён для этого адреса."
        );
      } else {
        setError("Ошибка входа или регистрации");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.authContainer}>
      <div className={styles.authCard}>
        <div className={styles.logoSection}>
          <div className={styles.logoWithIcon}>
            <div className={styles.carIconBg}>
              <Car className={styles.carIcon} />
            </div>
            <h1>CarMatch</h1>
          </div>
          <p>Интерактивный AI-консультант по подбору автомобилей</p>
        </div>

        <div className={styles.authToggle}>
          <button
            type="button"
            className={isLogin ? styles.active : ""}
            onClick={() => setIsLogin(true)}
          >
            Войти
          </button>
          <button
            type="button"
            className={!isLogin ? styles.active : ""}
            onClick={() => setIsLogin(false)}
          >
            Регистрация
          </button>
        </div>

        {error && <div className={styles.errorMessage}>{error}</div>}

        <form onSubmit={handleSubmit} className={styles.authForm}>
          <div className={styles.inputGroup}>
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className={styles.inputGroup}>
            <label htmlFor="password">Пароль</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={8}
            />
          </div>

          <button type="submit" disabled={loading} className={styles.submitBtn}>
            {loading ? "Загрузка..." : isLogin ? "Войти" : "Зарегистрироваться"}
          </button>
        </form>
      </div>
    </div>
  );
}
