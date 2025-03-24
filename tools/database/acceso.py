from contextlib import closing
import tools.database.database as db

def get_ips_allow():
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        *
                    FROM
                        ips
                        ''')
            ips = cur.fetchall()
            return ips
        
def is_ip_allow(ip):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        COUNT(*)
                    FROM
                        ips
                    WHERE
                        ip_address = %s
                        ''', (ip,))
            result = cur.fetchone()
            return int(result[0] > 0) 

def add_allowed_ip(ip, ip_for):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            if is_ip_allow(ip):
                db.logf(f"{ip} - Already exists.")
                return False
            else:
                cur.execute('''
                        INSERT INTO 
                            ips (ip_address, create_for) 
                        VALUES
                            (%s, %s)
                            ''', (ip, ip_for))
                db.logf(f"{ip} - Has been ADD.")
                con.commit()

def remove_allowed_ip(ip):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    DELETE
                    FROM
                        ips
                    WHERE
                        ip_address = %s
                        ''', (ip,))
            db.logf(f"{ip} - Has been deleted.")
            con.commit()

def edit_allowed_ip(ipin, ipexist, ip_for_exist, ip_for_in):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    UPDATE
                        ips
                    SET
                        ip_address = %s,
                        create_for = %s
                    WHERE
                        ip_address = %s AND create_for = %s
                        ''', (ipin, ip_for_in, ipexist, ip_for_exist))
            db.logf(f"{ipexist} - Has been changed to {ipin}.")
            con.commit()