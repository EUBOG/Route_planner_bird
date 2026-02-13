import csv
import os


def parse_csv_file(filepath):
    """
    Парсинг CSV файла с координатами

    Ожидаемый формат CSV:
    address,latitude,longitude
    "ул. Ленина, 1",55.7558,37.6173
    "Тверская ул., 13",55.7652,37.6010

    Возвращает:
        список словарей {'address': str, 'latitude': float, 'longitude': float}
    """
    waypoints = []

    if not os.path.exists(filepath):
        raise FileNotFoundError(f'Файл не найден: {filepath}')

    with open(filepath, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        # Проверка наличия необходимых колонок
        required_columns = {'address', 'latitude', 'longitude'}
        if not required_columns.issubset(set(reader.fieldnames)):
            raise ValueError(
                f'CSV файл должен содержать колонки: {", ".join(required_columns)}. '
                f'Найдены: {", ".join(reader.fieldnames)}'
            )

        for row_num, row in enumerate(reader, start=2):  # start=2 т.к. 1 строка — заголовок
            try:
                address = row['address'].strip()
                latitude = float(row['latitude'].strip())
                longitude = float(row['longitude'].strip())

                # Валидация координат
                if not (-90 <= latitude <= 90):
                    raise ValueError(f'Неверная широта в строке {row_num}: {latitude}')
                if not (-180 <= longitude <= 180):
                    raise ValueError(f'Неверная долгота в строке {row_num}: {longitude}')

                waypoints.append({
                    'address': address,
                    'latitude': latitude,
                    'longitude': longitude
                })

            except (ValueError, KeyError) as e:
                raise ValueError(f'Ошибка в строке {row_num}: {str(e)}')

    if not waypoints:
        raise ValueError('CSV файл не содержит данных')

    return waypoints