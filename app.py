from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from models import db, Route, Waypoint
from utils.csv_parser import parse_csv_file
from utils.map_generator import create_route_map
from algorithms.tsp_solver import solve_tsp
# Добавляем импорт утилиты яндекса
from utils.yandex_router import get_route_by_roads
from dotenv import load_dotenv

import logging

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Создание приложения
app = Flask(__name__)

# Конфигурация
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///routes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAP_FOLDER'] = 'static/maps'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MAP_FOLDER'], exist_ok=True)


# Инициализация базы данных
# db = SQLAlchemy(app)
db.init_app(app)

with app.app_context():
    db.create_all()

# Убеждаемся, что папка uploads существует
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Импорты утилит
from utils.map_generator import create_route_map
from utils.yandex_router import get_route_by_roads

@app.route('/result/<int:route_id>/roads')
def result_roads(route_id):
    """Версия маршрута с расчётом по дорогам"""
    route = Route.query.get_or_404(route_id)
    waypoints = Waypoint.query.filter_by(route_id=route_id).order_by(Waypoint.order_index).all()

    # Попытка построить маршрут по дорогам через Яндекс
    use_yandex_roads = request.args.get('roads', '0') == '1'
    yandex_route_data = None

    if use_yandex_roads:
        waypoints_data = [{
            'latitude': wp.latitude,
            'longitude': wp.longitude,
            'address': wp.address
        } for wp in waypoints]

        yandex_route_data = get_route_by_roads(waypoints_data)

        if yandex_route_data:
            # Обновляем дистанцию в базе
            route.total_distance = yandex_route_data['distance_km']
            db.session.commit()

    # Передаём yandex_route_data в create_route_map
    map_obj = create_route_map(
        waypoints,
        route.name,
        yandex_geometry=yandex_route_data['geometry'] if yandex_route_data else None
    )

    map_html = map_obj._repr_html_()

    # Передаём данные в шаблон
    return render_template(
        'result.html',
        route=route,
        waypoints=waypoints,
        map_html=map_html,
        yandex_available=yandex_route_data is not None,
        use_yandex_roads=use_yandex_roads
    )

@app.route('/')
def index():
    """Главная страница — форма загрузки CSV"""
    return render_template('index.html')


@app.route('/manual')
def manual_input():
    """Страница ручного ввода точек"""
    return render_template('manual_input.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки CSV файла"""
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    if not file.filename.endswith('.csv'):
        flash('Неверный формат файла. Требуется CSV.', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        waypoints_data = parse_csv_file(filepath)

        if len(waypoints_data) < 2:
            flash('Нужно минимум 2 точки для построения маршрута', 'error')
            os.remove(filepath)
            return redirect(url_for('index'))

        ordered_waypoints = solve_tsp(waypoints_data)

        route = Route(name=filename)
        db.session.add(route)
        db.session.flush()

        for idx, wp in enumerate(ordered_waypoints):
            waypoint = Waypoint(
                route_id=route.id,
                address=wp['address'],
                latitude=wp['latitude'],
                longitude=wp['longitude'],
                order_index=idx
            )
            db.session.add(waypoint)

        db.session.commit()

        os.remove(filepath)

        flash(f'Маршрут успешно рассчитан! Точек: {len(ordered_waypoints)}', 'success')
        return redirect(url_for('result', route_id=route.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка обработки файла: {str(e)}', 'error')
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect(url_for('index'))


@app.route('/manual/submit', methods=['POST'])
def manual_submit():
    """Обработка ручного ввода точек"""
    try:
        # Получаем данные из формы
        addresses = request.form.getlist('address[]')
        latitudes = request.form.getlist('latitude[]')
        longitudes = request.form.getlist('longitude[]')

        # Валидация данных
        waypoints_data = []
        for i in range(len(addresses)):
            address = addresses[i].strip()
            latitude = latitudes[i].strip()
            longitude = longitudes[i].strip()

            if not address or not latitude or not longitude:
                continue

            # Валидация координат
            lat = float(latitude)
            lon = float(longitude)

            if not (-90 <= lat <= 90):
                raise ValueError(f'Неверная широта в точке {i + 1}: {lat}')
            if not (-180 <= lon <= 180):
                raise ValueError(f'Неверная долгота в точке {i + 1}: {lon}')

            waypoints_data.append({
                'address': address,
                'latitude': lat,
                'longitude': lon
            })

        if len(waypoints_data) < 2:
            flash('Нужно минимум 2 точки для построения маршрута', 'error')
            return redirect(url_for('manual_input'))

        # Решение задачи коммивояжёра
        ordered_waypoints = solve_tsp(waypoints_data)

        # Сохранение маршрута в БД
        route = Route(name=f'Ручной маршрут {len(ordered_waypoints)} точек')
        db.session.add(route)
        db.session.flush()

        for idx, wp in enumerate(ordered_waypoints):
            waypoint = Waypoint(
                route_id=route.id,
                address=wp['address'],
                latitude=wp['latitude'],
                longitude=wp['longitude'],
                order_index=idx
            )
            db.session.add(waypoint)

        db.session.commit()

        flash(f'Маршрут успешно рассчитан! Точек: {len(ordered_waypoints)}', 'success')
        return redirect(url_for('result', route_id=route.id))

    except ValueError as e:
        db.session.rollback()
        flash(f'Ошибка валидации: {str(e)}', 'error')
        return redirect(url_for('manual_input'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка обработки: {str(e)}', 'error')
        return redirect(url_for('manual_input'))


@app.route('/result/<int:route_id>/yandex')
def result_yandex(route_id):
    """Маршрут по дорогам через JavaScript API Яндекс.Карт"""
    route = Route.query.get_or_404(route_id)
    waypoints = Waypoint.query.filter_by(route_id=route_id).order_by(Waypoint.order_index).all()

    # Получаем JavaScript API ключ из .env
    yandex_api_key_js = os.getenv('YANDEX_API_KEY_JS')

    return render_template(
        'result_yandex.html',
        route=route,
        waypoints=waypoints,
        YANDEX_API_KEY_JS=yandex_api_key_js
    )


@app.route('/result/<int:route_id>')
def result(route_id):
    """Страница с результатом маршрута"""
    route = Route.query.get_or_404(route_id)
    waypoints = Waypoint.query.filter_by(route_id=route_id).order_by(Waypoint.order_index).all()

    use_yandex_roads = request.args.get('roads', '0') == '1'
    yandex_route_data = None

    if use_yandex_roads:
        logger.info(f"Запрос маршрута по дорогам для route_id={route_id}")
        waypoints_data = [{
            'latitude': wp.latitude,
            'longitude': wp.longitude,
            'address': wp.address
        } for wp in waypoints]

        yandex_route_data = get_route_by_roads(waypoints_data)

        if yandex_route_data:
            logger.info(f"Маршрут по дорогам получен: {yandex_route_data['distance_km']} км")
            route.total_distance = yandex_route_data['distance_km']
            db.session.commit()
        else:
            logger.warning("Не удалось получить маршрут по дорогам от Яндекс")

    total_distance = route.calculate_total_distance() if not yandex_route_data else yandex_route_data['distance_km']

    try:
        map_obj = create_route_map(
            waypoints,
            route.name,
            yandex_geometry=yandex_route_data['geometry'] if yandex_route_data else None
        )

        map_filename = f'route_{route_id}.html'
        map_path = os.path.join(app.config['MAP_FOLDER'], map_filename)
        map_obj.save(map_path)

        map_url = url_for('static', filename=f'maps/{map_filename}')
    except Exception as e:
        flash(f'Ошибка генерации карты: {str(e)}', 'warning')
        map_url = None

    return render_template(
        'result.html',
        route=route,
        waypoints=waypoints,
        total_distance=total_distance,
        map_url=map_url,
        yandex_available = yandex_route_data is not None,
        use_yandex_roads = use_yandex_roads
    )


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)