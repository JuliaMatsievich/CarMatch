import { useState } from 'react';
import type { CarResult } from '../../api/cars';
import { CarDetailModal } from './CarDetailModal';
import styles from './CarResults.module.css';

interface CarResultsProps {
  cars: CarResult[];
}

export function CarResults({ cars }: CarResultsProps) {
  const [selectedCar, setSelectedCar] = useState<CarResult | null>(null);

  if (cars.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Подобранные автомобили</h3>
      <div className={styles.grid}>
        {cars.map((car) => (
          <article
            key={car.id}
            className={styles.card}
            onClick={() => setSelectedCar(car)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setSelectedCar(car);
              }
            }}
            aria-label={`Подробнее: ${car.mark_name} ${car.model_name}`}
          >
            {car.images?.[0] && (
              <img src={car.images[0]} alt="" className={styles.image} />
            )}
            <div className={styles.body}>
              <h4 className={styles.name}>
                {car.mark_name} {car.model_name}
              </h4>
              <p className={styles.meta}>
                {car.year != null && `${car.year} г.`}
                {car.price_rub != null && ` · ${Number(car.price_rub).toLocaleString('ru-RU')} ₽`}
              </p>
              <p className={styles.specs}>
                {[car.body_type, car.fuel_type, car.transmission].filter(Boolean).join(' · ')}
              </p>
              {(car.engine_volume != null || car.horsepower != null || car.modification) && (
                <p className={styles.specs}>
                  {car.engine_volume != null && `${car.engine_volume} л`}
                  {car.engine_volume != null && car.horsepower != null && ' · '}
                  {car.horsepower != null && `${car.horsepower} л.с.`}
                  {car.modification && !car.engine_volume && !car.horsepower ? car.modification : null}
                </p>
              )}
              {car.description && (
                <p className={styles.description}>{car.description}</p>
              )}
            </div>
          </article>
        ))}
      </div>
      {selectedCar && (
        <CarDetailModal car={selectedCar} onClose={() => setSelectedCar(null)} />
      )}
    </div>
  );
}
