import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { AdminLayout } from "../components/AdminLayout/AdminLayout";
import {
  adminGetSessionDetail,
  type AdminSessionMessage,
} from "../api/adminSessions";
import styles from "./AdminDialogDetailPage.module.css";

function statusClass(displayStatus: string): string {
  if (displayStatus === "Успешно") return styles.badgeSuccess;
  if (displayStatus === "В процессе") return styles.badgeInProgress;
  if (displayStatus === "Ошибка") return styles.badgeError;
  return styles.badgeDone;
}

function AdminDialogDetailInner() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-session-detail", sessionId],
    queryFn: () => adminGetSessionDetail(sessionId!),
    enabled: !!sessionId,
  });

  if (!sessionId) {
    return <div>Не указан ID диалога</div>;
  }

  if (isLoading || !data) {
    return <div>Загрузка диалога...</div>;
  }

  const { session, messages } = data;

  const assistantMessagesWithAi = messages.filter(
    (m) => m.role !== "user" && m.ai_metadata
  );

  const renderMessageMeta = (m: AdminSessionMessage) =>
    `${m.role === "user" ? "Пользователь" : "Бот"} • ${new Date(
      m.created_at
    ).toLocaleString("ru-RU")}`;

  return (
    <div className={styles.pageRoot}>
      <button
        type="button"
        className={styles.backLink}
        onClick={() => navigate("/admin/dialogs")}
      >
        ← К списку диалогов
      </button>
      <div className={styles.layoutGrid}>
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>Диалог #{session.id}</h3>
            <div className={styles.meta}>
              Пользователь #{session.user_id} ({session.user_email}) •{" "}
              {new Date(session.created_at).toLocaleString("ru-RU")} •{" "}
              <span
                className={`${styles.badge} ${statusClass(session.display_status)}`}
              >
                {session.display_status}
              </span>
            </div>
          </div>
          <ul className={styles.chatList}>
            {messages.map((m) => (
              <li key={m.id} className={styles.chatItem}>
                <div
                  className={
                    m.role === "user"
                      ? styles.bubbleUser
                      : styles.bubbleAssistant
                  }
                >
                  <div className={styles.bubbleMeta}>{renderMessageMeta(m)}</div>
                  <div>{m.content}</div>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>AI-лог и результаты</h3>
            <div className={styles.meta}>
              Извлечённые параметры:{" "}
              {Object.keys(session.extracted_params || {}).length || 0} •
              Автомобилей в выдаче: {session.cars_found}
            </div>
          </div>
          <ul className={styles.aiLogList}>
            {assistantMessagesWithAi.map((m) => (
              <li key={m.id} className={styles.aiLogItem}>
                <div className={styles.meta}>
                  Шаг #{m.sequence_order} •{" "}
                  {new Date(m.created_at).toLocaleTimeString("ru-RU")}
                </div>
                <pre style={{ whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(m.ai_metadata, null, 2)}
                </pre>
              </li>
            ))}
            {assistantMessagesWithAi.length === 0 && (
              <li className={styles.aiLogItem}>
                Нет AI-метаданных для этого диалога.
              </li>
            )}
          </ul>
        </section>
      </div>
      <section className={styles.card} style={{ marginTop: 14 }}>
        <div className={styles.cardHeader}>
          <h3 className={styles.cardTitle}>Предложенные автомобили</h3>
        </div>
        {session.search_results.length === 0 ? (
          <div className={styles.meta}>Автомобили не найдены.</div>
        ) : (
          <table className={styles.carsTable}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Модель</th>
                <th>Год</th>
                <th>Цена</th>
              </tr>
            </thead>
            <tbody>
              {session.search_results.map((car) => (
                <tr key={car.id}>
                  <td>{car.id}</td>
                  <td>
                    {car.mark_name} {car.model_name}
                  </td>
                  <td>{car.year ?? "-"}</td>
                  <td>
                    {car.price_rub == null
                      ? "-"
                      : car.price_rub.toLocaleString("ru-RU", {
                          style: "currency",
                          currency: "RUB",
                          maximumFractionDigits: 0,
                        })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default function AdminDialogDetailPage() {
  return (
    <AdminLayout
      title="Детальный просмотр диалога"
      subtitle="История сообщений, AI-лог и выданные автомобили"
    >
      <AdminDialogDetailInner />
    </AdminLayout>
  );
}

