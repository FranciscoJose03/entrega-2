import os
from flask import Flask, json, request, render_template, redirect, url_for, flash, session, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user 
import requests
from werkzeug.security import generate_password_hash, check_password_hash 
from dotenv import load_dotenv
import tools.database.database as db 
import tools.database.patients as dbpatients
import tools.database.patients_baja as dbbaja
import tools.database.cie10 as dbcie
import tools.database.calendario as dbcalendario
import tools.database.acceso as dbacceso
import tools.database.users as dbusers
import logging
from datetime import datetime
import waitress
import config
import secrets

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': config.CHAT_ID,
        'text': message
    }
    requests.post(url, json=payload)

def get_telegram_updates():
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url)
    
    if response.status_code == 200:
        updates = response
        json_updates = json.loads(updates.text)
    
        if 'result' in json_updates:
            allupdates = json_updates['result']
            if allupdates:
                last_update = allupdates[-1]
                return last_update['message']['text']
        else:
            logging.error("No se encontraron resultados en la respuesta.")
            return None
    else:
        logging.error(f"Failed to get updates: {response.status_code}")
        return None

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, tipo, active, name):
        self.id = id
        self.tipo = tipo
        self.active = active
        self.name = name

@login_manager.unauthorized_handler
def unauthorized():
    ip = request.remote_addr
    logging.warning(f'{ip} - Unauthorized access attempt.')

    return redirect(url_for('login'))

@app.before_request
def before_request():
    if 'X-Real-Ip' in request.headers:
        ip = request.headers.get('X-Real-Ip')
        if not db.is_ip_allow(ip):
            logging.warning(f'{ip} - Trying to access.')
            return "Bye Bye", 403
    else: 
        return "No IP", 403
    g.user = current_user

@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

"""OBLIGATORIO DE FLASK-LOGIN"""
@login_manager.user_loader
def load_user(user_id):
    user_row = dbusers.get_user_flask(user_id)
    if user_row:
        for user in user_row:
            return User(user['id'], user['tipo'], user['active'], user['name'])
    return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        
        if not name or not password:
            flash('Please enter both username and password')
            return redirect(url_for('login'))

        user_row = dbusers.get_user(name)
        
        if user_row:
            for user_row in user_row:
                if check_password_hash(user_row['password'], password):
                    user = User(user_row['id'], user_row['tipo'], user_row['active'], user_row['name'])
                    login_user(user)

                    if user.active == False:
                        updates = get_telegram_updates()
                        if updates:
                            if updates == f"/rechazar_{user.name}":
                                send_telegram_message(f"Se ha rechazado la solicitud de acceso de {user.name}.")
                            elif updates == f"/aceptar_{user.name}":
                                send_telegram_message(f"{user.name} ha sido activada.\nRecuerda que puedes desactivarla en cualquier momento.")
                                dbusers.change_active_user(2, user.id)
                    
                    if user.active == True:
                        logging.info(f'{user.name} - Has logged in.')
                        return redirect(url_for('patients'))
            
        else:
            flash ('User or password incorrect')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
            paswordtocreate = secrets.token_urlsafe(16)
            print(paswordtocreate)
            session['paswordtocreate'] = paswordtocreate

    if request.method == 'POST':
        if 'paswordtocreate' in session and session['paswordtocreate'] == request.form.get('paswordtocreate'):
            name = request.form['username']
            if dbusers.get_user(name):
                flash('The username already exists. Please choose another one.')
                return redirect(url_for('register'))

            password = generate_password_hash(request.form['password'])
            dbusers.create_user("user", name, password)                

            return redirect(url_for('login'))

    return render_template('register.html')

def check_user_active():
    if not dbusers.check_user_active(g.user.id):
        flash('Your user is inactive. Please contact the administrator.')
        return redirect(url_for('logout'))

@app.route('/export', methods=['GET', 'POST'])
@login_required
def export():
    check_user_active()
    
    return Response(
                    db.create_backup(),
                    mimetype='application/octet-stream',
                    headers={'Content-disposition': f'attachment; filename=campaign_result_{datetime.now()}.bin'}
                )
    
@app.route('/patients', methods=['GET', 'POST'])
@login_required
def patients():
    check_user_active()
    #dbpatients.add_patients_from_csv("/opt/app/app/datos_aleatorios.csv")
    today = datetime.now()
    page = request.args.get('page', default=1, type=int)
    cie10_data = dbcie.get_cie10_complete()
    
    if request.method == 'POST':
        action = request.form['action']
        patient_id = request.form['patient_id'] if 'patient_id' in request.form else ""
        empleo = request.form['empleo'] if 'empleo' in request.form else ""
        apellido1 = request.form['apellido1'] if 'apellido1' in request.form else ""
        apellido2 = request.form['apellido2'] if 'apellido2' in request.form else ""
        nombre = request.form['nombre'] if 'nombre' in request.form else ""
        unidad = request.form['unidad'] if 'unidad' in request.form else ""
        destino = request.form['destino'] if 'destino' in request.form else ""
        ultimoreco = request.form['ultimoreco'] if 'ultimoreco' in request.form else ""
        situacion = request.form['situacion'] if 'situacion' in request.form else ""
        observaciones = request.form['observaciones'] if 'observaciones' in request.form else ""
        ta = request.form['ta'] if 'ta' in request.form else ""
        altura = request.form['altura'] if 'altura' in request.form else ""
        peso = request.form['peso'] if 'peso' in request.form else ""
        revision = request.form['revision'] if 'revision' in request.form else ""
        
        if action == 'add_patient':
            dbpatients.add_patient(empleo, 
                          apellido1, 
                          apellido2, 
                          nombre, 
                          unidad, 
                          destino, 
                          ultimoreco, 
                          situacion, 
                          observaciones, 
                          ta, 
                          altura, 
                          peso,
                          revision, 
                          )   
            logging.info(f'{g.user.name} - Has created a Patient.')
            return redirect(url_for('patients')) 
        
        elif action == 'add_patient_downtime':
            baja = request.form['baja'] if 'baja' in request.form else ""
            rmnp = request.form['rmnp'] if 'rmnp' in request.form else ""
            motivo = request.form['motivo'] if 'motivo' in request.form else ""
            prof = request.form['prof'] if 'prof' in request.form else ""
            cie10 = request.form['cie10'] if 'cie10' in request.form else ""
            renovacion = request.form['renovacion'] if 'renovacion' in request.form else ""
            info = request.form['info'] if 'info' in request.form else ""
            domicilio = request.form['domicilio'] if 'domicilio' in request.form else ""
            aseguradora = request.form['aseguradora'] if 'aseguradora' in request.form else ""
            dbbaja.add_patients_baja(patient_id,
                            baja,
                            rmnp,
                            motivo,
                            prof,
                            cie10,
                            renovacion,
                            info,
                            domicilio,
                            aseguradora
                        )

            return redirect(url_for('patients'))
        
        elif action == 'edit_patient':
            dbpatients.edit_patient(patient_id,
                            empleo, 
                            apellido1, 
                            apellido2, 
                            nombre, 
                            unidad, 
                            destino, 
                            ultimoreco, 
                            situacion, 
                            observaciones, 
                            ta, 
                            altura, 
                            peso,
                            revision,
                          )
            
            db.create_historicopacientes("Auto", patient_id)

            logging.info(f'{g.user.name} - Has edited a Patient.')
            return redirect(url_for('patients'))  
        
        elif action == 'delete_patient':
            dbpatients.delete_patient(request.form['patient_id'])

            logging.info(f'{g.user.name} - Has deleted a Patient.')
            return redirect(url_for('patients'))        
        
        elif action == 'search_patient':
            nombre = request.form['nombre'].replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            apellidos = request.form['apellidos'].replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

            patients = dbpatients.search_patients(nombre, apellidos)

            return render_template('patients.html', patients=patients, user=g.user, today=today, cie10_data=cie10_data)
        
        elif action == 'get_patient_cita_proximas':
            
            patients = dbpatients.get_patient_proximas_revisiones()
            
            return render_template('patients.html', patients=patients, user=g.user, today=today, cie10_data=cie10_data)
        
        elif action == 'get_patient_cita_hoy':

            patients = dbpatients.get_patient_hoy_revisiones()
            
            return render_template('patients.html', patients=patients, user=g.user, today=today, cie10_data=cie10_data)
        
    patients = dbpatients.get_patients(page=page)
    total_pages = -(-len(patients) // 100)
    start_page = max(1, page - 3)
    end_page = min(total_pages, page + 4)

    return render_template('patients.html', patients=patients, today=today, user=g.user, cie10_data=cie10_data, total_pages=total_pages, current_page=page, start_page=start_page, end_page=end_page)

@app.route('/patients_bajas', methods=['GET', 'POST'])
@login_required
def patients_bajas():
    check_user_active()
    if request.method == 'POST':
        action = request.form['action']
        if action == 'search_patient':
            nombre = request.form['nombre'].replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            apellidos = request.form['apellidos'].replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            
            patients = dbbaja.search_patients_baja(nombre, apellidos)

            return render_template('patients_bajas.html', patients=patients, user=g.user, cie10_data=dbcie.get_cie10_complete(), unidades=db.get_unidades())

        elif action == 'filter_by_week':
            start_week = request.form.get('start_week') or "2000-01-01"
            end_week = request.form.get('start_week') or "3000-01-01"

            patients = dbbaja.get_patients_baja_week(start_week, end_week)

            return render_template('patients_bajas.html', patients=patients, user=g.user, cie10_data=dbcie.get_cie10_complete(), unidades=db.get_unidades())
        
        elif action == 'filter_by_unit':
            unidad = request.form.get('unidad')
            patients = dbbaja.get_patients_baja_by_unidad(unidad)

            return render_template('patients_bajas.html', patients=patients, user=g.user, cie10_data=dbcie.get_cie10_complete(), unidades=db.get_unidades())

        elif action == 'delete_baja':
            baja_id = request.form.get('baja_id')
            dbbaja.delete_patients_baja(baja_id)
            
    page = request.args.get('page', default=1, type=int)
    patients = dbbaja.get_patients_baja()
    total_pages = -(-len(patients) // 100)
    start_page = max(1, page - 3)
    end_page = min(total_pages, page + 4)

    return render_template('patients_bajas.html', patients=patients, user=g.user, cie10_data=dbcie.get_cie10_complete(), unidades=db.get_unidades(), total_pages=total_pages, current_page=page, start_page=start_page, end_page=end_page)

@app.route('/patient', methods=['POST'])
@login_required
def patient():
    check_user_active()
    action = request.form['action'] if 'action' in request.form else ""
    patient_id = request.form['patient_id']
    patient=dbpatients.get_patient(patient_id)

    if action == "add_info":
        infoad = request.form['infoAdicional']
        db.add_infoadicional(patient_id, infoad)
        logging.info(f'{g.user.name} - Has created a Info.')

    elif action == "delete_info":
        info_adicional_id = request.form['info_adicional_id']
        db.delete_infoadicional(info_adicional_id)
        logging.info(f'{g.user.name} - Has deleted a Info.')

    elif action == "create_historicopacientes":
        tipo = request.form['tipo']
        db.create_historicopacientes(tipo, patient_id)
        logging.info(f'{g.user.name} - Has created a History')

    info = db.get_infoadicional(patient_id)
    return render_template('patient.html', info_adicional=info, patient=patient, cie10_data=dbcie.get_cie10_complete(), user=g.user)

@app.route('/logout')
@login_required
def logout():
    logging.info(f'{g.user.name} - Has LogOut')

    logout_user()
    flash('You have successfully logged out.')
    return redirect(url_for('index'))

@app.route('/add_patient', methods=['GET'])
@login_required
def add_patient():
    check_user_active()
    
    current_date = datetime.now().strftime("%Y-%m-%d")

    return render_template('add_patient.html', user=g.user, current_date=current_date, unidades=db.get_unidades())

@app.route('/add_patient_baja', methods=['GET'])
@login_required
def add_patient_baja():
    check_user_active()

    patient_id = request.args.get('id')

    return render_template('add_patient_baja.html', patient=dbpatients.get_patient(patient_id), cie10_data=dbcie.get_cie10_complete(), user=g.user)

@app.route('/edit_patient', methods=['GET'])
@login_required
def edit_patient():
    check_user_active()

    patient_id = request.args.get('id')

    return render_template('edit_patient.html', patient=dbpatients.get_patient(patient_id), cie10_data=dbcie.get_cie10_complete(), unidades=db.get_unidades(), user=g.user)


@app.route('/cie10', methods=['GET', 'POST'])
@login_required
def cie10():
    check_user_active()

    if request.method == 'POST':
        action = request.form['action']

        if action == 'add_cie':
            cie_code = request.form['cie_code']
            cie_name = request.form['cie_name']
            dbcie.add_cie10(cie_code, cie_name)

            return redirect(url_for('cie10'))

        elif action == 'edit_cie':
            cie_code = request.form['cie_code']
            cie_name = request.form['cie_name']
            dbcie.edit_cie10(cie_code, cie_name)

            return redirect(url_for('cie10'))

        elif action == 'delete_cie': 
            cie_code = request.form['cie_code']
            dbcie.delete_cie10(cie_code)

            return redirect(url_for('cie10'))

    code = request.args.get('code')
    if code:
        cie10 = dbcie.get_cie10_bycode(code)

        return render_template('cie10.html', cie10=cie10, user=g.user)
    else:
        cie10 = dbcie.get_cie10_complete()

        return render_template('cie10.html', cie10_data=cie10, user=g.user)
    
@app.route('/patient_history', methods=['GET', 'POST'])
@login_required
def patient_history():
    check_user_active()

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        history_id = request.form['history_id']

        db.delete_historicopaciente(patient_id, history_id)
        return redirect(url_for('patient_history', id=patient_id))
    
    patient_id = request.args.get('id')
    
    historicopacientes = db.get_historicopacientes(patient_id)
    info_adicional = db.get_infoadicional(patient_id)
    current_history_index = request.args.get('history_index', type=int)
    total_histories = len(historicopacientes)

    if current_history_index is None or current_history_index < 0 or current_history_index >= total_histories:
        current_history_index = current_history_index if current_history_index is not None else 0

    if total_histories > 0:
        current_history = historicopacientes[current_history_index] if 0 <= current_history_index < total_histories else None
    else:
        current_history = None
    
    return render_template('patient_history.html', 
                            history=current_history,
                            historicopacientes=historicopacientes,
                            current_history_index=current_history_index,
                            info_adicional=info_adicional,
                            total_histories=total_histories,
                            patient_id=patient_id,
                            cie10_data=dbcie.get_cie10_complete(),
                            user=g.user)

@app.route('/panel', methods=['GET', 'POST'])
@login_required
def panel():
    check_user_active()
    
    if g.user.tipo != "super":
        logging.warning(f'{g.user.name} - Unauthorized access attempt.')
        flash('You do not have permission to access this page.')
        return redirect(url_for('logout'))
    
    if request.method == "POST":
        action = request.form['action'] if 'action' in request.form else ""
        if action == "delete_user":
            id_user = request.form['id']

            dbusers.delete_user(g.user, id_user)

        elif action == "change_active":
            id_user = request.form['id']

            dbusers.change_active_user(g.user, id_user)

        elif action == "add_allowed_ip":
            ip = request.form['ipAddress']
            ip_for = request.form['ipFor']

            dbacceso.add_allowed_ip(ip, ip_for)

        elif action == "remove_allowed_ip":
            ip = request.form['ip']
            
            dbacceso.remove_allowed_ip(ip)
        
        elif action == "edit_allowed_ip":
            ipin = request.form['ipin']
            ip_for_in = request.form['ip_for_in']
            ipexist = request.form['ipexist']
            ip_for_exist = request.form['ip_for_exist']
            dbacceso.edit_allowed_ip(ipin, ipexist, ip_for_exist, ip_for_in)
        view_logs = request.form['viewLogs']

        if view_logs == "yes":
            with open('app.log', 'r') as log_file:
                log_content = ''.join([line for line in reversed(log_file.readlines())])
            log_entries = [entry.split(' - ') for entry in log_content.splitlines() if 'root' in entry]
            return render_template('panel.html', user=g.user, users=dbusers.get_users(), ips=dbacceso.get_ips_allow(), log_content=log_entries)
        
    return render_template('panel.html', user=g.user, users=dbusers.get_users(), ips=dbacceso.get_ips_allow())

from calendar import monthrange

@app.route('/calendario', methods=['GET'])
@login_required
def calendario():
    check_user_active()

    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    first_day_of_week, days_in_month = monthrange(year, month)

    citas = dbcalendario.get_citas(year, month)

    citas_dict = {}
    for cita in citas:
        fecha = cita[0].strftime('%Y-%m-%d')
        hora = cita[0].strftime('%H:%M')
        nombre = cita[1]
        if fecha not in citas_dict:
            citas_dict[fecha] = []
        citas_dict[fecha].append({'hora': hora, 'nombre': nombre})

    return render_template( 'calendario.html', 
                            user=g.user,
                            today=datetime.now(),
                            year=year, 
                            month=month, 
                            first_day_of_week=first_day_of_week, 
                            days_in_month=days_in_month, 
                            citas_dict=citas_dict)

if __name__ == '__main__':
    if not db.exists_db():
        db.init_db()
    print("Running on http://127.0.0.1:3000/")
    waitress.serve(app, host='127.0.0.1', port=3000)
"""
docker run --name postgres-container -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=YOUR_PASSWORD -e POSTGRES_DB=Clinica -p 5432:5432 -d postgres"
docker exec -it postgres-container psql -U postgres
\c Clinica
INSERT INTO ips (ip_address, create_for) VALUES ('81.44.40.172', 'Trabajo');
"""
