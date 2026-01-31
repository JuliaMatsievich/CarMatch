import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CarResults } from "./CarResults";
import type { CarResult } from "../../api/cars";

describe("CarResults", () => {
  it("returns null when cars array is empty", () => {
    const { container } = render(<CarResults cars={[]} />);

    expect(container.firstChild).toBeNull();
  });

  it("renders car cards with mark, model, year and price", () => {
    const cars: CarResult[] = [
      {
        id: 1,
        mark_name: "Toyota",
        model_name: "Camry",
        year: 2020,
        price_rub: 2_500_000,
        body_type: "седан",
        fuel_type: "бензин",
        images: null,
      },
    ];

    render(<CarResults cars={cars} />);

    expect(screen.getByText("Подобранные автомобили")).toBeInTheDocument();
    expect(screen.getByText("Toyota Camry")).toBeInTheDocument();
    expect(screen.getByText(/2020 г\./)).toBeInTheDocument();
    expect(screen.getByText(/2\s*500\s*000.*₽/)).toBeInTheDocument();
  });

  it("renders specs when present", () => {
    const cars: CarResult[] = [
      {
        id: 1,
        mark_name: "Honda",
        model_name: "Accord",
        year: 2021,
        price_rub: 3_000_000,
        body_type: "седан",
        fuel_type: "гибрид",
        images: null,
      },
    ];

    render(<CarResults cars={cars} />);

    expect(screen.getByText("седан · гибрид")).toBeInTheDocument();
  });

  it("renders image when available", () => {
    const cars: CarResult[] = [
      {
        id: 1,
        mark_name: "Toyota",
        model_name: "Camry",
        year: 2020,
        price_rub: 2_500_000,
        body_type: null,
        fuel_type: null,
        images: ["https://example.com/car.jpg"],
      },
    ];

    const { container } = render(<CarResults cars={cars} />);
    const img = container.querySelector("img");
    expect(img).toHaveAttribute("src", "https://example.com/car.jpg");
  });

  it("renders multiple cars", () => {
    const cars: CarResult[] = [
      {
        id: 1,
        mark_name: "Toyota",
        model_name: "Camry",
        year: 2020,
        price_rub: 2_500_000,
        body_type: null,
        fuel_type: null,
        images: null,
      },
      {
        id: 2,
        mark_name: "Honda",
        model_name: "Accord",
        year: 2021,
        price_rub: 3_000_000,
        body_type: null,
        fuel_type: null,
        images: null,
      },
    ];

    render(<CarResults cars={cars} />);

    expect(screen.getByText("Toyota Camry")).toBeInTheDocument();
    expect(screen.getByText("Honda Accord")).toBeInTheDocument();
  });
});
