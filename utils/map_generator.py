import folium
from folium.plugins import MarkerCluster, PolyLineTextPath


def create_route_map(waypoints, route_name="Маршрут"):
    """
    Создание интерактивной карты маршрута с использованием folium

    Аргументы:
        waypoints: список объектов Waypoint, отсортированных по order_index
        route_name: название маршрута для заголовка

    Возвращает:
        объект карты folium.Map
    """
    if not waypoints:
        raise ValueError("Список точек пуст")

    # Определяем центр карты (среднее значение координат)
    avg_lat = sum(wp.latitude for wp in waypoints) / len(waypoints)
    avg_lon = sum(wp.longitude for wp in waypoints) / len(waypoints)

    # Создаем карту
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=13,
        tiles='OpenStreetMap',  # Можно заменить на 'CartoDB positron' для другого стиля
        control_scale=True
    )

    # Координаты для линии маршрута
    route_coords = [[wp.latitude, wp.longitude] for wp in waypoints]

    # Добавляем линию маршрута
    folium.PolyLine(
        route_coords,
        weight=4,
        color='#667eea',
        opacity=0.8,
        dash_array='5, 10',
        popup=f'Маршрут: {route_name}<br>Точек: {len(waypoints)}'
    ).add_to(m)

    # Добавляем стрелки направления движения
    for i in range(len(route_coords) - 1):
        start = route_coords[i]
        end = route_coords[i + 1]

        # Создаем линию с текстом-стрелкой
        line = folium.PolyLine(
            [start, end],
            weight=0,
            color='transparent'
        ).add_to(m)

        PolyLineTextPath(
            line,
            '➤',
            offset=8,
            attributes={
                'fill': '#667eea',
                'font-weight': 'bold',
                'font-size': '20px'
            }
        ).add_to(m)

    # Добавляем маркеры для каждой точки
    for idx, wp in enumerate(waypoints):
        # Определяем иконку в зависимости от позиции
        if idx == 0:
            # Первая точка — зелёный маркер (старт)
            icon = folium.Icon(icon='play', prefix='fa', color='green')
            popup_text = f'<b>🏁 СТАРТ</b><br>{wp.address}<br><small>Позиция: {idx + 1}</small>'
        elif idx == len(waypoints) - 1:
            # Последняя точка — красный маркер (финиш)
            icon = folium.Icon(icon='flag-checkered', prefix='fa', color='red')
            popup_text = f'<b>🏁 ФИНИШ</b><br>{wp.address}<br><small>Позиция: {idx + 1}</small>'
        else:
            # Промежуточные точки — синие маркеры
            icon = folium.Icon(icon='map-marker', prefix='fa', color='blue')
            popup_text = f'<b>📍 Точка {idx + 1}</b><br>{wp.address}'

        # Создаем маркер
        marker = folium.Marker(
            location=[wp.latitude, wp.longitude],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f'{idx + 1}. {wp.address}',
            icon=icon
        )
        marker.add_to(m)

        # Добавляем номер рядом с маркером
        folium.Marker(
            location=[wp.latitude, wp.longitude],
            icon=folium.DivIcon(
                html=f'''<div style="
                    font-weight: bold;
                    font-size: 14px;
                    color: white;
                    background-color: #667eea;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-top: -28px;
                    margin-left: 8px;
                ">{idx + 1}</div>'''
            )
        ).add_to(m)

    # Добавляем легенду
    legend_html = '''
    <div style="
        position: fixed;
        bottom: 50px;
        right: 10px;
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 9999;
        font-family: Arial, sans-serif;
        font-size: 12px;
    ">
        <b style="color: #333;">Легенда:</b><br>
        <span style="color: green;">🟢</span> Старт<br>
        <span style="color: blue;">🔵</span> Промежуточная точка<br>
        <span style="color: red;">🔴</span> Финиш
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Добавляем информацию о маршруте
    info_html = f'''
    <div style="
        position: fixed;
        top: 10px;
        right: 10px;
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 9999;
        font-family: Arial, sans-serif;
        font-size: 13px;
    ">
        <b style="color: #667eea;">🚚 Route Planner</b><br>
        <b>Маршрут:</b> {route_name}<br>
        <b>Точек:</b> {len(waypoints)}<br>
        <b>Дистанция:</b> {sum(
        haversine_distance(
            waypoints[i].latitude, waypoints[i].longitude,
            waypoints[i + 1].latitude, waypoints[i + 1].longitude
        )
        for i in range(len(waypoints) - 1)
    ):.2f} км
    </div>
    '''
    m.get_root().html.add_child(folium.Element(info_html))

    # Добавляем масштаб и полноэкранный режим
    folium.LatLngPopup().add_to(m)
    folium.plugins.Fullscreen(
        position='topright',
        title='Полный экран',
        title_cancel='Закрыть',
        force_separate_button=True
    ).add_to(m)

    return m


def haversine_distance(lat1, lon1, lat2, lon2):
    """Вспомогательная функция для расчёта расстояния (км)"""
    import math
    R = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c