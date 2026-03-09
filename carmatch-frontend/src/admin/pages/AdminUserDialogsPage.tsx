import { useEffect, useMemo, useState } from "react";
import { Car, Trash2, User } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { AdminLayout } from "../components/AdminLayout/AdminLayout";
import { adminListUserSessions } from "../api/adminUsers";
import {
  adminGetSessionDetail,
  adminDeleteSession,
  type AdminSessionDetailResponse,
  type AdminSessionMessage,
  type AdminSessionListResponse,
} from "../api/adminSessions";
import styles from "./AdminUserDialogsPage.module.css";
import chatStyles from "../../components/Chat/MessageList.module.css";

type SelectedMessage = AdminSessionMessage | null;

function AdminUserDialogsInner() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null
  );
  const [selectedMessage, setSelectedMessage] = useState<SelectedMessage>(null);
  const [confirmSessionId, setConfirmSessionId] = useState<string | null>(null);

  const numericUserId = Number(userId);

  const {
    data: sessionsData,
    isLoading: isSessionsLoading,
  } = useQuery<AdminSessionListResponse>({
    queryKey: ["admin-user-sessions", numericUserId, page, perPage],
    queryFn: () => adminListUserSessions(numericUserId, page, perPage),
    enabled: Number.isFinite(numericUserId),
    placeholderData: keepPreviousData,
  });

  const totalPages = sessionsData?.pages ?? 0;
  const userEmail = sessionsData?.items[0]?.user_email;

  useEffect(() => {
    if (sessionsData?.items.length && !selectedSessionId) {
      setSelectedSessionId(sessionsData.items[0].id);
    }
  }, [sessionsData, selectedSessionId]);

  const {
    data: sessionDetail,
    isLoading: isDetailLoading,
  } = useQuery<AdminSessionDetailResponse | undefined>({
    queryKey: ["admin-session-detail-for-user", selectedSessionId],
    queryFn: () =>
      selectedSessionId ? adminGetSessionDetail(selectedSessionId) : undefined,
    enabled: !!selectedSessionId,
  });

  useEffect(() => {
    if (sessionDetail?.messages?.length) {
      setSelectedMessage(sessionDetail.messages[0]);
    } else {
      setSelectedMessage(null);
    }
  }, [sessionDetail]);

  const logsTitle = useMemo(() => {
    if (!selectedMessage) return "Логи";
    return selectedMessage.role === "user"
      ? "Extracted params (извлечённые параметры)"
      : "Search results (результаты поиска)";
  }, [selectedMessage]);

  const logsPayload = useMemo(() => {
    if (!selectedMessage || !sessionDetail) return null;

    if (selectedMessage.role === "user") {
      const meta = selectedMessage.ai_metadata as
        | { extracted_params?: unknown }
        | null
        | undefined;

      if (meta?.extracted_params != null) {
        return meta.extracted_params;
      }

      return null;
    }

    const meta = selectedMessage.ai_metadata as
      | { search_results?: unknown }
      | null
      | undefined;

    if (meta?.search_results != null) {
      return meta.search_results;
    }

    return meta ?? null;
  }, [selectedMessage, sessionDetail]);

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => adminDeleteSession(sessionId),
    onSuccess: (_data, deletedId) => {
      queryClient.invalidateQueries({
        queryKey: ["admin-user-sessions", numericUserId],
      });
      setConfirmSessionId(null);
      if (selectedSessionId === deletedId) {
        const remaining = sessionsData?.items.filter((s) => s.id !== deletedId);
        setSelectedSessionId(remaining && remaining.length ? remaining[0].id : null);
      }
    },
  });

  const openDeleteConfirm = (sessionId: string) => {
    setConfirmSessionId(sessionId);
  };

  return (
    <>
      <div className={styles.pageRoot}>
        <button
          type="button"
          className={styles.backLink}
          onClick={() => navigate("/admin/dialogs")}
        >
          ← Ко всем пользователям
        </button>

        <div className={styles.layoutGrid}>
          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <h3 className={styles.cardTitle}>
                Диалоги пользователя #{userId}
                {userEmail ? ` (${userEmail})` : ""}
              </h3>
            </div>
            <div className={styles.sessionsWrapper}>
            {isSessionsLoading && (
              <div style={{ padding: 12 }}>Загрузка диалогов...</div>
            )}
            {!isSessionsLoading && sessionsData && (
              <>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Дата</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {sessionsData.items.map((s) => (
                      <tr
                        key={s.id}
                        className={
                          s.id === selectedSessionId ? styles.rowSelected : undefined
                        }
                      >
                        <td
                          className={styles.clickableRow}
                          onClick={() => setSelectedSessionId(s.id)}
                        >
                          {s.id.slice(0, 8)}
                        </td>
                        <td
                          className={styles.clickableRow}
                          onClick={() => setSelectedSessionId(s.id)}
                        >
                          {new Date(s.created_at).toLocaleString("ru-RU")}
                        </td>
                        <td className={styles.sessionActions}>
                          <button
                            type="button"
                            className={styles.iconBtn}
                            title="Удалить сессию"
                            onClick={() => openDeleteConfirm(s.id)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {sessionsData.items.length === 0 && (
                      <tr>
                        <td
                          colSpan={2}
                          style={{ padding: 12, textAlign: "center" }}
                        >
                          Диалоги не найдены
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <div className={styles.pagination}>
                  <div>
                    Всего: {sessionsData.total} • Стр. {sessionsData.page} из{" "}
                    {sessionsData.pages || 1}
                  </div>
                  <div className={styles.pageControls}>
                    <button
                      type="button"
                      className={styles.pageBtn}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      Назад
                    </button>
                    <button
                      type="button"
                      className={styles.pageBtn}
                      onClick={() =>
                        setPage((p) =>
                          totalPages && p < totalPages ? p + 1 : p
                        )
                      }
                      disabled={!totalPages || page >= totalPages}
                    >
                      Вперёд
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>Чат</h3>
          </div>
          <div className={styles.chatScrollWrap}>
          {isDetailLoading && (
            <div style={{ padding: 12 }}>Загрузка чата...</div>
          )}
          {!isDetailLoading && sessionDetail && (
            <ul className={chatStyles.list}>
              {sessionDetail.messages
                .slice()
                .sort((a, b) => a.sequence_order - b.sequence_order)
                .map((m) => (
                  <li
                    key={m.id}
                    className={`${styles.clickableRow} ${
                      m.role === "user"
                        ? chatStyles.userRow
                        : chatStyles.assistantRow
                    }`}
                    onClick={() => setSelectedMessage(m)}
                  >
                    {m.role === "user" ? null : (
                      <span className={chatStyles.iconWrap} aria-hidden>
                        <Car size={20} className={chatStyles.iconCar} />
                      </span>
                    )}
                    <div
                      className={
                        m.role === "user"
                          ? chatStyles.userBubble
                          : chatStyles.assistantBubble
                      }
                    >
                      <div
                        className={
                          m.role === "user"
                            ? chatStyles.userMessage
                            : chatStyles.assistantMessage
                        }
                      >
                        <span className={chatStyles.role}>
                          {m.role === "user" ? "Пользователь" : "CarMatch"}
                        </span>
                        <p className={chatStyles.content}>{m.content}</p>
                      </div>
                    </div>
                    {m.role === "user" ? (
                      <span className={chatStyles.iconWrap} aria-hidden>
                        <User size={20} className={chatStyles.iconUser} />
                      </span>
                    ) : null}
                    {selectedMessage && selectedMessage.id === m.id && (
                      <span className={styles.selectedCheck} aria-hidden>
                        ✓
                      </span>
                    )}
                  </li>
                ))}
            </ul>
          )}
          {!isDetailLoading && !sessionDetail && (
            <div style={{ padding: 12, fontSize: "0.85rem", color: "#6b7280" }}>
              Выберите диалог слева, чтобы увидеть сообщения.
            </div>
          )}
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>{logsTitle}</h3>
          </div>
          <div className={styles.logsBody}>
            {!selectedMessage && (
              <div className={styles.logsPlaceholder}>
                Нажмите на сообщение в чате, чтобы увидеть связанные логи.
              </div>
            )}
            {selectedMessage && logsPayload && (
              <pre className={styles.logsPre}>
                {JSON.stringify(logsPayload, null, 2)}
              </pre>
            )}
            {selectedMessage && !logsPayload && (
              <div className={styles.logsPlaceholder}>
                Для этого сообщения нет дополнительных логов.
              </div>
            )}
          </div>
        </section>
        </div>
      </div>

      {confirmSessionId && (
        <div className={styles.modalBackdrop}>
          <div className={styles.modal}>
            <h3 className={styles.modalTitle}>Удалить диалог?</h3>
            <p className={styles.modalText}>
              Диалог #{confirmSessionId.slice(0, 8)} пользователя #{userId} будет
              удалён вместе со всеми сообщениями. Это действие необратимо.
            </p>
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.modalBtn}
                onClick={() => setConfirmSessionId(null)}
                disabled={deleteMutation.isPending}
              >
                Отменить
              </button>
              <button
                type="button"
                className={styles.modalBtnDanger}
                onClick={() => deleteMutation.mutate(confirmSessionId)}
                disabled={deleteMutation.isPending}
              >
                Удалить диалог
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function AdminUserDialogsPage() {
  const { userId } = useParams<{ userId: string }>();

  return (
    <AdminLayout
      title={`Диалоги пользователя #${userId}`}
      subtitle="Таблица диалогов, чат и связанные логи"
    >
      <AdminUserDialogsInner />
    </AdminLayout>
  );
}
