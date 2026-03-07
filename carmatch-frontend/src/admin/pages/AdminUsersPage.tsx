import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { AdminLayout } from "../components/AdminLayout/AdminLayout";
import {
  adminDeleteUser,
  adminListUsers,
  type AdminUserListResponse,
} from "../api/adminUsers";
import styles from "./AdminUsersPage.module.css";

function AdminUsersInner() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [emailFilter, setEmailFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>("");
  const [confirmUserId, setConfirmUserId] = useState<number | null>(null);
  const [confirmUserEmail, setConfirmUserEmail] = useState<string | null>(null);

  const { data, isLoading } = useQuery<AdminUserListResponse>({
    queryKey: ["admin-users", page, perPage, emailFilter, activeFilter],
    queryFn: () =>
      adminListUsers({
        page,
        per_page: perPage,
        email: emailFilter || undefined,
        is_active:
          activeFilter === ""
            ? undefined
            : activeFilter === "active"
              ? true
              : false,
      }),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: number) => adminDeleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-users"],
      });
      setConfirmUserId(null);
      setConfirmUserEmail(null);
    },
  });

  const handleDelete = (userId: number, email: string) => {
    setConfirmUserId(userId);
    setConfirmUserEmail(email);
  };

  const totalPages = data?.pages ?? 0;

  return (
    <>
      <div className={styles.toolbar}>
        <input
          className={styles.filterInput}
          placeholder="Email"
          value={emailFilter}
          onChange={(e) => setEmailFilter(e.target.value)}
        />
        <select
          className={styles.statusSelect}
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
        >
          <option value="">Любой статус</option>
          <option value="active">Активные</option>
          <option value="inactive">Заблокированные</option>
        </select>
      </div>

      <div className={styles.tableCard}>
        {isLoading && <div style={{ padding: 12 }}>Загрузка...</div>}
        {!isLoading && data && (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Email</th>
                  <th>Статус</th>
                  <th>Сессий</th>
                  <th>Логинов</th>
                  <th>Создан</th>
                  <th>Последний вход</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.email}</td>
                    <td>
                      <span
                        className={`${styles.badge} ${
                          u.is_active ? styles.badgeActive : styles.badgeInactive
                        }`}
                      >
                        {u.is_active ? "Активен" : "Неактивен"}
                      </span>
                    </td>
                    <td>{u.sessions_count}</td>
                    <td>{u.login_count}</td>
                    <td>
                      {new Date(u.created_at).toLocaleDateString("ru-RU")}
                    </td>
                    <td>
                      {u.last_login
                        ? new Date(u.last_login).toLocaleString("ru-RU")
                        : "-"}
                    </td>
                    <td className={styles.actionsCell}>
                      <button
                        type="button"
                        className={styles.smallBtn}
                        onClick={() => navigate(`/admin/users/${u.id}/dialogs`)}
                      >
                        Посмотреть диалоги
                      </button>
                      <button
                        type="button"
                        className={styles.iconBtn}
                        title="Удалить пользователя"
                        onClick={() => handleDelete(u.id, u.email)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ padding: 12, textAlign: "center" }}>
                      Пользователи не найдены
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className={styles.pagination}>
              <div>
                Всего: {data.total} • Стр. {data.page} из {data.pages || 1}
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

      {confirmUserId !== null && confirmUserEmail && (
        <div className={styles.modalBackdrop}>
          <div className={styles.modal}>
            <h3 className={styles.modalTitle}>Удалить пользователя?</h3>
            <p className={styles.modalText}>
              Пользователь #{confirmUserId} ({confirmUserEmail}) и все его
              диалоги будут удалены без возможности восстановления.
            </p>
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.modalBtn}
                onClick={() => {
                  setConfirmUserId(null);
                  setConfirmUserEmail(null);
                }}
                disabled={deleteMutation.isPending}
              >
                Отменить
              </button>
              <button
                type="button"
                className={styles.modalBtnDanger}
                onClick={() => deleteMutation.mutate(confirmUserId)}
                disabled={deleteMutation.isPending}
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function AdminUsersPage() {
  return (
    <AdminLayout
      title="Пользователи"
      subtitle="Список зарегистрированных пользователей и их активность"
    >
      <AdminUsersInner />
    </AdminLayout>
  );
}

