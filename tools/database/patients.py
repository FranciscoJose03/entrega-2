from contextlib import closing
import csv
import time
import tools.database.database as db

def get_patients(page=1, page_size=100):
    offset = (page - 1) * page_size
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        p.*,
                        u.unidad
                    FROM 
                        patients p
                    JOIN 
                        unidades u ON p.unidad = u.id
                    ORDER BY 
                        p.id
                    LIMIT %s OFFSET %s
                        ''', (page_size, offset,))
            patients = cur.fetchall()

            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]
        
def get_patient(patient_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        p.*,
                        u.unidad
                    FROM 
                        patients p
                    JOIN 
                        unidades u ON p.unidad = u.id
                    WHERE 
                        p.id = %s
                        ''', (patient_id,))
            patient = cur.fetchone()
            
            return [dict(zip([desc[0] for desc in cur.description], patient))]

def get_patient_total(patient_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        p.*,
                        b.baja,
                        b.rmnp,
                        b.motivo,
                        b.prof,
                        b.cie10,
                        b.renovacion,
                        b.info_baja,
                        b.domicilio,
                        b.aseguradora,
                        u.unidad
                    FROM 
                        patients p
                    JOIN 
                        unidades u ON p.unidad = u.id
                    LEFT 
                        JOIN bajas b ON p.id = b.patient_id
                    WHERE 
                        p.id = %s
                        ''', (patient_id,))
            patient = cur.fetchone()
            
            return [dict(zip([desc[0] for desc in cur.description], patient))]

def search_patients(nombre, apellidos):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        p.*,
                        u.unidad 
                    FROM 
                        patients p
                    JOIN 
                        unidades u ON p.unidad = u.id
                    WHERE 
                        unaccent(nombre) ILIKE unaccent(%s) 
                        OR (unaccent(apellido1) ILIKE unaccent(%s) OR unaccent(apellido2) ILIKE unaccent(%s))
                        ''', (f'{nombre}', f'{apellidos}', f'{apellidos}'))
            
            patients = cur.fetchall()

            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]

def get_patient_proximas_revisiones():
    today = time.strftime('%Y-%m-%d 00:00:00')
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        p.*,
                        u.unidad 
                    FROM 
                        patients p
                    JOIN 
                        unidades u ON p.unidad = u.id
                    WHERE 
                        revision >= %s
                        ''', (today,))
            patients = cur.fetchall()

            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]

def get_patient_hoy_revisiones():
    today = time.strftime('%Y-%m-%d 00:00:00')
    todaynight = time.strftime('%Y-%m-%d 23:59:59')
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        p.*,
                        u.unidad 
                    FROM 
                        patients p
                    JOIN 
                        unidades u ON p.unidad = u.id
                    WHERE 
                        revision BETWEEN %s AND %s
                        ''', (today, todaynight,))
            patients = cur.fetchall()

            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]
        
"""ACCIONES"""
def add_patient(empleo, 
        apellido1, 
        apellido2, 
        nombre, 
        unidad, 
        destino, 
        ultimo_reco, 
        situacion, 
        observaciones, 
        ta, 
        altura, 
        peso,
        revision):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                INSERT INTO patients (
                    empleo, apellido1, apellido2, nombre, unidad, destino,
                    ultimoReco, situacion, observaciones,
                    ta, altura, peso, revision
                ) 
                VALUES 
                (%s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s)
                ''', 
                (empleo, apellido1, apellido2, nombre, unidad, destino,
                ultimo_reco, situacion, observaciones,
                ta, altura, peso, revision
                ))
            con.commit()

def edit_patient(patient_id, 
            empleo, 
            apellido1, 
            apellido2, 
            nombre, 
            unidad, 
            destino, 
            ultimo_reco, 
            situacion, 
            observaciones, 
            ta, 
            altura, 
            peso,
            revision):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                UPDATE patients SET 
                    empleo = %s, apellido1 = %s, apellido2 = %s, nombre = %s, unidad = %s, 
                    destino = %s, ultimoReco = %s, situacion = %s, observaciones = %s, 
                    ta = %s, altura = %s, peso = %s, revision = %s
                WHERE id = %s
                ''', 
                (empleo, apellido1, apellido2, nombre, unidad, 
                destino, ultimo_reco, situacion, observaciones,
                ta, altura, peso, revision, 
                patient_id
                ))
            con.commit()

"""FALTA EDITARLAS"""
def add_patients_from_csv(data_csv):
    with open(data_csv, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        with closing(db.get_connection()) as con:
            with closing(con.cursor()) as cur:
                for row in reader:
                    apellido, nombre = row[0].split(", ")
                    print(row[0])
                    data = (
                        nombre,                         # 0 nombre SI
                        apellido,                       # 1 apellido SI 
                        row[3],                         # 2 fechaNacimiento NO
                        row[4],                         # 3 telefono SI
                        row[5],                         # 4 direccion SI
                        row[6] if row[6] else None,     # 5 fechaUltimoAptoTFCF NO
                        row[7],                         # 6 resultadoActualTFCF SI
                        row[8],                         # 7 observacionesTFCF SI 
                        row[9] if row[9] else None,     # 8 fechaInicioBaja NO
                        row[10] if row[10] else None,   # 9 fechaFinBaja NO
                        row[11],                        # 10 cie10 NO
                        row[12],                        # 11 diagnostico SI
                        row[1],                         # 12 unidad SI
                        row[2],                         # 13 empleo SI
                        row[14] if row[14] else None    # 14 proximaCita NO
                    )
                    cur.execute('''
                        INSERT INTO patients (
                            nombre, apellido, fechaNacimiento, telefono, direccion,
                            fechaUltimoAptoTFCF, resultadoActualTFCF, observacionesTFCF,
                            fechaInicioBaja, fechaFinBaja, cie10, diagnostico,
                            unidad, empleo, proximaCita
                        ) VALUES (%s, %s, %s, %s, %s,
                                %s, %s, %s, 
                                %s, %s, %s, %s,
                                %s, %s, %s)''', 
                        (data[0], data[1],  data[2],  data[3], data[4],  data[5], 
                         data[6], data[7],  data[8], 
                         data[9], data[10], data[11], data[12], 
                         data[13],  data[14]))
                    con.commit()

def delete_patient(patient_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM patients WHERE id = %s', (patient_id,))
            con.commit()