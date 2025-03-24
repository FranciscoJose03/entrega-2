from contextlib import closing
import tools.database.database as db

def get_user(name):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        *
                    FROM
                        users
                    WHERE
                        name = %s
                        ''',(name,))
            user = cur.fetchone()
            return [dict(zip([desc[0] for desc in cur.description], user))] if user else None

def get_users():
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        *
                    FROM
                        users
                        ''')
            users = cur.fetchall()
            users = sorted(users, key=lambda x: x[1])
            return users

def get_user_flask(user_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        *
                    FROM
                        users
                    WHERE
                        id = %s
                        ''',(user_id,))
            user = cur.fetchone()
            
            return [dict(zip([desc[0] for desc in cur.description], user))] if user else None

def create_user(tipo, name, password):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
                cur.execute('''
                        INSERT INTO 
                            users (tipo, name, password)
                        VALUES 
                            (%s, %s, %s)
                            ''', (tipo, name, password,))
                con.commit()
                db.logf(f'New user created: {name}. \n ¿Desea Iniciarlo? \n /aceptar_{name} \n /rechazar_{name}')

def delete_user(user, user_id):
    if(user == user_id):
        return None
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    DELETE
                    FROM 
                        users
                    WHERE
                        id = %s
                        ''',  (user_id,))
            con.commit()

def change_active_user(current_id, user_id):
    if hasattr(current_id, 'id'):
        current_id = current_id.id
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT 
                        * 
                    FROM 
                        users 
                    WHERE 
                        id = %s 
                        AND tipo = %s
                        ''', (current_id, "super"))
            if cur.fetchone():
                cur.execute('''
                        UPDATE 
                            users
                        SET 
                            active = NOT active
                        WHERE 
                            id = %s
                            ''', (user_id,))
                con.commit()
            else:
                return None

def check_user_active(user_id):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        active
                    FROM
                        users
                    WHERE
                        id = %s
                        ''', (user_id,))
            active = cur.fetchone()
            return active[0]
        