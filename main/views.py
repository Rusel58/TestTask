from django.shortcuts import render
from .models import Truck, Warehouse, UnloadingEvent

def index(request):
    """
    Главная страница:
    - GET: отображаем Таблицу 1 (все самосвалы + поля для ввода координат).
    - POST: обрабатываем введённые координаты, создаём UnloadingEvent,
      проверяем вхождение в полигон, рассчитываем результаты, отображаем Таблицу 2.
    """
    # Получим "единственный" склад (предполагается, что он один).
    warehouse = Warehouse.objects.first()
    if warehouse is None:
        # Если склада нет — можно вывести ошибку или просто создать дефолтный объект.
        return render(request, 'no_warehouse.html')

    # Получаем все самосвалы для отображения
    trucks = Truck.objects.select_related('model').all()

    context = {
        'trucks': trucks,
        'warehouse': warehouse,
        # Результаты расчёта добавим в context, но пока он пустой
        'result': None,
    }

    if request.method == 'POST':
        # Обработка нажатия "Рассчитать"
        # Перебираем все самосвалы и смотрим, что ввёл пользователь
        total_added_volume = 0.0
        # Для расчёта нового качества — нам нужно взвешенное усреднение
        # храним сумму (масса * %SiO2) и (масса * %Fe) по включённым самосвалам
        sum_sio2_mass = 0.0
        sum_fe_mass = 0.0

        # Суммарный список обработанных событий, чтобы отобразить (необязательно)
        events = []

        for truck in trucks:
            key = f'coord_{truck.id}'
            coord_str = request.POST.get(key, '').strip()
            if not coord_str:
                # Пользователь ничего не указал — пропускаем
                continue

            # Создаём событие разгрузки (не знаем ещё, внутри или нет)
            event = UnloadingEvent(truck=truck, coord_input=coord_str)

            # Проверим, можем ли распарсить, и попадает ли в полигон
            pt = event.get_point()
            if pt is None:
                # Некорректный ввод (не удалось распарсить X Y) — считаем непринятым в полигон
                event.is_inside = False
                event.save()
                events.append(event)
                continue

            # Получаем полигон склада и проверяем
            poly = warehouse.get_polygon()
            if poly is None:
                event.is_inside = False
                event.save()
                events.append(event)
                continue

            # Попадание на границу считается попаданием (contains OR touches)
            if poly.contains(pt) or poly.touches(pt):
                event.is_inside = True
                # Если самосвал попал — добавляем его current_load в итог
                added = float(truck.current_load)
                total_added_volume += added
                # Учитываем качественные характеристики
                # %SiO2 (truck.percent_sio2) в форме Decimal, приводим к float
                sio2 = float(truck.percent_sio2)
                fe = float(truck.percent_fe)
                sum_sio2_mass += added * sio2 / 100.0  # масса чистого вещества SiO2
                sum_fe_mass += added * fe / 100.0      # масса чистого вещества Fe
            else:
                event.is_inside = False

            # Сохраняем событие (с флагом is_inside)
            event.save()
            events.append(event)

        # После цикла у нас есть:
        # - total_added_volume (тонн)
        # - sum_sio2_mass (тонн чистого SiO2)
        # - sum_fe_mass   (тонн чистого Fe)
        # Текущие складские показатели:
        init_vol = float(warehouse.volume)
        init_sio2 = float(warehouse.percent_sio2)
        init_fe = float(warehouse.percent_fe)
        # Вычислим массы чистого вещества на складе до разгрузки:
        init_mass_sio2 = init_vol * init_sio2 / 100.0
        init_mass_fe = init_vol * init_fe / 100.0

        # Итоговый общий объём
        final_volume = init_vol + total_added_volume

        # Итоговые массы чистого вещества
        total_mass_sio2 = init_mass_sio2 + sum_sio2_mass
        total_mass_fe = init_mass_fe + sum_fe_mass

        # Итоговые проценты (если итоговый объём > 0)
        if final_volume > 0:
            final_sio2_pct = (total_mass_sio2 / final_volume) * 100.0
            final_fe_pct = (total_mass_fe / final_volume) * 100.0
        else:
            final_sio2_pct = 0.0
            final_fe_pct = 0.0

        # Составим словарь результата для передачи в шаблон
        result = {
            'initial_volume': init_vol,
            'initial_sio2': init_sio2,
            'initial_fe': init_fe,
            'added_volume': total_added_volume,
            'final_volume': final_volume,
            'final_sio2': round(final_sio2_pct, 2),
            'final_fe': round(final_fe_pct, 2),
            'events': events,  # чтобы видеть, кто попал, кто нет
        }

        context['result'] = result

    return render(request, 'main.html', context)
