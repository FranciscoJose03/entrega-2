from contextlib import closing
import tools.database.database as db

def get_cie10_bycode(code):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        *
                    FROM
                        cie10
                    WHERE
                        code = %s
                        ''', (code,))
            cie10 = cur.fetchone()
            return cie10 if cie10 else None

def get_cie10_complete():
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        *
                    FROM
                        cie10
                        ''')
            targets = cur.fetchall()
            return {target[0]: target[1] for target in targets}
        
def add_cie10(code, name):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    INSERT INTO
                        cie10 (code, name)
                    VALUES
                        (%s, %s)
                        ''', (code, name,))
            con.commit()

def edit_cie10(code, name):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    UPDATE cie10
                    SET name = %s
                    WHERE code = %s
                        ''', (name, code))
            con.commit()

def delete_cie10(code):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    DELETE
                    FROM
                        cie10
                    WHERE
                        code = %s
                        ''', (code,))
            con.commit()
