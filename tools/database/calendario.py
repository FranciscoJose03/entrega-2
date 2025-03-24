from contextlib import closing
import tools.database.database as db

def get_citas(year, month):
    with closing(db.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('''
                    SELECT
                        revision,
                        nombre 
                    FROM 
                        patients 
                    WHERE 
                        EXTRACT(YEAR FROM revision) = %s 
                        AND EXTRACT(MONTH FROM revision) = %s
                    ORDER BY
                        revision
                        ''', (year, month))
            citas = cur.fetchall()
            return citas
        