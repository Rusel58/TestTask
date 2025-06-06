from django.contrib import admin
from .models import TruckModel, Truck, Warehouse, UnloadingEvent

@admin.register(TruckModel)
class TruckModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_capacity')
    search_fields = ('name',)

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('board_number', 'model', 'current_load', 'percent_sio2', 'percent_fe')
    list_filter = ('model',)
    search_fields = ('board_number',)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'volume', 'percent_sio2', 'percent_fe')

@admin.register(UnloadingEvent)
class UnloadingEventAdmin(admin.ModelAdmin):
    list_display = ('truck', 'coord_input', 'is_inside', 'timestamp')
    list_filter = ('is_inside', 'timestamp')
    search_fields = ('truck__board_number', 'coord_input')
