import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Pencil, Trash2, ChevronUp, ChevronDown } from "lucide-react";
import { AdminLayout } from "../components/AdminLayout/AdminLayout";
import {
  adminListCars,
  adminCreateCar,
  adminUpdateCar,
  adminDeleteCar,
  type AdminCarItem,
  type AdminCarCreate,
  type AdminCarUpdate,
} from "../api/adminCars";
import styles from "./AdminCarsPage.module.css";

interface CarFormState {
  mark_name: string;
  model_name: string;
  year: string;
  price_rub: string;
  body_type: string;
  fuel_type: string;
  engine_volume: string;
  horsepower: string;
  transmission: string;
  country: string;
  modification: string;
  description: string;
  is_active: boolean;
}

const emptyForm: CarFormState = {
  mark_name: "",
  model_name: "",
  year: "",
  price_rub: "",
  body_type: "",
  fuel_type: "",
  engine_volume: "",
  horsepower: "",
  transmission: "",
  country: "",
  modification: "",
  description: "",
  is_active: true,
};

function mapFormToPayload(form: CarFormState): AdminCarCreate | AdminCarUpdate {
  const payload: AdminCarCreate = {
    mark_name: form.mark_name,
    model_name: form.model_name,
    is_active: form.is_active,
  };
  if (form.year) payload.year = Number(form.year);
  if (form.price_rub) payload.price_rub = Number(form.price_rub);
  if (form.body_type) payload.body_type = form.body_type;
  if (form.fuel_type) payload.fuel_type = form.fuel_type;
  if (form.engine_volume) payload.engine_volume = Number(form.engine_volume);
  if (form.horsepower) payload.horsepower = Number(form.horsepower);
  if (form.transmission) payload.transmission = form.transmission;
  if (form.country) payload.country = form.country;
  if (form.modification) payload.modification = form.modification;
  if (form.description) payload.description = form.description;
  return payload;
}

function AdminCarsInner() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [markFilter, setMarkFilter] = useState("");
  const [modelFilter, setModelFilter] = useState("");
  const [onlyActive, setOnlyActive] = useState(true);
  const [fuelFilter, setFuelFilter] = useState("");
  const [transmissionFilter, setTransmissionFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [sortBy, setSortBy] = useState<"mark_name" | "model_name" | "year" | "">(
    ""
  );
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingCar, setEditingCar] = useState<AdminCarItem | null>(null);
  const [form, setForm] = useState<CarFormState>(emptyForm);

  const { data, isLoading } = useQuery({
    queryKey: [
      "admin-cars",
      page,
      perPage,
      markFilter,
      modelFilter,
      fuelFilter,
      transmissionFilter,
      countryFilter,
      onlyActive,
      sortBy,
      sortDir,
    ],
    queryFn: () =>
      adminListCars({
        page,
        per_page: perPage,
        mark_name: markFilter || undefined,
        model_name: modelFilter || undefined,
        fuel_type: fuelFilter || undefined,
        transmission: transmissionFilter || undefined,
        country: countryFilter || undefined,
        is_active: onlyActive ? true : undefined,
        sort_by: sortBy || undefined,
        sort_dir: sortBy ? sortDir : undefined,
      }),
    keepPreviousData: true,
  });

  const createMutation = useMutation({
    mutationFn: (body: AdminCarCreate) => adminCreateCar(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cars"] });
      setModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (params: { id: number; body: AdminCarUpdate }) =>
      adminUpdateCar(params.id, params.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cars"] });
      setModalOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminDeleteCar(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cars"] });
    },
  });

  const openCreateModal = () => {
    setEditingCar(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEditModal = (car: AdminCarItem) => {
    setEditingCar(car);
    setForm({
      mark_name: car.mark_name,
      model_name: car.model_name,
      year: car.year ? String(car.year) : "",
      price_rub: car.price_rub ? String(car.price_rub) : "",
      body_type: car.body_type || "",
      fuel_type: car.fuel_type || "",
      engine_volume:
        typeof car.engine_volume === "number" ? String(car.engine_volume) : "",
      horsepower:
        typeof car.horsepower === "number" ? String(car.horsepower) : "",
      transmission: car.transmission || "",
      country: car.country || "",
      modification: car.modification || "",
      description: car.description || "",
      is_active: car.is_active,
    });
    setModalOpen(true);
  };

  const handleFormChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmitForm = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = mapFormToPayload(form);
    if (editingCar) {
      updateMutation.mutate({ id: editingCar.id, body: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleDelete = (car: AdminCarItem) => {
    // eslint-disable-next-line no-alert
    const ok = window.confirm(
      `Удалить автомобиль #${car.id} ${car.mark_name} ${car.model_name}?`
    );
    if (!ok) return;
    deleteMutation.mutate(car.id);
  };

  const totalPages = data?.pages ?? 0;

  return (
    <>
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <input
            className={styles.filterInput}
            placeholder="Марка"
            value={markFilter}
            onChange={(e) => setMarkFilter(e.target.value)}
          />
          <input
            className={styles.filterInput}
            placeholder="Модель"
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
          />
          <input
            className={styles.filterInput}
            placeholder="Топливо"
            value={fuelFilter}
            onChange={(e) => setFuelFilter(e.target.value)}
          />
          <input
            className={styles.filterInput}
            placeholder="КПП"
            value={transmissionFilter}
            onChange={(e) => setTransmissionFilter(e.target.value)}
          />
          <input
            className={styles.filterInput}
            placeholder="Страна"
            value={countryFilter}
            onChange={(e) => setCountryFilter(e.target.value)}
          />
          <button
            type="button"
            className={styles.toggleActive}
            onClick={() => setOnlyActive((v) => !v)}
          >
            {onlyActive ? "Только активные" : "Все состояния"}
          </button>
        </div>
        <div className={styles.toolbarRight}>
          <button
            type="button"
            className={styles.addBtn}
            onClick={openCreateModal}
          >
            Добавить авто
          </button>
        </div>
      </div>

      <div className={styles.tableCard}>
        {isLoading && <div style={{ padding: 12 }}>Загрузка...</div>}
        {!isLoading && data && (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>
                    <button
                      type="button"
                      className={styles.sortableHeader}
                      onClick={() => {
                        setSortBy("mark_name");
                        setSortDir((prev) =>
                          sortBy === "mark_name" && prev === "asc" ? "desc" : "asc"
                        );
                      }}
                    >
                      <span>Марка</span>
                      {sortBy === "mark_name" ? (
                        sortDir === "asc" ? (
                          <ChevronUp size={14} className={styles.sortIcon} />
                        ) : (
                          <ChevronDown size={14} className={styles.sortIcon} />
                        )
                      ) : null}
                    </button>
                  </th>
                  <th>
                    <button
                      type="button"
                      className={styles.sortableHeader}
                      onClick={() => {
                        setSortBy("model_name");
                        setSortDir((prev) =>
                          sortBy === "model_name" && prev === "asc" ? "desc" : "asc"
                        );
                      }}
                    >
                      <span>Модель</span>
                      {sortBy === "model_name" ? (
                        sortDir === "asc" ? (
                          <ChevronUp size={14} className={styles.sortIcon} />
                        ) : (
                          <ChevronDown size={14} className={styles.sortIcon} />
                        )
                      ) : null}
                    </button>
                  </th>
                  <th>
                    <button
                      type="button"
                      className={styles.sortableHeader}
                      onClick={() => {
                        setSortBy("year");
                        setSortDir((prev) =>
                          sortBy === "year" && prev === "asc" ? "desc" : "asc"
                        );
                      }}
                    >
                      <span>Год</span>
                      {sortBy === "year" ? (
                        sortDir === "asc" ? (
                          <ChevronUp size={14} className={styles.sortIcon} />
                        ) : (
                          <ChevronDown size={14} className={styles.sortIcon} />
                        )
                      ) : null}
                    </button>
                  </th>
                  <th>Кузов</th>
                  <th>Топливо</th>
                  <th>КПП</th>
                  <th>Страна</th>
                  <th>Объём</th>
                  <th>Л.с.</th>
                  <th>Описание</th>
                  <th>Статус</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((car) => (
                  <tr key={car.id}>
                    <td title={String(car.id)}>{car.id}</td>
                    <td
                      className={styles.cellEllipsis}
                      title={car.mark_name || undefined}
                    >
                      {car.mark_name}
                    </td>
                    <td
                      className={styles.cellEllipsis}
                      title={car.model_name || undefined}
                    >
                      {car.model_name}
                    </td>
                    <td title={String(car.year ?? "-")}>{car.year ?? "-"}</td>
                    <td
                      className={styles.cellEllipsis}
                      title={car.body_type || undefined}
                    >
                      {car.body_type ?? "-"}
                    </td>
                    <td
                      className={styles.cellEllipsis}
                      title={car.fuel_type || undefined}
                    >
                      {car.fuel_type ?? "-"}
                    </td>
                    <td
                      className={styles.cellEllipsis}
                      title={car.transmission || undefined}
                    >
                      {car.transmission ?? "-"}
                    </td>
                    <td
                      className={styles.cellEllipsis}
                      title={car.country || undefined}
                    >
                      {car.country ?? "-"}
                    </td>
                    <td
                      title={
                        typeof car.engine_volume === "number"
                          ? car.engine_volume.toFixed(1)
                          : "-"
                      }
                    >
                      {typeof car.engine_volume === "number"
                        ? car.engine_volume.toFixed(1)
                        : "-"}
                    </td>
                    <td title={String(car.horsepower ?? "-")}>
                      {car.horsepower ?? "-"}
                    </td>
                    <td
                      className={styles.descriptionCell}
                      title={car.description || undefined}
                    >
                      {car.description ?? "-"}
                    </td>
                    <td
                      title={car.is_active ? "Активен" : "Снят"}
                    >
                      <span
                        className={`${styles.statusChip} ${
                          car.is_active ? styles.statusActive : styles.statusInactive
                        }`}
                      >
                        {car.is_active ? "Активен" : "Снят"}
                      </span>
                    </td>
                    <td className={styles.actionsCell}>
                      <button
                        type="button"
                        className={styles.iconBtn}
                        onClick={() => openEditModal(car)}
                        title="Редактировать"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                        onClick={() => handleDelete(car)}
                        title="Удалить"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={13} style={{ padding: 12, textAlign: "center" }}>
                      Автомобили не найдены
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className={styles.pagination}>
              <div className={styles.paginationInfo}>
                Всего: {data.total} • Стр. {data.page} из {data.pages || 1} • по {perPage} на стр.
              </div>
              <div className={styles.pageControls}>
                <button
                  type="button"
                  className={styles.pageBtn}
                  onClick={() => setPage(1)}
                  disabled={page <= 1}
                  title="В начало"
                >
                  «
                </button>
                <button
                  type="button"
                  className={styles.pageBtn}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  Назад
                </button>
                <span className={styles.pageNumbers}>
                  {Array.from({ length: Math.min(5, totalPages || 1) }, (_, i) => {
                    const total = totalPages || 1;
                    let p: number;
                    if (total <= 5) p = i + 1;
                    else if (page <= 3) p = i + 1;
                    else if (page >= total - 2) p = total - 4 + i;
                    else p = page - 2 + i;
                    return (
                      <button
                        key={p}
                        type="button"
                        className={`${styles.pageBtn} ${page === p ? styles.pageBtnActive : ""}`}
                        onClick={() => setPage(p)}
                        disabled={!totalPages}
                      >
                        {p}
                      </button>
                    );
                  })}
                </span>
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
                <button
                  type="button"
                  className={styles.pageBtn}
                  onClick={() => setPage(totalPages || 1)}
                  disabled={!totalPages || page >= totalPages}
                  title="В конец"
                >
                  »
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {modalOpen && (
        <div className={styles.modalBackdrop}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                {editingCar ? "Редактировать автомобиль" : "Новый автомобиль"}
              </div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSubmitForm}>
              <div className={styles.modalGrid}>
                <div className={styles.modalField}>
                  <label htmlFor="mark_name">Марка</label>
                  <input
                    id="mark_name"
                    name="mark_name"
                    value={form.mark_name}
                    onChange={handleFormChange}
                    required
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="model_name">Модель</label>
                  <input
                    id="model_name"
                    name="model_name"
                    value={form.model_name}
                    onChange={handleFormChange}
                    required
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="year">Год</label>
                  <input
                    id="year"
                    name="year"
                    type="number"
                    value={form.year}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="price_rub">Цена (руб.)</label>
                  <input
                    id="price_rub"
                    name="price_rub"
                    type="number"
                    value={form.price_rub}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="body_type">Кузов</label>
                  <input
                    id="body_type"
                    name="body_type"
                    value={form.body_type}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="fuel_type">Топливо</label>
                  <input
                    id="fuel_type"
                    name="fuel_type"
                    value={form.fuel_type}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="engine_volume">Объём двигателя (л)</label>
                  <input
                    id="engine_volume"
                    name="engine_volume"
                    type="number"
                    step="0.1"
                    value={form.engine_volume}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="horsepower">Мощность (л.с.)</label>
                  <input
                    id="horsepower"
                    name="horsepower"
                    type="number"
                    value={form.horsepower}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="transmission">КПП</label>
                  <input
                    id="transmission"
                    name="transmission"
                    value={form.transmission}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="country">Страна</label>
                  <input
                    id="country"
                    name="country"
                    value={form.country}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label htmlFor="modification">Модификация</label>
                  <input
                    id="modification"
                    name="modification"
                    value={form.modification}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField} style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="description">Описание</label>
                  <textarea
                    id="description"
                    name="description"
                    value={form.description}
                    onChange={handleFormChange}
                  />
                </div>
                <div className={styles.modalField}>
                  <label>
                    <input
                      type="checkbox"
                      name="is_active"
                      checked={form.is_active}
                      onChange={handleFormChange}
                    />{" "}
                    Активен
                  </label>
                </div>
              </div>
              <div className={styles.modalFooter}>
                <button
                  type="button"
                  className={styles.modalSecondaryBtn}
                  onClick={() => setModalOpen(false)}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className={styles.modalPrimaryBtn}
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  {editingCar ? "Сохранить" : "Создать"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

export default function AdminCarsPage() {
  return (
    <AdminLayout
      title="Каталог автомобилей"
      subtitle="Просмотр и управление записями в таблице cars"
    >
      <AdminCarsInner />
    </AdminLayout>
  );
}

