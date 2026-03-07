"""
Заполнение колонки cars.country (страна-производитель).

1) Из поля description: «Выпускается в Франция», «Производство — Германия».
2) Для остальных — по марке (mark_name) из справочника марок и стран.

Запуск из корня carmatch-backend:
  python scripts/populate_cars_country.py
  python scripts/populate_cars_country.py --dry-run
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database import SessionLocal
from src.models import Car

# Марка (как в БД) -> страна-производитель
BRAND_COUNTRY = {
    # Франция
    "Renault": "Франция",
    "Peugeot": "Франция",
    "Citroën": "Франция",
    "Citroen": "Франция",
    "DS": "Франция",
    "Alpine": "Франция",
    "Venturi": "Франция",
    "Matra": "Франция",
    "Simca": "Франция",
    "Talbot": "Франция",
    "Delage": "Франция",
    "Facel Vega": "Франция",
    "PGO": "Франция",
    "Renault Samsung": "Южная Корея",  # Samsung Motors
    "Mobilize": "Франция",
    # Япония
    "Toyota": "Япония",
    "Nissan": "Япония",
    "Honda": "Япония",
    "Mazda": "Япония",
    "Subaru": "Япония",
    "Mitsubishi": "Япония",
    "Suzuki": "Япония",
    "Lexus": "Япония",
    "Acura": "Япония",
    "Daihatsu": "Япония",
    "Infiniti": "Япония",
    "Isuzu": "Япония",
    "Scion": "Япония",
    "Datsun": "Япония",
    "Mitsuoka": "Япония",
    "Ciimo (Dongfeng-Honda)": "Китай",
    # Германия
    "BMW": "Германия",
    "Mercedes-Benz": "Германия",
    "Volkswagen": "Германия",
    "Audi": "Германия",
    "Opel": "Германия",
    "Porsche": "Германия",
    "Smart": "Германия",
    "Alpina": "Германия",
    "Maybach": "Германия",
    "Borgward": "Германия",
    "Wiesmann": "Германия",
    "Bitter": "Германия",
    "Hanomag": "Германия",
    "Horch": "Германия",
    "Wanderer": "Германия",
    "DKW": "Германия",
    "Auto Union": "Германия",
    "Steyr": "Австрия",
    "Brabus": "Германия",
    "Rinspeed": "Швейцария",
    "Isdera": "Германия",
    "Goggomobil": "Германия",
    "Heinkel": "Германия",
    "Trabant": "ГДР",
    "Wartburg": "ГДР",
    # Чехия / Словакия
    "Škoda": "Чехия",
    "Skoda": "Чехия",
    "Tatra": "Чехия",
    # Южная Корея
    "Hyundai": "Южная Корея",
    "Kia": "Южная Корея",
    "Genesis": "Южная Корея",
    "Daewoo": "Южная Корея",
    "SsangYong": "Южная Корея",
    # США
    "Chevrolet": "США",
    "Ford": "США",
    "Jeep": "США",
    "Tesla": "США",
    "Cadillac": "США",
    "Buick": "США",
    "GMC": "США",
    "Chrysler": "США",
    "Dodge": "США",
    "Ram": "США",
    "Lincoln": "США",
    "Hummer": "США",
    "Mercury": "США",
    "Pontiac": "США",
    "Saturn": "США",
    "Oldsmobile": "США",
    "Plymouth": "США",
    "Eagle": "США",
    "AMC": "США",
    "AM General": "США",
    "DeSoto": "США",
    "Hudson": "США",
    "Nash": "США",
    "Packard": "США",
    "Studebaker": "США",
    "Willys": "США",
    "Geo": "США",
    "Scout": "США",
    "Hennessey": "США",
    "Saleen": "США",
    "Fisker": "США",
    "Lucid": "США",
    "Rivian": "США",
    "Coda": "США",
    "Rezvani": "США",
    "Vector": "США",
    "Panoz": "США",
    "Excalibur": "США",
    "Franklin": "США",
    "Cord": "США",
    "Pierce-Arrow": "США",
    "International Harvester": "США",
    "Sears": "США",
    "Batmobile": "США",
    # Италия
    "Fiat": "Италия",
    "Alfa Romeo": "Италия",
    "Ferrari": "Италия",
    "Lamborghini": "Италия",
    "Lancia": "Италия",
    "Maserati": "Италия",
    "Abarth": "Италия",
    "De Tomaso": "Италия",
    "Pagani": "Италия",
    "Cizeta": "Италия",
    "Innocenti": "Италия",
    "Autobianchi": "Италия",
    "Bertone": "Италия",
    "Pininfarina": "Италия",
    "Dallara": "Италия",
    "Iveco": "Италия",
    "Piaggio": "Италия",
    # Великобритания
    "Land Rover": "Великобритания",
    "Jaguar": "Великобритания",
    "Mini": "Великобритания",
    "Bentley": "Великобритания",
    "Rolls-Royce": "Великобритания",
    "Aston Martin": "Великобритания",
    "Lotus": "Великобритания",
    "McLaren": "Великобритания",
    "Morgan": "Великобритания",
    "Caterham": "Великобритания",
    "Noble": "Великобритания",
    "TVR": "Великобритания",
    "Rover": "Великобритания",
    "Vauxhall": "Великобритания",
    "AC": "Великобритания",
    "Ariel": "Великобритания",
    "Austin": "Великобритания",
    "Austin Healey": "Великобритания",
    "Bristol": "Великобритания",
    "Carbodies": "Великобритания",
    "Jensen": "Великобритания",
    "LTI": "Великобритания",
    "Marcos": "Великобритания",
    "Marlin": "Великобритания",
    "Metrocab": "Великобритания",
    "Morris": "Великобритания",
    "Radford": "Великобритания",
    "Ronart": "Великобритания",
    "Spectre": "Великобритания",
    "Ultima": "Великобритания",
    "Daimler": "Великобритания",
    # Швеция
    "Volvo": "Швеция",
    "Saab": "Швеция",
    "Koenigsegg": "Швеция",
    # Румыния
    "Dacia": "Румыния",
    "Aro": "Румыния",
    "Oltcit": "Румыния",
    # Россия
    "Lada": "Россия",
    "ВАЗ": "Россия",
    "UAZ": "Россия",
    "GAZ": "Россия",
    "Aurus": "Россия",
    "Derways": "Россия",
    "Marussia": "Россия",
    "Volga": "Россия",
    "Vortex": "Россия",
    "Evolute": "Россия",
    "Sollers": "Россия",
    "Doninvest": "Россия",
    "Bilenkin": "Россия",
    "Lada (Нива)": "Россия",
    "Нива": "Россия",
    "Лада": "Россия",
    "УАЗ": "Россия",
    "ГАЗ": "Россия",
    "ТагАЗ": "Россия",
    "Иж": "Россия",
    "Москвич": "Россия",
    "Ока": "Россия",
    "Северсталь-Авто": "Россия",
    # Китай
    "Geely": "Китай",
    "Chery": "Китай",
    "Haval": "Китай",
    "FAW": "Китай",
    "Lifan": "Китай",
    "BYD": "Китай",
    "Changan": "Китай",
    "Dongfeng": "Китай",
    "GAC": "Китай",
    "GAC Aion": "Китай",
    "GAC Trumpchi": "Китай",
    "Nio": "Китай",
    "Xpeng": "Китай",
    "Li Auto (Lixiang)": "Китай",
    "Hongqi": "Китай",
    "Jetour": "Китай",
    "JETOUR": "Китай",
    "Exeed": "Китай",
    "Omoda": "Китай",
    "Jaecoo": "Китай",
    "Tank": "Китай",
    "Wey": "Китай",
    "Zeekr": "Китай",
    "Lynk & Co": "Китай",
    "Livan": "Китай",
    "Voyah": "Китай",
    "Leapmotor": "Китай",
    "Seres": "Китай",
    "Aito": "Китай",
    "Avatr": "Китай",
    "Baojun": "Китай",
    "Bestune": "Китай",
    "Brilliance": "Китай",
    "Chana": "Китай",
    "Changfeng": "Китай",
    "Changhe": "Китай",
    "Cowin": "Китай",
    "Dayun": "Китай",
    "Denza": "Китай",
    "Dongfeng": "Китай",
    "Enovate (Enoreve)": "Китай",
    "Forthing": "Китай",
    "Foton": "Китай",
    "Gonow": "Китай",
    "Great Wall": "Китай",
    "Hafei": "Китай",
    "Haima": "Китай",
    "Hanteng": "Китай",
    "Hawtai": "Китай",
    "HiPhi": "Китай",
    "Hozon": "Китай",
    "Hycan": "Китай",
    "iCar": "Китай",
    "iCaur": "Китай",
    "IM Motors (Zhiji)": "Китай",
    "JAC": "Китай",
    "Jidu": "Китай",
    "Jinbei": "Китай",
    "JMC": "Китай",
    "JMEV": "Китай",
    "Jonway": "Китай",
    "Kaiyi": "Китай",
    "Karma": "США",
    "Letin": "Китай",
    "Lingxi": "Китай",
    "Luxeed": "Китай",
    "Maple": "Китай",
    "Shanghai Maple": "Китай",
    "Maxus": "Китай",
    "M-Hero": "Китай",
    "Nio": "Китай",
    "Ora": "Китай",
    "Oshan": "Китай",
    "Qiantu": "Китай",
    "Qoros": "Китай",
    "Radar": "Китай",
    "Rising Auto": "Китай",
    "Roewe": "Китай",
    "SAIC": "Китай",
    "Seres": "Китай",
    "Skywell": "Китай",
    "Stelato": "Китай",
    "SWM": "Китай",
    "Tank": "Китай",
    "TENET": "Китай",
    "Venucia": "Китай",
    "VGV": "Китай",
    "Weltmeister": "Китай",
    "Wuling": "Китай",
    "Xiaomi": "Китай",
    "Xin Kai": "Китай",
    "Yema": "Китай",
    "Zhido": "Китай",
    "Zotye": "Китай",
    "ZX": "Китай",
    "Aiways": "Китай",
    "Arcfox": "Китай",
    "BAIC": "Китай",
    "BAW": "Китай",
    "Blaval": "Китай",
    "DW Hover": "Китай",
    "DW Hower": "Китай",
    "Eonyx": "Китай",
    "Polar Stone (Jishi)": "Китай",
    "ShuangHuan": "Китай",
    "Tianma": "Китай",
    "Yudo": "Китай",
    "Mega": "Китай",
    "Orange": "Китай",
    "Oting": "Китай",
    "Rox": "Китай",
    "Knewstar": "Китай",
    "Kawei": "Китай",
    "KYC": "Китай",
    "Maextro": "Китай",
    "Micro": "Китай",
    "Minelli": "Китай",
    "Renaissance": "Китай",
    # Индия
    "Tata": "Индия",
    "Mahindra": "Индия",
    "Maruti": "Индия",
    "Hindustan": "Индия",
    "Premier": "Индия",
    "Bajaj": "Индия",
    # Малайзия
    "Perodua": "Малайзия",
    "Proton": "Малайзия",
    # Вьетнам
    "VinFast": "Вьетнам",
    # Турция
    "Tofas": "Турция",
    # Иран
    "Iran Khodro": "Иран",
    "Saipa": "Иран",
    # Испания
    "SEAT": "Испания",
    "Cupra": "Испания",
    "Santana": "Испания",
    "Tramontana": "Испания",
    "Hispano-Suiza": "Испания",
    # Нидерланды
    "Spyker": "Нидерланды",
    "Donkervoort": "Нидерланды",
    "Lightyear": "Нидерланды",
    # Бельгия
    "Minerva": "Бельгия",
    # Швейцария
    "Rinspeed": "Швейцария",
    # Австрия
    "KTM AG": "Австрия",
    "Steyr": "Австрия",
    "Puch": "Австрия",
    "GMA": "Австрия",
    # Австралия
    "Holden": "Австралия",
    "HSV": "Австралия",
    "Bufori": "Малайзия",
    # Канада
    # ОАЭ
    "W Motors": "ОАЭ",
    # Хорватия
    "Rimac": "Хорватия",
    # Дания
    "Zenvo": "Дания",
    # Беларусь
    "Belgee": "Беларусь",
    "Zubr": "Беларусь",
    # Латвия
    "Baltijas Dzips": "Латвия",
    # Польша
    "FSO": "Польша",
    # Югославия / Сербия
    "Zastava": "Сербия",
    # Тайвань
    "Luxgen": "Тайвань",
    "Yulon": "Тайвань",
    # Таиланд
    # Египет
    # Разное
    "Microcar": "Франция",
    "Adler": "Германия",
    "Apal": "Бельгия",
    "Bio Auto": "Италия",
    "Coggiola": "Италия",
    "DeLorean": "Ирландия",
    "DR": "Россия",
    "E-Car": "Россия",
    "GP": "Россия",
    "Hedmos": "Греция",
    "Hyperion": "США",
    "Invicta": "Великобритания",
    "Karma": "США",
    "Logem": "Россия",
    "Nordcross": "Россия",
    "Puma": "Бразилия",
    "Punk": "Россия",
    "Qvale": "Италия",
    "Rayton Fissore": "Италия",
    "Rossa": "Россия",
    "Solaris": "Казахстан",
    "Spectre": "Великобритания",
    "Think": "Норвегия",
    "VUHL": "Мексика",
    "Ambertruck": "Россия",
    "Asia": "Южная Корея",
    "Eagle Cars": "Великобритания",
    "Mobilize": "Франция",
    "Jetta": "Китай",
    "MG": "Великобритания",
    "KGM": "Южная Корея",
    "Soueast": "Китай",
    "Triumph": "Великобритания",
    "Landwind": "Китай",
    "Polestar": "Швеция",
    "HuangHai": "Китай",
    "Bugatti": "Франция",
    "Qingling": "Китай",
    "Dadi": "Китай",
    "Ravon": "Узбекистан",
    "Sandstorm": "Россия",
    "Xcite": "Россия",
    "Gordon": "Великобритания",
    "Merkur": "США",
    "Huazi": "Китай",
    "LEVC": "Великобритания",
    "Overland": "США",
    "Jiangnan": "Китай",
    "Humber": "Великобритания",
    "Tazzari": "Италия",
}

# Кириллические названия марок (для машин, загруженных с русскими именами)
BRAND_COUNTRY_CYRILLIC = {
    "Лада": "Россия",
    "Лада (Нива)": "Россия",
    "Нива": "Россия",
    "ВАЗ": "Россия",
    "УАЗ": "Россия",
    "ГАЗ": "Россия",
    "ТагАЗ": "Россия",
    "Иж": "Россия",
    "Москвич": "Россия",
    "Ока": "Россия",
    "Северсталь-Авто": "Россия",
    "Ё-мобиль": "Россия",
    "ЗИЛ": "Россия",
    "Камаз": "Россия",
    "ЛуАЗ": "Россия",
}


def extract_country_from_description(description: str | None) -> str | None:
    if not description or not description.strip():
        return None
    d = description.strip()
    m = re.search(r"\bВыпускается\s+в\s+([^.]+?)(?:\.|$)", d, re.IGNORECASE)
    if m:
        return m.group(1).strip() or None
    m = re.search(r"Производство\s*[—\-]\s*([^.]+?)(?:\.|$)", d)
    if m:
        return m.group(1).strip() or None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнить cars.country")
    parser.add_argument("--dry-run", action="store_true", help="Не сохранять в БД, только вывести план")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        cars = db.query(Car).filter(Car.is_active == True).all()
        from_desc = 0
        from_brand = 0
        skipped = 0

        for car in cars:
            country = getattr(car, "country", None) or None
            if country and str(country).strip():
                skipped += 1
                continue

            # 1) Из description
            extracted = extract_country_from_description(getattr(car, "description", None))
            if extracted:
                if not args.dry_run:
                    car.country = extracted
                from_desc += 1
                continue

            # 2) По марке (латиница и кириллица)
            mark = (getattr(car, "mark_name", None) or "").strip()
            if mark and mark in BRAND_COUNTRY:
                if not args.dry_run:
                    car.country = BRAND_COUNTRY[mark]
                from_brand += 1
                continue
            if mark and mark in BRAND_COUNTRY_CYRILLIC:
                if not args.dry_run:
                    car.country = BRAND_COUNTRY_CYRILLIC[mark]
                from_brand += 1
                continue
            if mark and mark.startswith("Lada"):
                if not args.dry_run:
                    car.country = "Россия"
                from_brand += 1
                continue

        if not args.dry_run:
            db.commit()
            print("Готово. Обновлено записей в БД.")
        else:
            print("Dry-run: изменения не сохранены.")

        print(f"  Из описания: {from_desc}")
        print(f"  По марке:    {from_brand}")
        print(f"  Уже заполнено (пропущено): {skipped}")
        print(f"  Всего машин: {len(cars)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
