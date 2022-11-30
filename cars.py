from trytond.model import ModelSQL, ModelView,fields,Unique
from trytond.pyson import Eval, Bool
import datetime
from trytond.pool import Pool,PoolMeta
from trytond.wizard import Wizard, StateView,StateTransition,Button
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.modules.company import CompanyReport

class Marca(ModelSQL,ModelView):
    "Marca"
    __name__ = 'cars.marca'
    _rec_name = 'nombre' #si nombre fuera 'name' no haria falta, rec_name coge name por defecto

    nombre = fields.Char("Nombre", required=True)
    modelos = fields.One2Many('cars.modelo','marca',"Modelos")

class Modelo(ModelSQL,ModelView):
    "Modelo"
    __name__ = 'cars.modelo'
    _rec_name = 'modelo'
    marca = fields.Many2One('cars.marca', 'Marca', required=True, ondelete='CASCADE')
    modelo = fields.Char("Modelo", required=True)
    fecha_lanzamiento = fields.Date("Fecha Lanzamiento")
    combustible = fields.Selection([
            ('diesel', 'Diesel'),
            ('gasolina', 'Gasolina'),
            ('electrico', 'Electrico'),
            ('hibrido', 'Hibrido'),
            (None,''), #Permite guardar valores vacíos
            ], 'Combustible')
    cavallos = fields.Integer("Cavallos")
    precioModelo = fields.Integer('Precio del modelo')

    productosDelModelo = fields.Many2Many('modelo-producto','modelo','producto','Productos disponibles',
        domain=[
            ('type','=','goods'),
        ])

    @classmethod
    def default_fecha_lanzamiento(cls):
        return datetime.date.today()       

    @classmethod
    def default_marca(cls):
        pool = Pool()
        marca = pool.get('cars.marca')
        marca1 = marca.search([],limit=1,
            order=[('nombre','ASC'),('id','ASC')])
        if len(marca1):
            return marca1[0].id

class Coche(ModelSQL,ModelView):
    "Coche"
    __name__ = 'cars.coche'
    matricula = fields.Char("Matricula", required=True,
        states={
            'readonly': Eval('id',-1)>0, # lo mismo que 'readonly':Greater(Eval('id',-1),0)
        })
    marca = fields.Many2One('cars.marca', "Marca",ondelete='CASCADE')
    modelo = fields.Many2One('cars.modelo', "Modelo",ondelete='CASCADE',
        domain=[
        ('marca','=',Eval('marca',-1))
        ], depends=['marca'],
        states={
            'required': Bool(Eval('marca',-1)),
            'invisible': ~Bool(Eval('marca',-1)) # ~ = NOT
        }
    )
    propietario = fields.Many2One('party.party', "Propietario",required=True,ondelete='CASCADE')
    precio = fields.Integer("Precio",
        domain=[ 'OR',
        ('precio','>',0),
        ('precio','=', None)]
    )
    fecha_matriculacion = fields.Date("Fecha de Matriculacion")
    fecha_baja = fields.Date("Fecha de Baja")
    cavallos = fields.Function(fields.Integer('numero de cavallos'),'getHP',searcher='searcherHP')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('matricula unica', Unique(t,t.matricula),'cars.msg_coche_matricula_unique')
        ]

    @classmethod
    def searcherHP(cls,name,clause):
        return [('modelo.cavallos',clause[1],clause[2])]

    @fields.depends('marca','modelo')
    def on_change_marca(self):
        if self.marca:
            if len(self.marca.modelos) ==1:
                self.modelo = self.marca.modelos[0]
            if self.modelo:
                if self.modelo.marca.id!=self.marca.id:
                    self.modelo = None
            else:
                self.modelo = None

    @fields.depends('marca','modelo')
    def on_change_with_precio(self): #cambia el precio al valor de return
        if self.marca and self.modelo:
            return self.modelo.precioModelo

    def getHP(self,name):
        if self.modelo:
            return self.modelo.cavallos
        else:
            return 0

class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    coches = fields.One2Many('cars.coche','propietario','Coches')
    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.name.required = True
        cls.name.states.update({
            'readonly':Eval('id',-1)>0
        })

class Productos(metaclass=PoolMeta):
    __name__ = 'product.template'

    modelos_compatibles = fields.Many2Many('modelo-producto','producto','modelo','Modelos compatibles',
        states={
            'invisible':Eval('type','')!='goods'
        },
        depends=['type'],
        )

class ModeloProducto(ModelSQL):
    "modelos - productos" #descripcion
    __name__ = 'modelo-producto'
    modelo = fields.Many2One('cars.modelo','modelo',required=True,ondelete='CASCADE')
    producto = fields.Many2One('product.template','product',required=True,ondelete='CASCADE')

#wizards
class BajaCoche(Wizard):
    "Baja coche"
    __name__ = "cars.coche.baja"
    start = StateView('cars.coche.baja.start',
        'cars.coche_baja_start_form',[
            Button('Cancel','end','tryton-cancel'),
            Button('Baja','baja','tryton-ok',default=True),
        ])
    baja=StateTransition()
    result = StateView('cars.coche.baja.result',
        'cars.coche_baja_result_form',[
            Button('Close','end','tryton-close'),
        ])

    def transition_baja(self):
        pool = Pool()
        Coche = pool.get('cars.coche')
        coches = Coche.browse(Transaction().context['active_ids'])
        for coche in coches:
            coche.fecha_baja = self.start.fecha_baja
        Coche.save(coches)
        return "result"

class BajaCocheStart(ModelView):
    "baja de coche start"
    __name__ = "cars.coche.baja.start"
    fecha_baja = fields.Date('Fecha baja',required=True)

    @classmethod
    def default_fecha_baja(cls):
        return datetime.date.today()

class BajaCocheResultado(ModelView):
    "baja de coche resultado"
    __name__ = "cars.coche.baja.result"
    n_coches_afectados = fields.Integer("Numero de coches afectados",readonly=True)

    @classmethod
    def default_n_coches_afectados(cls):
        return len(Transaction().context.get('active_ids',[]))

#reports
class CocheReport(Report):
    "coche CocheReport"
    __name__ = "ficha_tecnica_coche"

    @classmethod
    def get_context(cls, records, header, data):
        context = super().get_context(records, header, data)
        context['empresa'] = "Empresa de Ejemplo"
        return context