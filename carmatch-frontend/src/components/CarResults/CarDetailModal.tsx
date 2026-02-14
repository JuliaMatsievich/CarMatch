import type { CarResult } from '../../api/cars';
import styles from './CarDetailModal.module.css';

interface CarDetailModalProps {
  car: CarResult;
  onClose: () => void;
}

export function CarDetailModal({ car, onClose }: CarDetailModalProps) {
  const formatPrice = (n: number | null) =>
    n != null ? `${Number(n).toLocaleString('ru-RU')} ₽` : null;

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="car-detail-title">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 id="car-detail-title" className={styles.title}>
            {car.mark_name} {car.model_name}
          </h2>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>

        <div className={styles.gallery}>
          {car.images && car.images.length > 0 ? (
            car.images.map((src, i) => (
              <img key={i} src={src} alt="" className={styles.galleryImage} />
            ))
          ) : (
            <div className={styles.noImage}>Нет фото</div>
          )}
        </div>

        <div className={styles.body}>
          <dl className={styles.specList}>
            {car.year != null && (
              <>
                <dt>Год</dt>
                <dd>{car.year}</dd>
              </>
            )}
            {formatPrice(car.price_rub) && (
              <>
                <dt>Цена</dt>
                <dd>{formatPrice(car.price_rub)}</dd>
              </>
            )}
            {car.body_type && (
              <>
                <dt>Тип кузова</dt>
                <dd>{car.body_type}</dd>
              </>
            )}
            {car.fuel_type && (
              <>
                <dt>Топливо</dt>
                <dd>{car.fuel_type}</dd>
              </>
            )}
            {car.transmission && (
              <>
                <dt>Коробка</dt>
                <dd>{car.transmission}</dd>
              </>
            )}
            {car.engine_volume != null && (
              <>
                <dt>Объём двигателя</dt>
                <dd>{car.engine_volume} л</dd>
              </>
            )}
            {car.horsepower != null && (
              <>
                <dt>Мощность</dt>
                <dd>{car.horsepower} л.с.</dd>
              </>
            )}
            {car.modification && (
              <>
                <dt>Модификация</dt>
                <dd>{car.modification}</dd>
              </>
            )}
          </dl>

          {car.description && (
            <div className={styles.descriptionBlock}>
              <h4 className={styles.descriptionTitle}>Описание</h4>
              <p className={styles.description}>{car.description}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
