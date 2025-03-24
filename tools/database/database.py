from contextlib import closing
from flask import json
import logging
import psycopg2
import config
from cryptography.fernet import Fernet
from app import send_telegram_message
import tools.database.patients as dbpatients

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",  
            database="Clinica",
            user="postgres",
            password=config.DATABASE_KEY
        )
        return conn
    except Exception as error:
        print("Error al conectarse a la base de datos:", error)
        return None

def exists_db():
    try:
        with closing(get_connection()) as con:
            with con.cursor() as cur:
                cur.execute('SELECT 1 FROM patients LIMIT 1')
                return True
    except psycopg2.Error:
        return False

def init_db():
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cie10 (
                    code TEXT PRIMARY KEY NOT NULL,
                    name TEXT NOT NULL
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tipo TEXT NOT NULL,
                    active BOOLEAN DEFAULT FALSE,
                    name TEXT NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS unidades (
                    id SERIAL PRIMARY KEY,
                    unidad TEXT NOT NULL
                )
            ''') 
            cur.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id SERIAL PRIMARY KEY,
                    empleo TEXT,
                    apellido1 TEXT NOT NULL,
                    apellido2 TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    unidad INTEGER NOT NULL,
                    destino TEXT,
                    ultimoReco TIMESTAMP,
                    situacion TEXT,
                    observaciones TEXT,
                    ta TEXT,
                    altura FLOAT,
                    peso FLOAT,
                    revision TIMESTAMP,
                    FOREIGN KEY(unidad) REFERENCES unidades(id)
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS infoadicional (  
                    id SERIAL PRIMARY KEY,
                    patient_id INTEGER NOT NULL,
                    info_ad TEXT NOT NULL,
                    created_at_info TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    FOREIGN KEY(patient_id) REFERENCES patients(id)
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS bajas (
                    id SERIAL PRIMARY KEY,
                    patient_id INTEGER NOT NULL,
                    baja TIMESTAMP NOT NULL,
                    RMNP TEXT,
                    motivo TEXT,
                    PROF TEXT,
                    cie10 TEXT,
                    renovacion TIMESTAMP,
                    info_baja TEXT,
                    domicilio TEXT,
                    aseguradora TEXT,
                    FOREIGN KEY(patient_id) REFERENCES patients(id),
                    FOREIGN KEY(cie10) REFERENCES cie10(code)
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS historicopacientes (
                    id SERIAL PRIMARY KEY,
                    tipo TEXT NOT NULL,
                    patient_id INTEGER NOT NULL,
                    empleo TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    apellido1 TEXT NOT NULL,
                    apellido2 TEXT NOT NULL,
                    unidad TEXT NOT NULL,
                    destino TEXT,
                    ultimoreco TIMESTAMP,
                    situacion TEXT,
                    observaciones TEXT,
                    ta TEXT,
                    altura FLOAT,
                    peso FLOAT,
                    revision TIMESTAMP,
                    baja TIMESTAMP,
                    rmnp TEXT,
                    motivo TEXT,
                    prof TEXT,
                    cie10 TEXT,
                    renovacion TIMESTAMP,
                    info_baja TEXT,
                    domicilio TEXT,
                    aseguradora TEXT,
                    created_at_historico TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(patient_id) REFERENCES patients(id),
                    FOREIGN KEY(cie10) REFERENCES cie10(code)
                )
            ''')
            cur.execute('''
                    CREATE TABLE IF NOT EXISTS ips (
                    ip_address VARCHAR(45) PRIMARY KEY NOT NULL,
                    create_for TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''');    
            cur.execute('CREATE EXTENSION IF NOT EXISTS "unaccent";')

            cur.execute('SELECT * FROM cie10')
            cie10 = cur.fetchone()
            if cie10 is None:
                with open('cie10.json', 'r') as file:
                    datos = json.load(file)
                    for item in datos:
                        code = item['code']
                        name = item['name']
                        cur.execute('INSERT INTO cie10 (code, name) VALUES (%s, %s)', (code, name))
            con.commit()

def logf(message):
    send_telegram_message(message)


def get_unidades():
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT * FROM unidades')
            unidades = cur.fetchall()
            return [dict(zip([desc[0] for desc in cur.description], unidad)) for unidad in unidades]
        
def get_infoadicional(patient_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT * FROM infoadicional WHERE patient_id = %s', ( patient_id,))
            infoadicional = cur.fetchall()
            infoadicional = sorted(infoadicional, key=lambda x: x[1], reverse=True)
            return [dict(zip([desc[0] for desc in cur.description], info)) for info in infoadicional]

    
def add_infoadicional(patient_id, info):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                INSERT INTO infoadicional ( patient_id, info_ad)
                VALUES ( %s, %s)
            ''', ( patient_id, info,))
            con.commit()

def delete_infoadicional(info_adicional_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('UPDATE infoadicional SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s', (info_adicional_id,))
            con.commit()

def delete_infoadicional_real(patient_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM infoadicional WHER WHERE patient_id = %s', (patient_id,))
            con.commit()

def get_historicopacientes(patient_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''SELECT 
                    h.id,
                    h.tipo,
                    h.patient_id,
                    h.empleo,
                    h.nombre,
                    h.apellido1,
                    h.apellido2,
                    h.unidad,
                    h.destino,
                    h.ultimoreco,
                    h.situacion,
                    h.observaciones,
                    h.ta,
                    h.altura,
                    h.peso,
                    h.baja,
                    h.rmnp,
                    h.motivo,
                    h.prof,
                    h.cie10,
                    h.renovacion,
                    h.info_baja,
                    h.domicilio,
                    h.aseguradora,
                    h.created_at_historico,
                    h.revision
                    FROM historicopacientes h
                    WHERE h.patient_id = %s''', (patient_id,))
            historicopacientes = cur.fetchall()
            historicopacientes = sorted(historicopacientes, key=lambda x: x[1], reverse=True)
            
            return [dict(zip([desc[0] for desc in cur.description], historicopaciente)) for historicopaciente in historicopacientes]

def create_historicopacientes(tipo, patient_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            patient = dbpatients.get_patient_total(patient_id)
            for patient in patient:
                cur.execute('''
                    INSERT INTO historicopacientes (
                        tipo, patient_id, empleo, nombre, 
                        apellido1, apellido2, unidad, destino, 
                        ultimoreco, situacion, observaciones, ta, 
                        altura, peso, revision, baja, 
                        rmnp, motivo, prof, cie10, 
                        renovacion, info_baja, domicilio, aseguradora
                    ) VALUES   (%s, %s, %s, %s, 
                                %s, %s, %s, %s, 
                                %s, %s, %s, %s, 
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s)
                ''', (
                    tipo, patient_id, patient['empleo'], patient['nombre'], 
                    patient['apellido1'], patient['apellido2'], patient['unidad'], patient['destino'],
                    patient['ultimoreco'], patient['situacion'], patient['observaciones'], patient['ta'],
                    patient['altura'], patient['peso'], patient['revision'], patient['baja'],
                    patient['rmnp'], patient['motivo'], patient['prof'], patient['cie10'], 
                    patient['renovacion'],patient['info_baja'], patient['domicilio'], patient['aseguradora']
                ))
                con.commit()

def delete_historicopacientes(patient_id, historicopaciente_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM historicopacientes WHERE patient_id = %s and id = %s', (patient_id, historicopaciente_id,))
            con.commit()

def delete_historicopaciente_total(patient_id):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM historicopacientes WHERE patient_id = %s', (patient_id,))
            con.commit()

def create_backup():
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]
    
            backup_data = {}
            for table in tables:
                if table == 'cie10':
                    continue
                cur.execute(f'SELECT * FROM {table}')
                rows = cur.fetchall()
                column_names = [desc[0] for desc in cur.description]  # Obtener nombres de columnas

                # Convertir filas a diccionarios
                backup_data[table] = [dict(zip(column_names, row)) for row in rows]
                
            results = json.dumps(backup_data, default=str, indent=4)
            
            fernet = Fernet(config.BACKUP_KEY)
            texto_cifrado = fernet.encrypt(results.encode())
                    
            return texto_cifrado

def get_ips_allow():
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT * FROM ips', ())
            ips = cur.fetchall()
            return ips
        
def is_ip_allow(ip):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT COUNT(*) FROM ips WHERE ip_address = %s', (ip,))
            result = cur.fetchone()
            return int(result[0] > 0)
        

def add_allowed_ip(ip):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            if is_ip_allow(ip):
                logging.info(f"{ip} - Already exists.")
                return False
            else:
                cur.execute('INSERT INTO ips (ip_address) VALUES (%s)', (ip))
                logging.warning(f"{ip} - Has been ADD.")
                con.commit()

def remove_allowed_ip(ip):
    with closing(get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM ips WHERE ip_address = %s', (ip,))
            logging.info(f"{ip} - Has been deleted.")
            con.commit()
