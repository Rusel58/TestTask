from django.db import models
from shapely import wkt
from shapely.geometry import Point, Polygon

# Справочник моделей самосвалов
class TruckModel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    max_capacity = models.PositiveIntegerField(
        verbose_name='Макс. грузоподъёмность (т)'
    )

    class Meta:
        verbose_name = 'Модель самосвала'
        verbose_name_plural = 'Модели самосвалов'

    def __str__(self):
        return f'{self.name} ({self.max_capacity} т)'


# Самосвал
class Truck(models.Model):
    board_number = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Бортовой номер'
    )
    model = models.ForeignKey(
        TruckModel,
        on_delete=models.PROTECT,
        verbose_name='Модель'
    )
    current_load = models.PositiveIntegerField(
        verbose_name='Текущий вес груза (т)'
    )
    # Процентное содержание SiO2 и Fe в грузе
    percent_sio2 = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='% SiO2'
    )
    percent_fe = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='% Fe'
    )

    class Meta:
        verbose_name = 'Самосвал'
        verbose_name_plural = 'Самосвалы'

    def __str__(self):
        return f'{self.board_number} ({self.model.name})'


# Склад
class Warehouse(models.Model):
    # Название склада
    name = models.CharField(max_length=100, default='Основной склад')
    # Текущий объём на складе (т)
    volume = models.FloatField(verbose_name='Объём до разгрузки (т)')
    # Процентное содержание SiO2 и Fe
    percent_sio2 = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='% SiO2'
    )
    percent_fe = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='% Fe'
    )
    # Полигон в виде WKT-строки (Polygon ((x1 y1, x2 y2, ...)))
    polygon_wkt = models.TextField(
        verbose_name='Полигон склада (WKT)',
        help_text='Например: POLYGON((30 10, 40 40, 20 40, 10 20, 30 10))'
    )

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'

    def __str__(self):
        return self.name

    # Метод, который возвращает объект Shapely-атрибута Polygon
    def get_polygon(self) -> Polygon:
        try:
            return wkt.loads(self.polygon_wkt)
        except Exception:
            return None


# Событие разгрузки
class UnloadingEvent(models.Model):
    truck = models.ForeignKey(
        Truck,
        on_delete=models.CASCADE,
        verbose_name='Самосвал'
    )
    coord_input = models.CharField(
        max_length=50,
        verbose_name='Координаты разгрузки (X Y)',
        help_text='Ввод формата "X Y", например "30 20"'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время запроса'
    )
    # Флаг: попал ли в полигон
    is_inside = models.BooleanField(
        default=False,
        verbose_name='Попал в полигон'
    )

    class Meta:
        verbose_name = 'Событие разгрузки'
        verbose_name_plural = 'События разгрузок'
        ordering = ['-timestamp']

    def __str__(self):
        return f'Разгрузка {self.truck.board_number} в "{self.coord_input}"'

    # Дополнительный метод: получить точку Shapely из coord_input
    def get_point(self):
        try:
            x_str, y_str = self.coord_input.split()
            x, y = float(x_str), float(y_str)
            return Point(x, y)
        except Exception:
            return None

    # Метод для проверки попадания в полигон склада
    def check_inside_polygon(self, warehouse: Warehouse) -> bool:
        poly = warehouse.get_polygon()
        pt = self.get_point()
        if poly and pt:
            # Попадание на границу считается попаданием, поэтому используем .contains OR .touches
            return poly.contains(pt) or poly.touches(pt)
        return False
