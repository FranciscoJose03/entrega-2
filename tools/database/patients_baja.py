from contextlib import closing
import tools.database.database as db

def get_patients_baja(page=1, page_size=100):
    offset = (page - 1) * page_size
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                SELECT 
                    b.*,
                    p.empleo,
                    p.apellido1, 
                    p.apellido2, 
                    p.nombre, 
                    u.unidad
                FROM 
                    bajas b
                JOIN 
                    patients p ON b.patient_id = p.id
                JOIN 
                    unidades u ON p.unidad = u.id
                ORDER BY 
                    b.id 
                LIMIT %s OFFSET %s
            ''', (page_size, offset,))
            patients = cur.fetchall()
            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]

def get_patients_baja_week(start_date, end_date):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                SELECT 
                    b.id,
                    b.patient_id,
                    p.empleo,
                    p.apellido1, 
                    p.apellido2, 
                    p.nombre, 
                    u.unidad, 
                    b.baja, 
                    b.rmnp,
                    b.motivo, 
                    b.prof, 
                    b.cie10, 
                    b.renovacion, 
                    b.info_baja, 
                    b.domicilio, 
                    b.aseguradora
                FROM 
                    bajas b
                JOIN 
                    patients p ON b.patient_id = p.id
                JOIN
                    unidades u ON p.unidad = u.id
                WHERE 
                    b.baja BETWEEN %s AND %s
                ORDER BY 
                    b.id
            ''', (start_date, end_date,))
            patients = cur.fetchall()

            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]

def search_patients_baja(nombre, apellidos):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        b.id,
                        b.patient_id,
                        p.empleo,
                        p.apellido1, 
                        p.apellido2, 
                        p.nombre, 
                        u.unidad, 
                        b.baja, 
                        b.rmnp,
                        b.motivo, 
                        b.prof, 
                        b.cie10, 
                        b.renovacion, 
                        b.info_baja, 
                        b.domicilio, 
                        b.aseguradora
                    FROM 
                        bajas b
                    JOIN 
                        patients p ON b.patient_id = p.id
                    JOIN 
                        unidades u ON p.unidad = u.id
                    WHERE 
                        unaccent(nombre) ILIKE unaccent(%s) 
                        OR (unaccent(apellido1) ILIKE unaccent(%s) OR unaccent(apellido2) ILIKE unaccent(%s))
                    ''',(f'%{nombre}%', f'%{apellidos}%', f'%{apellidos}%'))
            patients = cur.fetchall()

            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]

def get_patients_baja_by_unidad(unidad_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                SELECT 
                    b.*,
                    p.empleo,
                    p.apellido1, 
                    p.apellido2, 
                    p.nombre, 
                    u.unidad
                FROM 
                    bajas b
                JOIN 
                    patients p ON b.patient_id = p.id
                JOIN 
                    unidades u ON p.unidad = u.id
                WHERE 
                    p.unidad = %s
                ORDER BY 
                    b.id 
            ''', (unidad_id,))
            patients = cur.fetchall()
            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patients]

def delete_patients_baja(baja_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM bajas WHERE id = %s', (baja_id,))
            con.commit()

def get_patient_baja(patient_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                SELECT 
                    b.*,
                    p.empleo,
                    p.apellido1, 
                    p.apellido2, 
                    p.nombre, 
                    u.unidad
                FROM 
                    bajas b
                JOIN 
                    patients p ON b.patient_id = p.id
                JOIN 
                    unidades u ON p.unidad = u.id
                WHERE 
                    b.patient_id = %s
                ORDER BY 
                    b.id 
            ''', (patient_id,))
            patient = cur.fetchall()
            return [dict(zip([desc[0] for desc in cur.description], patient)) for patient in patient] if patient else None

"""ACCIONES"""
def add_patients_baja(  patient_id,
                        baja, 
                        rmnp, 
                        motivo,
                        prof,
                        cie10, 
                        renovacion, 
                        info, 
                        domicilio, 
                        aseguradora
                    ):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                INSERT INTO bajas (
                    patient_id, baja, rmnp, motivo, prof, cie10, renovacion, info_baja, domicilio, aseguradora
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (patient_id, baja or None, rmnp, motivo, prof, cie10 or None, renovacion or None, info, domicilio, aseguradora))
            con.commit()

