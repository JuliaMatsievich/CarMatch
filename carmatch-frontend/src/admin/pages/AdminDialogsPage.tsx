import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { AdminLayout } from "../components/AdminLayout/AdminLayout";
import {
  adminListUsers,
  type AdminUserListItem,
  type AdminUserListResponse,
} from "../api/adminUsers";
import styles from "./AdminDialogsPage.module.css";

function AdminDialogsInner() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [emailFilter, setEmailFilter] = useState<string>("");

  const { data, isLoading } = useQuery<AdminUserListResponse>({
    queryKey: ["admin-dialog-users", page, perPage, emailFilter],
    queryFn: () =>
      adminListUsers({
        page,
        per_page: perPage,
        email: emailFilter || undefined,
      }),
    placeholderData: keepPreviousData,
  });

  const handleOpen = (user: AdminUserListItem) => {
    navigate(`/admin/users/${user.id}/dialogs`);
  };

  const totalPages = data?.pages ?? 0;

  return (
    <>
      <div className={styles.toolbar}>
        <input
          className={styles.filterInput}
          placeholder="Email пользователя"
          value={emailFilter}
          onChange={(e) => setEmailFilter(e.target.value)}
        />
      </div>

      <div className={styles.tableCard}>
        {isLoading && <div style={{ padding: 12 }}>Загрузка...</div>}
        {!isLoading && data && (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Пользователь</th>
                  <th>Дата последнего входа</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items
                  .filter((u) =>
                    emailFilter
                      ? u.email.toLowerCase().includes(emailFilter.toLowerCase())
                      : true
                  )
                  .map((u) => (
                    <tr key={u.id}>
                      <td>{u.id}</td>
                      <td>{u.email}</td>
                      <td>
                        {u.last_login
                          ? new Date(u.last_login).toLocaleString("ru-RU")
                          : "-"}
                      </td>
                      <td className={styles.actionsCell}>
                        <button
                          type="button"
                          className={styles.smallBtn}
                          onClick={() => handleOpen(u)}
                        >
                          Посмотреть
                        </button>
                      </td>
                    </tr>
                  ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ padding: 12, textAlign: "center" }}>
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
    </>
  );
}

export default function AdminDialogsPage() {
  return (
    <AdminLayout
      title="Диалоги"
      subtitle="Пользователи с диалогами и переход к деталям"
    >
      <AdminDialogsInner />
    </AdminLayout>
  );
}

