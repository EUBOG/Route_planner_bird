from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import math

db = SQLAlchemy()


class Route(db.Model):
    """Маршрут"""
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_distance = db.Column(db.Float)  # Общее расстояние в км

    # Связь с точками маршрута
    waypoints = db.relationship('Waypoint', backref='route', lazy=True, cascade='all, delete-orphan')

    def calculate_total_distance(self):
        """Расчет общей дистанции маршрута в километрах"""
        waypoints = Waypoint.query.filter_by(route_id=self.id).order_by(Waypoint.order_index).all()

        if len(waypoints) < 2:
            return 0.0

        total = 0.0
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            distance = self._haversine_distance(wp1.latitude, wp1.longitude, wp2.latitude, wp2.longitude)
            total += distance

        self.total_distance = round(total, 2)
        db.session.commit()
        return self.total_distance

    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2):
        """
        Расчет расстояния между двумя точками по формуле Haversine
        Возвращает расстояние в километрах
        """
        # Радиус Земли в км
        R = 6371.0

        # Преобразование градусов в радианы
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Разница координат
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Формула Haversine
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance

    def __repr__(self):
        return f'<Route {self.id}: {self.name}>'


class Waypoint(db.Model):
    """Точка маршрута (адрес с координатами)"""
    __tablename__ = 'waypoints'

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    order_index = db.Column(db.Integer, nullable=False)  # Порядок в маршруте

    def __repr__(self):
        return f'<Waypoint {self.id}: {self.address}>'