import sqlite3 as sql
import json

PROCESSING = 'processing'
COMPLETE = 'complete'
FAILED = 'failed'

database_path = './database/mlinsta.db'


def insert_account(username):
    con = sql.connect(database_path)
    cur = con.cursor()

    try:
        cur.execute("INSERT INTO ACCOUNT_INFO (username,q1_status,q2_status,q3_status,result) "
                    "VALUES (?,?,?,?,?)", (username, 'pending', 'pending', 'pending', None))
        con.commit()
        con.close()
    except sql.IntegrityError as e:
        cur.execute(
            "UPDATE ACCOUNT_INFO SET q2_status = CASE WHEN q2_status == 'failed' THEN 'pending' ELSE q2_status END WHERE username = ?",
            (username,))
        con.commit()
        con.close()


def update_queue_status(username, queue, status):
    con = sql.connect(database_path)
    cur = con.cursor()

    query = "UPDATE ACCOUNT_INFO SET q{}_status = ? WHERE username = ?".format(queue)

    cur.execute(query, (status, username))
    con.commit()
    con.close()


def is_complete(username, queue_number):
    con = sql.connect(database_path)
    cur = con.cursor()

    query = None

    if queue_number == 1:
        query = "SELECT q1_status FROM ACCOUNT_INFO WHERE username = ?"
    elif queue_number == 2:
        query = "SELECT q2_status FROM ACCOUNT_INFO WHERE username = ?"
    elif queue_number == 3:
        query = "SELECT q3_status FROM ACCOUNT_INFO WHERE username = ?"

    if query:
        cur.execute(query, (username,))
        row = cur.fetchone()
        return row[0] == 'complete'
    else:
        return False


def write_results(username, json_string):
    con = sql.connect(database_path)
    cur = con.cursor()

    cur.execute("UPDATE ACCOUNT_INFO SET result = ? WHERE username = ?", (json_string, username))
    con.commit()
    con.close()


def get_results(username):
    con = sql.connect(database_path)
    cur = con.cursor()

    cur.execute("SELECT result FROM ACCOUNT_INFO WHERE username = ?", (username,))
    row = cur.fetchone()

    if row:
        return row[0]
    else:
        return '{}'


def get_status(username):
    con = sql.connect(database_path)
    cur = con.cursor()

    cur.execute("SELECT "
                "q1_status, "
                "q2_status, "
                "q3_status, "
                "q1_progress, "
                "q2_progress, "
                "q1_exec_time, "
                "q2_exec_time, "
                "result "
                "FROM ACCOUNT_INFO WHERE username = ?", (username,))
    row = cur.fetchone()

    if row:
        status = {
            "1_grab_queue": {
                "status": row[0],
                "grabbed": row[3],
                "exec_time": row[5]
            },
            "2_scrape_queue": {
                "status": row[1],
                "scraped": row[4],
                "exec_time": row[6]
            },
            "3_predict_queue": {
                "status": row[2],
                "result": row[7]
            },
        }
        return json.dumps(status)
    else:
        return json.dumps({})


def should_queue(username):
    con = sql.connect(database_path)
    cur = con.cursor()

    cur.execute("SELECT q1_status, q2_status, q3_status FROM ACCOUNT_INFO WHERE username = ?", (username,))
    row = cur.fetchone()

    return not row or (row[0] == FAILED or row[1] == FAILED or row[2] == FAILED)


################# GRAB UTILITY FUNCTIONS ########################

def update_grab_progress(username, grabbed, exec_time):
    con = sql.connect(database_path)
    cur = con.cursor()

    cur.execute("UPDATE ACCOUNT_INFO SET q1_progress = ?, q1_exec_time = ? WHERE username = ?", (grabbed, exec_time, username))
    con.commit()

    con.close()


def update_grab_execution_time(username, exec_time):
    con = sql.connect(database_path)
    cur = con.cursor()

    cur.execute("UPDATE ACCOUNT_INFO SET q1_exec_time = ? WHERE username = ?", (exec_time, username))
    con.commit()

    con.close()
