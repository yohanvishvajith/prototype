from flask import Flask, render_template, request, jsonify, session
import os
from dotenv import load_dotenv
import mysql.connector
from blockchain import add_farmer, add_miller, add_collector
from mysql.connector import errorcode
# (Blockchain integration removed) This application no longer attempts to register users on-chain.

# load .env from project root if present
load_dotenv()

app = Flask(__name__)
# server-side sessions: set a secret key (override with FLASK_SECRET in prod)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

# MySQL configuration - change via environment variables or edit below
MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'rice_supply')


def get_connection(db=None):
    cfg = {
        'host': MYSQL_HOST,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'port': MYSQL_PORT,
        'autocommit': True,
    }
    if db:
        cfg['database'] = db
    return mysql.connector.connect(**cfg)


def init_db():
    # Create database if not exists and create users table
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` DEFAULT CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_unicode_ci';")
        cursor.close()
        conn.close()

        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id varchar(255) PRIMARY KEY,
            user_type VARCHAR(50) NOT NULL,
            nic VARCHAR(64),
            full_name VARCHAR(255),
            company_register_number VARCHAR(128),
            company_name VARCHAR(255),
            address TEXT,
            district VARCHAR(128),
            contact_number VARCHAR(64),
            password VARCHAR(255),
            total_area_of_paddy_land VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        cursor.execute(create_table)
        cursor.close()
        conn.close()
        # Create transactions table to record transfers/purchases
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_tx = '''
        CREATE TABLE IF NOT EXISTS `transaction` (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            `from` VARCHAR(255),
            `to` VARCHAR(255),
            `type` VARCHAR(100),
            quantity DECIMAL(14,3),
            `datetime` DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        try:
            cursor.execute(create_tx)
        except mysql.connector.Error as e:
            # Log and continue; table creation is best-effort
            print('Could not create transaction table:', e)
        finally:
            cursor.close()
            conn.close()
        # Create stock table to track per-user stock levels
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_stock = '''
        CREATE TABLE IF NOT EXISTS `stock` (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id varchar(255),
            `type` VARCHAR(128),
            amount DECIMAL(20,3) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (user_id),
            INDEX (`type`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        try:
            cursor.execute(create_stock)
        except mysql.connector.Error as e:
            print('Could not create stock table:', e)
        finally:
            cursor.close()
            conn.close()
        # Create paddy_type table to store available paddy types
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_paddy = '''
        CREATE TABLE IF NOT EXISTS `paddy_type` (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        try:
            cursor.execute(create_paddy)
        except mysql.connector.Error as e:
            print('Could not create paddy_type table:', e)
        finally:
            cursor.close()
            conn.close()

        print('Database initialized (database/table ensured).')
    except mysql.connector.Error as err:
        print('Failed initializing database:', err)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/app')
def app_page():
    # serve the main application page
    return render_template('index.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    role = (data.get('role') or '').strip()

    # quick admin shortcut
    if username == 'admin' and password == 'admin' and role.lower() == 'admin':
        # set a minimal session for admin
        session['user_id'] = 'admin'
        session['user_type'] = 'Admin'
        session['full_name'] = 'Administrator'
        return jsonify({'ok': True, 'role': 'Admin'})

    # quick PMB (government) shortcut
    if username.lower() == 'pmb' and password == '123456' and role.lower() == 'pmb':
        session['user_id'] = 'pmb'
        session['user_type'] = 'PMB'
        session['full_name'] = 'Government (PMB)'
        return jsonify({'ok': True, 'role': 'PMB'})

    # treat username as a string identifier (no numeric validation)
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        # verify password exists in table; if password column missing this will raise
        try:
            cur.execute('SELECT id, user_type FROM users WHERE id = %s AND password = %s LIMIT 1', (username, password))
        except mysql.connector.Error:
            # fallback: table might not have password column
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Server not configured with password column'}), 500

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

        user_type = (row.get('user_type') or '').strip()
        # match role (case-insensitive startswith) to allow slight variations
        if user_type.lower().startswith(role.lower()):
            # set server-side session values
            session['user_id'] = row.get('id')
            session['user_type'] = row.get('user_type')
            session['full_name'] = row.get('full_name')
            return jsonify({'ok': True, 'role': user_type})
        else:
            return jsonify({'ok': False, 'error': 'Role does not match user account'}), 403
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/collecter')
def collecter_page():
    return render_template('collecter.html')


@app.route('/miller')
def miller_page():
    return render_template('miller.html')


@app.route('/pmb')
def pmb_page():
    return render_template('pmb.html')


@app.route('/api/me', methods=['GET'])
def api_me():
    """Return the current logged-in user (from server-side session).
    Response: { ok: True, user_id, user_type, full_name } or 401
    """
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    return jsonify({'ok': True, 'user_id': uid, 'user_type': session.get('user_type'), 'full_name': session.get('full_name')})


def log_last_inserted_user(user_type):
    """Fetch the most recently created user's ID by user_type.
    Always return the next ID (e.g., COL5, FAR1, MIL10).
    """
    try:
        # Prefix mapping for each user type
        prefix_map = {
            "Collector": "COL",
            "Farmer": "FAR",
            "Miller": "MIL"
        }

        # Default prefix = first 3 letters of user_type if not found
        prefix = prefix_map.get(user_type, user_type[:3].upper())

        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)

        query = """
            SELECT id FROM users
            WHERE user_type = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        cur.execute(query, (user_type,))
        row = cur.fetchone()

        # Determine next numeric part
        if row and row.get("id"):
            user_id = str(row["id"])
            numeric_part = user_id[3:] if len(user_id) > 3 else "0"
            try:
                next_number = int(numeric_part) + 1
            except ValueError:
                next_number = 1
        else:
            next_number = 1

        cur.close()
        conn.close()

        # Build the new ID
        next_id = f"{prefix}{next_number}"
        return next_id

    except Exception as e:
        print("[log_last_inserted_user] Error fetching last inserted user:", e)
        return None

@app.route('/api/users', methods=['GET'])
def api_get_users():
    try:
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users ORDER BY id DESC')
        rows = cursor.fetchall()
        # add computed user_code to each row (do not store in DB)
        prefix_map = {
            'Farmer': 'FAR',
            'Collecter': 'COL',
            'Miller': 'MIL'
        }
        for r in rows:
            try:
                prefix = prefix_map.get(r.get('user_type'), 'USR')
                r['user_code'] = f"{prefix}{int(r.get('id')):06d}" if r.get('id') is not None else None
            except Exception:
                r['user_code'] = None

        cursor.close()
        conn.close()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """Return basic counts for dashboard: total farmers, collectors, millers."""
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor()
        # count by user_type using case-insensitive LIKE to be forgiving
        counts = {'farmers': 0, 'collectors': 0, 'millers': 0}
        try:
            cur.execute("SELECT user_type, COUNT(*) FROM users GROUP BY LOWER(user_type)")
        except Exception:
            # fallback: count with LIKE patterns
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(user_type) LIKE %s", ("%farmer%",))
                counts['farmers'] = cur.fetchone()[0]
            except Exception:
                counts['farmers'] = 0
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(user_type) LIKE %s", ("%collect%",))
                counts['collectors'] = cur.fetchone()[0]
            except Exception:
                counts['collectors'] = 0
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(user_type) LIKE %s", ("%miller%",))
                counts['millers'] = cur.fetchone()[0]
            except Exception:
                counts['millers'] = 0
            cur.close()
            conn.close()
            return jsonify(counts)

        rows = cur.fetchall()
        # rows are (user_type, count)
        for r in rows:
            try:
                ut = (r[0] or '').strip().lower()
                c = int(r[1] or 0)
                if 'farmer' in ut:
                    counts['farmers'] += c
                elif 'collect' in ut:
                    counts['collectors'] += c
                elif 'miller' in ut:
                    counts['millers'] += c
            except Exception:
                continue

        cur.close()
        conn.close()
        return jsonify(counts)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/stock_summary', methods=['GET'])
def api_get_stock_summary():
    """Return aggregated paddy amounts by user role (PMB, Collecter, Miller).

    Response: { pmb: number, collecter: number, miller: number }
    """
    try:
        # optional paddy_type filter from query string
        paddy_type = (request.args.get('paddy_type') or '').strip()
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor()
        # build SQL with optional filter
        try:
            if paddy_type:
                sql = "SELECT LOWER(u.user_type) as ut, SUM(s.amount) FROM `stock` s JOIN users u ON s.user_id = u.id WHERE s.`type` = %s GROUP BY LOWER(u.user_type)"
                cur.execute(sql, (paddy_type,))
            else:
                cur.execute("SELECT LOWER(u.user_type) as ut, SUM(s.amount) FROM `stock` s JOIN users u ON s.user_id = u.id GROUP BY LOWER(u.user_type)")
            rows = cur.fetchall()
        except Exception:
            # fallback: perform individual sums using LIKE, with optional paddy_type filter
            rows = []
            try:
                if paddy_type:
                    cur.execute("SELECT SUM(amount) FROM `stock` WHERE `type` = %s AND user_id IN (SELECT id FROM users WHERE LOWER(user_type) LIKE %s)", (paddy_type, "%pmb%"))
                else:
                    cur.execute("SELECT SUM(amount) FROM `stock` WHERE user_id IN (SELECT id FROM users WHERE LOWER(user_type) LIKE %s)", ("%pmb%",))
                rows.append(('pmb', cur.fetchone()[0] or 0))
            except Exception:
                rows.append(('pmb', 0))
            try:
                if paddy_type:
                    cur.execute("SELECT SUM(amount) FROM `stock` WHERE `type` = %s AND user_id IN (SELECT id FROM users WHERE LOWER(user_type) LIKE %s)", (paddy_type, "%collect%"))
                else:
                    cur.execute("SELECT SUM(amount) FROM `stock` WHERE user_id IN (SELECT id FROM users WHERE LOWER(user_type) LIKE %s)", ("%collect%",))
                rows.append(('collecter', cur.fetchone()[0] or 0))
            except Exception:
                rows.append(('collecter', 0))
            try:
                if paddy_type:
                    cur.execute("SELECT SUM(amount) FROM `stock` WHERE `type` = %s AND user_id IN (SELECT id FROM users WHERE LOWER(user_type) LIKE %s)", (paddy_type, "%miller%"))
                else:
                    cur.execute("SELECT SUM(amount) FROM `stock` WHERE user_id IN (SELECT id FROM users WHERE LOWER(user_type) LIKE %s)", ("%miller%",))
                rows.append(('miller', cur.fetchone()[0] or 0))
            except Exception:
                rows.append(('miller', 0))

        totals = {'pmb': 0.0, 'collecter': 0.0, 'miller': 0.0}
        for r in rows:
            try:
                ut = (r[0] or '').lower()
                val = float(r[1] or 0)
                if 'pmb' in ut:
                    totals['pmb'] += val
                elif 'collect' in ut:
                    totals['collecter'] += val
                elif 'miller' in ut:
                    totals['miller'] += val
            except Exception:
                continue

        cur.close()
        conn.close()
        return jsonify(totals)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/stock_history', methods=['GET'])
def api_get_stock_history():
    """Return daily stock amounts by user role for time-series chart.
    
    Response: { dates: [...], pmb: [...], collecter: [...], miller: [...] }
    """
    try:
        paddy_type = (request.args.get('paddy_type') or '').strip()
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor()
        try:
            if paddy_type:
                sql = "SELECT LOWER(u.user_type) as ut, SUM(s.amount) FROM `stock` s JOIN users u ON s.user_id = u.id WHERE s.`type` = %s GROUP BY LOWER(u.user_type)"
                cur.execute(sql, (paddy_type,))
            else:
                cur.execute("SELECT LOWER(u.user_type) as ut, SUM(s.amount) FROM `stock` s JOIN users u ON s.user_id = u.id GROUP BY LOWER(u.user_type)")
            rows = cur.fetchall()
        except Exception:
            rows = []

        totals = {'pmb': 0.0, 'collecter': 0.0, 'miller': 0.0}
        for r in rows:
            try:
                ut = (r[0] or '').lower()
                val = float(r[1] or 0)
                if 'pmb' in ut:
                    totals['pmb'] += val
                elif 'collect' in ut:
                    totals['collecter'] += val
                elif 'miller' in ut:
                    totals['miller'] += val
            except Exception:
                continue

        cur.close()
        conn.close()
        
        # Generate 7 days of data (simulation: variations around current totals)
        import datetime
        import random
        dates = []
        pmb_series = []
        col_series = []
        mil_series = []
        today = datetime.date.today()
        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            dates.append(d.strftime('%Y-%m-%d'))
            factor = 0.8 + (0.4 * (6-i)/6)
            pmb_series.append(round(totals['pmb'] * factor + random.uniform(-5, 5), 2))
            col_series.append(round(totals['collecter'] * factor + random.uniform(-10, 10), 2))
            mil_series.append(round(totals['miller'] * factor + random.uniform(-10, 10), 2))
        
        return jsonify({
            'dates': dates,
            'pmb': pmb_series,
            'collecter': col_series,
            'miller': mil_series
        })
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/users/by_type', methods=['GET'])
def api_get_users_by_type():
    """Return list of users for a given user type.
    Query params:
      - type (string): user type to filter by (case-insensitive, substring match)
    Response: JSON array of {id, full_name, user_code}
    """
    typ = (request.args.get('type') or request.args.get('user_type') or '').strip()
    if not typ:
        return jsonify({'error': 'query parameter "type" is required'}), 400

    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        # Case-insensitive substring match to be forgiving with stored values
        sql = 'SELECT id, full_name FROM users WHERE LOWER(user_type) LIKE %s ORDER BY id'
        cur.execute(sql, (f"%{typ.lower()}%",))
        rows = cur.fetchall()

        prefix_map = {
            'Farmer': 'FAR',
            'Collecter': 'COL',
            'Miller': 'MIL'
        }
        out = []
        for r in rows:
            try:
                prefix = prefix_map.get(r.get('user_type'), 'USR')
                user_code = f"{prefix}{int(r.get('id')):06d}" if r.get('id') is not None else None
            except Exception:
                user_code = None
            out.append({'id': r.get('id'), 'full_name': r.get('full_name'), 'user_code': user_code})

        cur.close()
        conn.close()
        return jsonify(out)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/transactions', methods=['POST'])
def api_add_transaction():
    """Insert a transaction record into the transaction table.
    Expects JSON body: { from, to, type, quantity, datetime }
    """
    payload = request.get_json() or {}
    from_val = payload.get('from')
    to_val = payload.get('to')
    ttype = payload.get('type')
    quantity = payload.get('quantity')
    dt = payload.get('datetime')

    # basic validation
    if from_val is None or to_val is None or not ttype or quantity is None:
        return jsonify({'ok': False, 'error': 'Missing required fields (from,to,type,quantity)'}), 400

    try:
        # convert quantity to Decimal-like value (float is acceptable here)
        qty = float(quantity)
    except Exception:
        return jsonify({'ok': False, 'error': 'Invalid quantity'}), 400

    try:
        conn = get_connection(MYSQL_DATABASE)
        # perform insert + stock update atomically
        try:
            conn.start_transaction()
        except Exception:
            # some connectors use begin; ignore if not available
            pass
        cur = conn.cursor()
        # Determine sender type
        sender_type = None
        try:
            cur.execute('SELECT user_type FROM users WHERE id = %s LIMIT 1', (str(from_val),))
            urow = cur.fetchone()
            sender_type = urow[0] if urow else None
        except Exception:
            sender_type = None

        # If sender is not a Farmer, ensure they have sufficient stock before proceeding
        try:
            if not (isinstance(sender_type, str) and sender_type.strip().lower().startswith('farmer')):
                # lock sender stock row for update
                sel_s_sql = 'SELECT id, amount FROM `stock` WHERE user_id = %s AND `type` = %s FOR UPDATE'
                cur.execute(sel_s_sql, (str(from_val), ttype))
                srow = cur.fetchone()
                if not srow:
                    # no stock row -> insufficient
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cur.close()
                    conn.close()
                    return jsonify({'ok': False, 'error': 'Insufficient stock: sender has no stock for this paddy type'}), 400
                s_stock_id, s_current = srow[0], srow[1] if srow[1] is not None else 0
                if float(s_current) < float(qty):
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cur.close()
                    conn.close()
                    return jsonify({'ok': False, 'error': 'Insufficient stock: sender balance is lower than requested quantity'}), 400
                # deduct now (will be committed later)
                s_new = float(s_current) - float(qty)
                upd_s_sql = 'UPDATE `stock` SET amount = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s'
                cur.execute(upd_s_sql, (s_new, s_stock_id))

        except mysql.connector.Error as e:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Failed checking/deducting sender stock: ' + str(e)}), 500

        # Update recipient stock: if a row exists for (to_val, ttype) increment amount, else insert
        try:
            sel_sql = 'SELECT id, amount FROM `stock` WHERE user_id = %s AND `type` = %s FOR UPDATE'
            cur.execute(sel_sql, (str(to_val), ttype))
            row = cur.fetchone()
            if row:
                stock_id, current_amount = row[0], row[1] if row[1] is not None else 0
                new_amount = float(current_amount) + float(qty)
                upd_sql = 'UPDATE `stock` SET amount = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s'
                cur.execute(upd_sql, (new_amount, stock_id))
            else:
                ins_sql = 'INSERT INTO `stock` (user_id, `type`, amount) VALUES (%s, %s, %s)'
                cur.execute(ins_sql, (str(to_val), ttype, qty))
        except mysql.connector.Error as e:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Failed updating recipient stock: ' + str(e)}), 500

        # Now insert the transaction record (after stock updates)
        try:
            insert_sql = 'INSERT INTO `transaction` (`from`, `to`, `type`, quantity, `datetime`) VALUES (%s, %s, %s, %s, %s)'
            cur.execute(insert_sql, (str(from_val), str(to_val), ttype, qty, dt))
            last_id = cur.lastrowid
        except mysql.connector.Error as e:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Failed inserting transaction: ' + str(e)}), 500
        except mysql.connector.Error as e:
            # if stock update fails, rollback the transaction and return error
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Failed updating stock: ' + str(e)}), 500

        # commit both transaction insert and stock update
        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Failed to commit transaction'}), 500

        cur.close()
        conn.close()
        return jsonify({'ok': True, 'id': last_id}), 201
    except mysql.connector.Error as err:
        return jsonify({'ok': False, 'error': str(err)}), 500


@app.route('/api/transactions', methods=['GET'])
def api_get_transactions():
    """Return transactions. Optional query param `to` to filter by recipient (matches transaction.`to`).
    """
    to_param = request.args.get('to')
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        if to_param:
            sql = 'SELECT id, `from`, `to`, `type`, quantity, `datetime`, created_at FROM `transaction` WHERE `to` = %s ORDER BY id DESC'
            cur.execute(sql, (str(to_param),))
        else:
            sql = 'SELECT id, `from`, `to`, `type`, quantity, `datetime`, created_at FROM `transaction` ORDER BY id DESC LIMIT 200'
            cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/paddy_types', methods=['GET'])
def api_get_paddy_types():
    """Return list of paddy types from paddy_type table."""
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT id, name FROM paddy_type ORDER BY id')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/users', methods=['POST'])
def api_add_user():
    payload = request.get_json() or {}
    user_type = payload.get('userType')
    # map fields safely and normalize to single address and full_name
    nic = payload.get('nic')
    full_name = payload.get('fullName')
    company_register_number = payload.get('companyRegisterNumber')
    company_name = payload.get('companyName')
    # accept either a single 'address' or the older per-type fields and coalesce
    address = payload.get('address') or payload.get('homeAddress') or payload.get('collectorAddress') or payload.get('millerAddress') or ''
    district = payload.get('district')
    contact_number = payload.get('contactNumber')
    total_area = payload.get('totalAreaOfPaddyLand')
    id = (log_last_inserted_user(user_type))

    # If creating a PMB account, enforce single-account rule and fixed id
    try:
        if isinstance(user_type, str) and user_type.strip().lower().startswith('pmb'):
            conn_chk = get_connection(MYSQL_DATABASE)
            cur_chk = conn_chk.cursor()
            # check if any existing PMB user exists (by user_type or id)
            cur_chk.execute("SELECT id FROM users WHERE LOWER(user_type) = %s OR LOWER(id) = %s LIMIT 1", ('pmb', 'pmb'))
            existing = cur_chk.fetchone()
            cur_chk.close()
            conn_chk.close()
            if existing:
                return jsonify({'ok': False, 'error': 'PMB account already exists'}), 400
            # set the id explicitly to 'PMB'
            id = 'PMB'
    except Exception:
        # if check fails for some reason, continue and let insert raise if needed
        try:
            cur_chk.close()
        except Exception:
            pass
        try:
            conn_chk.close()
        except Exception:
            pass
   
    try:
        if(user_type=="Farmer"):
            try:
                add_farmer(
                    id,
                        nic,
                    full_name,
                    address,
                    district,
                    contact_number,
                123,
                    0.0,
                )
                print("add_farmer call finished.")
            except Exception as e:
                print("add_farmer raised an exception:", e)
        elif(user_type=="Miller"):
             add_miller(
            id,
            company_register_number,
            company_name,
            address,
            district,
            contact_number,
            0.0,
        )
        elif(user_type=="Collecter"):
            add_collector(
            id,
            nic,
            full_name,
            address,
            district,
            contact_number,
            0.0,
        )
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        insert_sql = '''
            INSERT INTO users (user_type, nic, full_name, company_register_number, company_name, address, district, contact_number, total_area_of_paddy_land,id,password)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        '''
        cursor.execute(insert_sql, (user_type, nic, full_name, company_register_number, company_name, address, district, contact_number, total_area,id,"123456"))
        # Try to get the inserted id reliably. Prefer cursor.lastrowid, but fall back to LAST_INSERT_ID().
        last_id = cursor.lastrowid
        if not last_id:
            try:
                cursor.execute('SELECT LAST_INSERT_ID()')
                last_id_row = cursor.fetchone()
                if last_id_row:
                    # fetchone() returns a tuple like (id,)
                    last_id = last_id_row[0]
            except Exception:
                last_id = None

        # Ensure the insert is committed
        try:
            conn.commit()
        except Exception:
            pass

        # compute a user_code for the response (do not persist)
        prefix_map = {
            'Farmer': 'FAR',
            'Collecter': 'COL',
            'Miller': 'MIL'
        }

        cursor.close()

    # If the client provided initial stock (paddy types + quantities), insert them
        # Use the application id we attempted to insert (variable `id`) if present,
        # otherwise fall back to the numeric last_id returned by the connector.
        created_user_id = id or last_id
        try:
            stock_items = payload.get('stock') if isinstance(payload, dict) else None
        except Exception:
            stock_items = None
        # Do not insert initial stock for Farmers or PMB
        is_no_stock = False
        try:
            is_no_stock = isinstance(user_type, str) and (user_type.strip().lower().startswith('farmer') or user_type.strip().lower().startswith('pmb'))
        except Exception:
            is_no_stock = False

        if stock_items and created_user_id and not is_no_stock:
            try:
                s_cur = conn.cursor()
                for si in stock_items:
                    # accept either {paddyType, quantity} or {type, quantity}
                    ptype = si.get('paddyType') if isinstance(si, dict) else None
                    if not ptype:
                        ptype = si.get('type') if isinstance(si, dict) else None
                    qty = None
                    try:
                        qty = float(si.get('quantity')) if isinstance(si, dict) and si.get('quantity') is not None else None
                    except Exception:
                        qty = None
                    if ptype and qty is not None:
                        try:
                            s_cur.execute('INSERT INTO `stock` (user_id, `type`, amount) VALUES (%s, %s, %s)', (str(created_user_id), ptype, qty))
                        except Exception as _:
                            # ignore individual stock insert failures but continue
                            pass
                try:
                    conn.commit()
                except Exception:
                    pass
                s_cur.close()
            except Exception:
                # ignore stock insertion errors to avoid blocking user creation
                pass

        # return the inserted row with a computed user_code
        rc = conn.cursor(dictionary=True)
        row = None
        if last_id:
            rc.execute('SELECT * FROM users WHERE id = %s', (last_id,))
            row = rc.fetchone()
            if row is not None:
                try:
                    prefix = prefix_map.get(user_type, 'USR')
                    row['user_code'] = f"{prefix}{int(last_id):06d}"
                except Exception:
                    row['user_code'] = None
        else:
            # As a safe fallback, try to return the most recent row matching some of the unique fields
            try:
                rc.execute('SELECT * FROM users WHERE user_type = %s ORDER BY id DESC LIMIT 1', (user_type,))
                row = rc.fetchone()
                if row and row.get('id') is not None:
                    try:
                        prefix = prefix_map.get(row.get('user_type'), 'USR')
                        row['user_code'] = f"{prefix}{int(row.get('id')):06d}"
                    except Exception:
                        row['user_code'] = None
            except Exception:
                row = None

        rc.close()
        conn.close()
        # Return the created user row (blockchain integration removed)
        if row is None:
            row = {}
        return jsonify(row), 201
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
