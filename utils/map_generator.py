import folium
from folium.plugins import AntPath
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def create_route_map(waypoints: List, route_name: str, yandex_geometry: Optional[List] = None):
    """Создание интерактивной карты маршрута

    Args:
        waypoints: список точек маршрута
        route_name: название маршрута
        yandex_geometry: геометрия маршрута от Яндекс API (если есть)

    Returns:
        Объект карты folium
    """
    if not waypoints:
        raise ValueError("Список точек не может быть пустым")

    # Центрируем карту на первой точке
    start_lat = waypoints[0].latitude
    start_lon = waypoints[0].longitude

    # Создаем карту
    m = folium.Map(
        location=[start_lat, start_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )

    # === Если есть геометрия от Яндекса - рисуем маршрут по дорогам ===
    if yandex_geometry:
        logger.debug(f"Отрисовка маршрута по дорогам, {len(yandex_geometry)} точек")

        # Преобразуем геометрию в формат [широта, долгота]
        # Яндекс возвращает массив точек в формате {"lat": ..., "lon": ...}
        if isinstance(yandex_geometry[0], dict):
            route_coords = [[point["lat"], point["lon"]] for point in yandex_geometry]
        else:
            # Если уже в правильном формате
            route_coords = yandex_geometry

        # Рисуем линию маршрута по дорогам (синяя)
        folium.PolyLine(
            locations=route_coords,
            color='blue',
            weight=5,
            opacity=0.8,
            popup=f'Маршрут по дорогам',
            tooltip='🛣️ Маршрут по дорогам'
        ).add_to(m)

        logger.debug(f"Маршрут по дорогам добавлен на карту")

    # === Рисуем точки маршрута ===
    for idx, wp in enumerate(waypoints):
        popup_text = f"""
        <b>Точка {idx + 1}</b><br>
        Адрес: {wp.address}<br>
        Координаты: {wp.latitude:.6f}, {wp.longitude:.6f}
        """

        # Разные цвета для первой и последней точек
        if idx == 0:
            color = 'green'
            icon = 'play'
            popup_text = f'<b>Старт</b><br>{popup_text}'
        elif idx == len(waypoints) - 1:
            color = 'red'
            icon = 'flag'
            popup_text = f'<b>Финиш</b><br>{popup_text}'
        else:
            color = 'blue'
            icon = 'info-sign'

        folium.Marker(
            location=[wp.latitude, wp.longitude],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f'Точка {idx + 1}: {wp.address}',
            icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
        ).add_to(m)

    # === Если НЕТ геометрии от Яндекса - рисуем маршрут по прямой ===
    if not yandex_geometry and len(waypoints) > 1:
        logger.debug("Отрисовка маршрута по прямой (птичий полёт)")

        # Собираем координаты для линии
        route_coords = [[wp.latitude, wp.longitude] for wp in waypoints]

        # Рисуем линию маршрута (оранжевая пунктирная)
        folium.PolyLine(
            locations=route_coords,
            color='orange',
            weight=3,
            opacity=0.7,
            dash_array='5, 5',
            popup=f'Маршрут по прямой',
            tooltip='📏 Птичий полёт'
        ).add_to(m)

        # Добавляем стрелки направления
        for i in range(len(route_coords) - 1):
            start = route_coords[i]
            end = route_coords[i + 1]

            AntPath(
                locations=[start, end],
                dash_array=[10, 20],
                delay=1000,
                color='orange',
                weight=0,
                pulse_color='darkorange'
            ).add_to(m)

    # Добавляем заголовок карты
    title_html = f'''
        <h3 align="center" style="font-size:20px">
            <b>{route_name}</b>
            {' 🛣️ Маршрут по дорогам' if yandex_geometry else ' 📏 Маршрут по прямой'}
        </h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Добавляем легенду
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; 
                background-color: white; 
                border:2px solid grey; 
                z-index:9999; 
                font-size:14px;
                padding: 10px;">
    <p><i class="fa fa-circle" style="color:green"></i> Старт</p>
    <p><i class="fa fa-circle" style="color:blue"></i> Промежуточная точка</p>
    <p><i class="fa fa-circle" style="color:red"></i> Финиш</p>
    <p><span style="color:blue">━━━━</span> Маршрут по дорогам</p>
    <p><span style="color:orange">- - -</span> Маршрут по прямой</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m