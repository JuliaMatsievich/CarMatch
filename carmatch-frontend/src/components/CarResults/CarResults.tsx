import type { CarResult } from '../../api/cars';
import styles from './CarResults.module.css';

interface CarResultsProps {
  cars: CarResult[];
}

export function CarResults({ cars }: CarResultsProps) {
  if (cars.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Подобранные автомобили</h3>
      <div className={styles.grid}>
        {cars.map((car) => (
          <article key={car.id} className={styles.card}>
            {car.images?.[0] && (
              <img src={car.images[0]} alt="" className={styles.image} />
            )}
            <div className={styles.body}>
              <h4 className={styles.name}>
                {car.mark_name} {car.model_name}
              </h4>
              <p className={styles.meta}>
                {car.year != null && `${car.year} г.`}
                {car.price_rub != null && ` · ${car.price_rub.toLocaleString('ru-RU')} ₽`}
              </p>
              {(car.body_type || car.fuel_type) && (
                <p className={styles.specs}>
                  {[car.body_type, car.fuel_type].filter(Boolean).join(' · ')}
                </p>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
