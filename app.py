from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename
from models import db, Route, Waypoint
from utils.csv_parser import parse_csv_file
from utils.map_generator import create_route_map
from algorithms.tsp_solver import solve_tsp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///routes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAP_FOLDER'] = 'static/maps'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MAP_FOLDER'], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()


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


@app.route('/result/<int:route_id>')
def result(route_id):
    """Страница с результатом маршрута"""
    route = Route.query.get_or_404(route_id)
    waypoints = Waypoint.query.filter_by(route_id=route_id).order_by(Waypoint.order_index).all()

    total_distance = route.calculate_total_distance()

    try:
        map_obj = create_route_map(waypoints, route.name)

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
        map_url=map_url
    )


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)