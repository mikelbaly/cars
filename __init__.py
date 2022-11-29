from trytond.pool import Pool
from . import cars

__all__ = ['register']


def register():
    Pool.register(
        cars.Marca,
        cars.Modelo,
        cars.Coche,
        cars.Party,
        cars.Productos,
        cars.ModeloProducto,
        cars.BajaCoche,
        cars.BajaCocheStart,
        cars.BajaCocheResultado,
        module='cars', type_='model')
    Pool.register(
        cars.BajaCoche,
        module='cars', type_='wizard')
    Pool.register(
        cars.CocheReport,
        module='cars', type_='report')
