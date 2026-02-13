import requests
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()  # Загрузка переменных из .env

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"
DIRECTIONS_URL = "https://api.routing.yandex.net/v2/route"


def get_route_by_roads(waypoints: List[Dict]) -> Optional[Dict]:
    logger.debug(f"Запрос маршрута по дорогам для {len(waypoints)} точек")
    logger.debug(f"Точки: {waypoints}")
    """
    Построение маршрута по дорогам через Яндекс Directions API
    Args:
        waypoints: список {'latitude': float, 'longitude': float, 'address': str}
    Returns:
        Словарь с данными маршрута или None при ошибке
    """
    if len(waypoints) < 2:
        return None

    # Формируем точки маршрута в формате Яндекса
    points = [{"lat": wp["latitude"], "lon": wp["longitude"]} for wp in waypoints]

    params = {
        "apikey": YANDEX_API_KEY,
        "waypoints": points,
        "mode": "driving"  # driving, walking, cycling
    }

    try:
        response = requests.post(DIRECTIONS_URL, json=params, timeout=10)
        logger.debug(f"Статус ответа Яндекс: {response.status_code}")
        logger.debug(f"Ответ: {response.text[:500]}")  # Первые 500 символов
        response.raise_for_status()
        data = response.json()

        # Извлекаем данные маршрута
        route = data["routes"][0]
        distance_km = route["summary"]["distance"] / 1000
        duration_min = route["summary"]["duration"] / 60

        # Координаты для отрисовки линии маршрута
        geometry = route["geometry"]

        return {
            "distance_km": round(distance_km, 2),
            "duration_min": round(duration_min, 1),
            "geometry": geometry,  # Массив координат для линии
            "legs": route["legs"]  # Отрезки между точками
        }

    except requests.RequestException as e:
        logger.error(f"Ошибка запроса к Яндекс API: {e}")
        logger.error(f"URL: {DIRECTIONS_URL}")
        logger.error(f"API Key present: {bool(YANDEX_API_KEY)}")
        return None