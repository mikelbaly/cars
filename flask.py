from flask import Flask, request, redirect, url_for
from flask_tryton import Tryton
from flask import render_template
from flask import abort,session,g
from functools import wraps
import os

app = Flask(__name__)
app.config['TRYTON_DATABASE'] = 'tallerb'
app.config.update(SECRET_KEY=os.urandom(24))
tryton = Tryton(app,configure_jinja=True)
Marca = tryton.pool.get('cars.marca')
Modelo = tryton.pool.get('cars.modelo')
Coche = tryton.pool.get('cars.coche')
Terceros = tryton.pool.get('party.party')

WebUser = tryton.pool.get('web.user')
UserSession = tryton.pool.get('web.user.session')

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html',name=name)

@app.route('/marcas')
@tryton.transaction()
def listaMarcas():
    marcas = Marca.search([])
    return render_template('marcas.html',misMarcas=marcas)

@app.route('/marcas/<marca_url>')
@tryton.transaction()
def listaModelosYCoches(marca_url):
    modelos = Modelo.search([('marca','=',marca_url)])
    coches = Coche.search([('marca','=',marca_url)])
    marca = Marca.search([('nombre','=',marca_url)])[0]
    return render_template('modelos.html',misModelos=modelos,misCoches=coches,miMarca=marca)


@app.route('/comprar/<record("cars.modelo"):modelo>',methods={'POST','GET'})
@tryton.transaction()
def comprar(modelo):
    if request.method=='POST':
        nuevoCoche = Coche()
        nuevoCoche.matricula = request.form.get('matricula',"")
        nuevoCoche.modelo = modelo
        nuevoCoche.marca = modelo.marca  
        if session.get('party'):
            miTercero = Terceros(session.get('party'))
            nuevoCoche.propietario=miTercero
        else:  
            nuevoCoche.propietario = int(request.form.get('propietario',0))
        nuevoCoche.save()
        return redirect(url_for('listaModelosYCoches',marca_url=modelo.marca.nombre))

    terceros = Terceros.search([])
    return render_template('comprar.html',miModelo=modelo,misTerceros=terceros)

@app.route('/nuevoModelo/<record("cars.marca"):marca>',methods={'POST','GET'})
@tryton.transaction()
def addModelo(marca):
    if request.method=='POST':
        nuevoModelo = Modelo()
        nuevoModelo.marca = marca
        nuevoModelo.modelo = request.form.get('modelo',"")
        nuevoModelo.save()
        return redirect(url_for('listaModelosYCoches',marca_url=marca.nombre))
    combustibles = Modelo.fields_get(['combustible'])['combustible']['selection']
    return render_template('nuevoModelo.html',miMarca=marca,misCombustibles=combustibles)

def login_required(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        session_key=None
        if 'session_key' in session:
            session_key = session['session_key']
        g.user = UserSession.get_user(session_key)
        if not g.user:
            return redirect(url_for('login',next=request.path))
        return func(*args,**kwargs)
    return wrapper


@app.route('/logout')
@tryton.transaction(readonly=False)
@login_required
def logout():
    if session['session_key']:
        user_sessions = UserSession.search([('key','=',session['session_key'])])
        UserSession.delete(user_sessions)
        session.pop('session_key',None)
        session.pop('party',None)
        session.pop('username',None)
        session.pop('name',None)
    return redirect(request.referrer if request.referrer else url_for('index'))

@app.route('/login',methods=['GET','POST'])
@tryton.transaction()
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            user = WebUser.authenticate(username,password)
            if user:
                session['session_key'] = WebUser.new_session(user)
                session['username'] = user.email
                if user.party:
                    session['party'] = user.party.id
                    session['name'] = user.party.name
                next_ = request.form.get('next',None)
                if next_:
                    return redirect(next_)
                return redirect('/')
            else:
                return 'Usuario Incorrecto'
    return render_template('login.html')


@app.route('/signup',methods=['GET','POST'])
@tryton.transaction()
def signup():
    if request.method == 'POST':
        nuevoTercero = Terceros()
        nuevoTercero.name = request.form.get('username')
        nuevoTercero.save()
        nuevoUsuario = WebUser()
        username = request.form.get('username')
        password = request.form.get('password')
        nuevoUsuario.email = username
        nuevoUsuario.password = password
        nuevoUsuario.party = nuevoTercero
        nuevoUsuario.save()
        return redirect(url_for('listaMarcas'))
    terceros = Terceros.search([])
    return render_template('signup.html',misTerceros=terceros)
