import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Расчет расстояния между двумя точками по формуле Haversine
    Возвращает расстояние в километрах
    """
    R = 6371.0  # Радиус Земли в км

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def find_nearest_point(current_point, candidates):
    """
    Находит ближайшую точку к текущей из списка кандидатов
    """
    min_distance = float('inf')
    nearest_point = None
    nearest_index = None

    for idx, point in enumerate(candidates):
        distance = haversine_distance(
            current_point['latitude'], current_point['longitude'],
            point['latitude'], point['longitude']
        )

        if distance < min_distance:
            min_distance = distance
            nearest_point = point
            nearest_index = idx

    return nearest_point, nearest_index


def solve_tsp(waypoints):
    """
    Решение задачи коммивояжёра методом ближайшего соседа

    Аргументы:
        waypoints: список словарей {'address': str, 'latitude': float, 'longitude': float}

    Возвращает:
        упорядоченный список точек (начиная с первой точки из исходного списка)
    """
    if len(waypoints) <= 1:
        return waypoints

    # Начинаем с первой точки
    ordered = [waypoints[0]]
    remaining = waypoints[1:].copy()

    current = waypoints[0]

    # Пока есть непосещенные точки
    while remaining:
        # Находим ближайшую точку
        nearest, idx = find_nearest_point(current, remaining)

        # Добавляем в маршрут
        ordered.append(nearest)
        current = nearest

        # Удаляем из оставшихся
        remaining.pop(idx)

    return ordered