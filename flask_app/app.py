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
        # Create damage table to track damaged inventory
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_damage = '''
        CREATE TABLE IF NOT EXISTS `damage` (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(255),
            paddy_type VARCHAR(128),
            quantity DECIMAL(14,3),
            reason TEXT,
            damage_date DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (user_id),
            INDEX (paddy_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        try:
            cursor.execute(create_damage)
        except mysql.connector.Error as e:
            print('Could not create damage table:', e)
        finally:
            cursor.close()
            conn.close()
        # Create milling table to track milling process
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_milling = '''
        CREATE TABLE IF NOT EXISTS `milling` (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            miller_id VARCHAR(255),
            paddy_type VARCHAR(128),
            input_paddy DECIMAL(14,3),
            output_rice DECIMAL(14,3),
            milling_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (miller_id),
            INDEX (paddy_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        try:
            cursor.execute(create_milling)
        except mysql.connector.Error as e:
            print('Could not create milling table:', e)
        finally:
            cursor.close()
            conn.close()
        # Create rice_stock table to track rice inventory from milling
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        create_rice_stock = '''
        CREATE TABLE IF NOT EXISTS `rice_stock` (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            miller_id VARCHAR(255),
            paddy_type VARCHAR(128),
            quantity DECIMAL(14,3),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (miller_id),
            INDEX (paddy_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''
        try:
            cursor.execute(create_rice_stock)
        except mysql.connector.Error as e:
            print('Could not create rice_stock table:', e)
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


@app.route('/wholesaler')
def wholesaler_page():
    return render_template('wholesaler.html')


@app.route('/retailer')
def retailer_page():
    return render_template('retailer.html')


@app.route('/beer')
def beer_page():
    return render_template('beer.html')


@app.route('/animalfood')
def animalfood_page():
    return render_template('animalfood.html')


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
            "Miller": "MIL",
            "Wholesaler": "WHO",
            "Retailer": "RET",
            "Beer": "BER",
            "Animal Food": "ANI"
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
            'Miller': 'MIL',
            'Wholesaler': 'WHO',
            'Retailer': 'RET',
            'Beer': 'BER',
            'Animal Food': 'ANI'
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
        counts = {'farmers': 0, 'collectors': 0, 'millers': 0, 'wholesalers': 0, 'retailers': 0, 'beer': 0, 'animalfood': 0}
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
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(user_type) LIKE %s", ("%wholesaler%",))
                counts['wholesalers'] = cur.fetchone()[0]
            except Exception:
                counts['wholesalers'] = 0
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(user_type) LIKE %s", ("%retailer%",))
                counts['retailers'] = cur.fetchone()[0]
            except Exception:
                counts['retailers'] = 0
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(user_type) LIKE %s", ("%beer%",))
                counts['beer'] = cur.fetchone()[0]
            except Exception:
                counts['beer'] = 0
            try:
                cur.execute("SELECT COUNT(*) FROM users WHERE user_type = %s", ("Animal Food",))
                counts['animalfood'] = cur.fetchone()[0]
            except Exception:
                counts['animalfood'] = 0
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
                elif 'wholesaler' in ut:
                    counts['wholesalers'] += c
                elif 'retailer' in ut:
                    counts['retailers'] += c
                elif 'beer' in ut:
                    counts['beer'] += c
                elif 'animal food' in ut:
                    counts['animalfood'] += c
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
        sql = 'SELECT id, full_name, user_type FROM users WHERE LOWER(user_type) LIKE %s ORDER BY id'
        cur.execute(sql, (f"%{typ.lower()}%",))
        rows = cur.fetchall()

        prefix_map = {
            'Farmer': 'FAR',
            'Collecter': 'COL',
            'Miller': 'MIL',
            'Wholesaler': 'WHO',
            'Retailer': 'RET',
            'Beer': 'BER',
            'Animal Food': 'ANI'
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


@app.route('/api/damages', methods=['POST'])
def api_add_damage():
    """Insert a damage record into the damage table and deduct from stock.
    Expects JSON body: { user_id, paddy_type, quantity, reason, damage_date }
    Validates that sufficient stock exists before recording damage.
    """
    payload = request.get_json() or {}
    user_id = payload.get('user_id')
    paddy_type = payload.get('paddy_type')
    quantity = payload.get('quantity')
    reason = payload.get('reason')
    damage_date = payload.get('damage_date')

    # basic validation
    if not user_id or not paddy_type or quantity is None or not reason:
        return jsonify({'ok': False, 'error': 'Missing required fields (user_id, paddy_type, quantity, reason)'}), 400

    try:
        qty = float(quantity)
        if qty <= 0:
            return jsonify({'ok': False, 'error': 'Quantity must be greater than 0'}), 400
    except Exception:
        return jsonify({'ok': False, 'error': 'Invalid quantity'}), 400

    try:
        conn = get_connection(MYSQL_DATABASE)
        # Start transaction
        try:
            conn.start_transaction()
        except Exception:
            pass
        
        cur = conn.cursor()
        
        # Check if sufficient stock exists for this user and paddy type
        cur.execute('SELECT id, amount FROM `stock` WHERE user_id = %s AND `type` = %s FOR UPDATE', 
                    (str(user_id), paddy_type))
        stock_row = cur.fetchone()
        
        if not stock_row:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': f'No stock found for paddy type "{paddy_type}". Cannot record damage.'}), 400
        
        stock_id, current_amount = stock_row[0], stock_row[1] if stock_row[1] is not None else 0
        
        if float(current_amount) < qty:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': f'Insufficient stock. Available: {current_amount} kg, Requested: {qty} kg'}), 400
        
        # Deduct from stock
        new_amount = float(current_amount) - qty
        cur.execute('UPDATE `stock` SET amount = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s', 
                    (new_amount, stock_id))
        
        # Insert damage record
        insert_sql = 'INSERT INTO `damage` (user_id, paddy_type, quantity, reason, damage_date) VALUES (%s, %s, %s, %s, %s)'
        cur.execute(insert_sql, (str(user_id), paddy_type, qty, reason, damage_date))
        last_id = cur.lastrowid
        
        # Commit transaction
        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Failed to commit damage record'}), 500
        
        cur.close()
        conn.close()
        return jsonify({'ok': True, 'id': last_id, 'remaining_stock': new_amount}), 201
    except mysql.connector.Error as err:
        return jsonify({'ok': False, 'error': str(err)}), 500


@app.route('/api/damages', methods=['GET'])
def api_get_damages():
    """Return damage records. Optional query param `user_id` to filter by user.
    """
    user_id_param = request.args.get('user_id')
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        if user_id_param:
            sql = 'SELECT id, user_id, paddy_type, quantity, reason, damage_date, created_at FROM `damage` WHERE user_id = %s ORDER BY id DESC'
            cur.execute(sql, (str(user_id_param),))
        else:
            sql = 'SELECT id, user_id, paddy_type, quantity, reason, damage_date, created_at FROM `damage` ORDER BY id DESC LIMIT 200'
            cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/stock_by_district', methods=['GET'])
def api_get_stock_by_district():
    """Return stock grouped by district for Millers and Collectors.
    Optional query param: paddy_type to filter by specific paddy type.
    If no paddy_type specified, returns breakdown by paddy type.
    
    Response when paddy_type specified: {
        districts: [...district names...],
        collectors: [...stock amounts by district...],
        millers: [...stock amounts by district...]
    }
    
    Response when no paddy_type: {
        districts: [...district names...],
        paddy_types: [...list of paddy types...],
        data: {
            collectors: { paddy_type: [amounts_by_district] },
            millers: { paddy_type: [amounts_by_district] }
        }
    }
    """
    paddy_type = request.args.get('paddy_type', '').strip()
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor()
        
        if paddy_type:
            # Single paddy type selected - simple aggregation
            # Query for collectors stock by district
            collector_sql = '''
                SELECT u.district, SUM(s.amount) as total
                FROM stock s
                JOIN users u ON s.user_id = u.id
                WHERE LOWER(u.user_type) LIKE %s AND s.type = %s
                GROUP BY u.district
                ORDER BY u.district
            '''
            cur.execute(collector_sql, ('%collect%', paddy_type))
            collector_rows = cur.fetchall()
            collector_data = {str(row[0] or 'Unknown'): float(row[1] or 0) for row in collector_rows}
            
            # Query for millers stock by district
            miller_sql = '''
                SELECT u.district, SUM(s.amount) as total
                FROM stock s
                JOIN users u ON s.user_id = u.id
                WHERE LOWER(u.user_type) LIKE %s AND s.type = %s
                GROUP BY u.district
                ORDER BY u.district
            '''
            cur.execute(miller_sql, ('%miller%', paddy_type))
            miller_rows = cur.fetchall()
            miller_data = {str(row[0] or 'Unknown'): float(row[1] or 0) for row in miller_rows}
            
            # Combine all districts
            all_districts = sorted(set(list(collector_data.keys()) + list(miller_data.keys())))
            
            # Build response arrays aligned to districts
            collector_amounts = [collector_data.get(d, 0) for d in all_districts]
            miller_amounts = [miller_data.get(d, 0) for d in all_districts]
            
            cur.close()
            conn.close()
            
            return jsonify({
                'districts': all_districts,
                'collectors': collector_amounts,
                'millers': miller_amounts
            })
        else:
            # No paddy type selected - return breakdown by type
            # Query for collectors stock by district and paddy type
            collector_sql = '''
                SELECT u.district, s.type, SUM(s.amount) as total
                FROM stock s
                JOIN users u ON s.user_id = u.id
                WHERE LOWER(u.user_type) LIKE %s
                GROUP BY u.district, s.type
                ORDER BY u.district, s.type
            '''
            cur.execute(collector_sql, ('%collect%',))
            collector_rows = cur.fetchall()
            
            # Query for millers stock by district and paddy type
            miller_sql = '''
                SELECT u.district, s.type, SUM(s.amount) as total
                FROM stock s
                JOIN users u ON s.user_id = u.id
                WHERE LOWER(u.user_type) LIKE %s
                GROUP BY u.district, s.type
                ORDER BY u.district, s.type
            '''
            cur.execute(miller_sql, ('%miller%',))
            miller_rows = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Organize data by district and paddy type
            all_districts = set()
            all_paddy_types = set()
            collector_data = {}  # {paddy_type: {district: amount}}
            miller_data = {}     # {paddy_type: {district: amount}}
            
            for row in collector_rows:
                district = str(row[0] or 'Unknown')
                ptype = str(row[1] or 'Unknown')
                amount = float(row[2] or 0)
                all_districts.add(district)
                all_paddy_types.add(ptype)
                if ptype not in collector_data:
                    collector_data[ptype] = {}
                collector_data[ptype][district] = amount
            
            for row in miller_rows:
                district = str(row[0] or 'Unknown')
                ptype = str(row[1] or 'Unknown')
                amount = float(row[2] or 0)
                all_districts.add(district)
                all_paddy_types.add(ptype)
                if ptype not in miller_data:
                    miller_data[ptype] = {}
                miller_data[ptype][district] = amount
            
            all_districts = sorted(all_districts)
            all_paddy_types = sorted(all_paddy_types)
            
            # Build response with arrays aligned to districts for each paddy type
            collector_by_type = {}
            miller_by_type = {}
            
            for ptype in all_paddy_types:
                collector_by_type[ptype] = [collector_data.get(ptype, {}).get(d, 0) for d in all_districts]
                miller_by_type[ptype] = [miller_data.get(ptype, {}).get(d, 0) for d in all_districts]
            
            return jsonify({
                'districts': all_districts,
                'paddy_types': all_paddy_types,
                'data': {
                    'collectors': collector_by_type,
                    'millers': miller_by_type
                }
            })
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/stock_by_user', methods=['GET'])
def api_get_stock_by_user():
    """Return stock totals by user for a given user_type (Collector or Miller).
    Query params:
      - user_type (required): collector|miller
      - paddy_type (optional): filter by paddy type
      - district (optional): filter by district
      - q (optional): search query to match id, full_name or nic (substring, case-insensitive)

    Response: [ { id, full_name, nic, district, total } ] sorted by total DESC
    """
    user_type = (request.args.get('user_type') or '').strip()
    paddy_type = (request.args.get('paddy_type') or '').strip()
    district = (request.args.get('district') or '').strip()
    q = (request.args.get('q') or '').strip()

    if not user_type:
        return jsonify({'error': 'user_type is required (collector or miller)'}), 400

    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)

        params = []
        user_like = f"%{user_type.lower()}%"

        if paddy_type:
            sql = '''
                SELECT u.id, u.full_name, u.nic, u.district, SUM(s.amount) AS total
                FROM stock s
                JOIN users u ON s.user_id = u.id
                WHERE LOWER(u.user_type) LIKE %s AND s.type = %s
            '''
            params = [user_like, paddy_type]
        else:
            sql = '''
                SELECT u.id, u.full_name, u.nic, u.district, SUM(s.amount) AS total
                FROM stock s
                JOIN users u ON s.user_id = u.id
                WHERE LOWER(u.user_type) LIKE %s
            '''
            params = [user_like]

        if district:
            sql += " AND u.district = %s"
            params.append(district)

        if q:
            # match id, full_name or nic
            sql += " AND (u.id LIKE %s OR LOWER(u.full_name) LIKE %s OR LOWER(u.nic) LIKE %s)"
            qparam = f"%{q}%"
            params.extend([qparam, qparam.lower(), qparam.lower()])

        sql += ' GROUP BY u.id, u.full_name, u.nic, u.district ORDER BY total DESC'

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        out = []
        for r in rows:
            out.append({
                'id': r.get('id'),
                'full_name': r.get('full_name'),
                'nic': r.get('nic'),
                'district': r.get('district'),
                'total': float(r.get('total') or 0)
            })
        return jsonify(out)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/stock_user_detail', methods=['GET'])
def api_get_stock_user_detail():
    """Return per-paddy-type stock for a given user_id.
    Query param: user_id
    Response: [ { type, amount } ]
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT `type`, amount FROM stock WHERE user_id = %s ORDER BY `type`', (str(user_id),))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        out = []
        for r in rows:
            out.append({'type': r.get('type'), 'amount': float(r.get('amount') or 0)})
        return jsonify(out)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
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
            'Miller': 'MIL',
            'Wholesaler': 'WHO',
            'Retailer': 'RET',
            'Beer': 'BER',
            'Animal Food': 'ANI'
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

        # If the client provided initial rice stock (for Miller), insert them into rice_stock table
        try:
            rice_items = payload.get('riceStock') if isinstance(payload, dict) else None
        except Exception:
            rice_items = None

        if rice_items and created_user_id:
            try:
                r_cur = conn.cursor()
                for ri in rice_items:
                    ptype = ri.get('paddyType') if isinstance(ri, dict) else None
                    qty = None
                    try:
                        qty = float(ri.get('quantity')) if isinstance(ri, dict) and ri.get('quantity') is not None else None
                    except Exception:
                        qty = None
                    if ptype and qty is not None:
                        try:
                            r_cur.execute('INSERT INTO `rice_stock` (miller_id, paddy_type, quantity) VALUES (%s, %s, %s)', (str(created_user_id), ptype, qty))
                        except Exception as _:
                            # ignore individual rice stock insert failures but continue
                            pass
                try:
                    conn.commit()
                except Exception:
                    pass
                r_cur.close()
            except Exception:
                # ignore rice stock insertion errors to avoid blocking user creation
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


@app.route('/api/milling', methods=['POST'])
def api_add_milling():
    """Insert a milling record into the milling table.
    Expects JSON body: { miller_id, paddy_type, input_paddy, output_rice, milling_date }
    """
    payload = request.get_json() or {}
    miller_id = payload.get('miller_id')
    paddy_type = payload.get('paddy_type')
    input_paddy = payload.get('input_paddy')
    output_rice = payload.get('output_rice')
    milling_date = payload.get('milling_date')

    # basic validation
    if not miller_id or not paddy_type or input_paddy is None or output_rice is None:
        return jsonify({'ok': False, 'error': 'Missing required fields (miller_id, paddy_type, input_paddy, output_rice)'}), 400

    try:
        input_qty = float(input_paddy)
        output_qty = float(output_rice)
        if output_qty > input_qty:
            return jsonify({'ok': False, 'error': 'Output rice cannot exceed input paddy'}), 400
    except Exception:
        return jsonify({'ok': False, 'error': 'Invalid quantity values'}), 400

    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        
        # 1. Validate miller has enough stock
        cur.execute('SELECT id, amount FROM `stock` WHERE user_id = %s AND `type` = %s', (str(miller_id), paddy_type))
        stock_row = cur.fetchone()
        
        if not stock_row:
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': f'No stock found for paddy type: {paddy_type}'}), 400
        
        current_stock = float(stock_row['amount'])
        if current_stock < input_qty:
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': f'Insufficient stock. Available: {current_stock} kg, Required: {input_qty} kg'}), 400
        
        # 2. Insert milling record
        insert_sql = 'INSERT INTO `milling` (miller_id, paddy_type, input_paddy, output_rice, milling_date) VALUES (%s, %s, %s, %s, %s)'
        cur.execute(insert_sql, (str(miller_id), paddy_type, input_qty, output_qty, milling_date))
        last_id = cur.lastrowid
        
        # 3. Deduct input_paddy from stock table
        new_amount = current_stock - input_qty
        cur.execute('UPDATE `stock` SET amount = %s WHERE id = %s', (new_amount, stock_row['id']))
        
        # 3. Add output_rice to rice_stock table
        # Check if rice_stock record exists for this miller and paddy type
        cur.execute('SELECT id, quantity FROM `rice_stock` WHERE miller_id = %s AND paddy_type = %s', (str(miller_id), paddy_type))
        rice_row = cur.fetchone()
        if rice_row:
            new_rice_qty = float(rice_row['quantity']) + output_qty
            cur.execute('UPDATE `rice_stock` SET quantity = %s WHERE id = %s', (new_rice_qty, rice_row['id']))
        else:
            cur.execute('INSERT INTO `rice_stock` (miller_id, paddy_type, quantity) VALUES (%s, %s, %s)', (str(miller_id), paddy_type, output_qty))
        
        try:
            conn.commit()
        except Exception:
            pass
        
        cur.close()
        conn.close()
        return jsonify({'ok': True, 'id': last_id}), 201
    except mysql.connector.Error as err:
        return jsonify({'ok': False, 'error': str(err)}), 500


@app.route('/api/milling', methods=['GET'])
def api_get_milling():
    """Return milling records. Optional query param `miller_id` to filter by miller.
    """
    miller_id_param = request.args.get('miller_id')
    try:
        conn = get_connection(MYSQL_DATABASE)
        cur = conn.cursor(dictionary=True)
        if miller_id_param:
            sql = 'SELECT id, miller_id, paddy_type, input_paddy, output_rice, milling_date, created_at FROM `milling` WHERE miller_id = %s ORDER BY id DESC'
            cur.execute(sql, (str(miller_id_param),))
        else:
            sql = 'SELECT id, miller_id, paddy_type, input_paddy, output_rice, milling_date, created_at FROM `milling` ORDER BY id DESC LIMIT 200'
            cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/users/<user_id>', methods=['PUT'])
def api_update_user(user_id):
    payload = request.get_json() or {}
    
    # Extract fields from payload
    nic = payload.get('nic')
    full_name = payload.get('fullName')
    company_register_number = payload.get('companyRegisterNumber')
    company_name = payload.get('companyName')
    address = payload.get('address') or ''
    district = payload.get('district')
    contact_number = payload.get('contactNumber')
    total_area = payload.get('totalAreaOfPaddyLand')
    
    try:
        conn = get_connection(MYSQL_DATABASE)
        cursor = conn.cursor()
        
        # Build UPDATE query with only non-None fields
        update_fields = []
        update_values = []
        
        if nic is not None:
            update_fields.append('nic = %s')
            update_values.append(nic)
        if full_name is not None:
            update_fields.append('full_name = %s')
            update_values.append(full_name)
        if company_register_number is not None:
            update_fields.append('company_register_number = %s')
            update_values.append(company_register_number)
        if company_name is not None:
            update_fields.append('company_name = %s')
            update_values.append(company_name)
        if address is not None:
            update_fields.append('address = %s')
            update_values.append(address)
        if district is not None:
            update_fields.append('district = %s')
            update_values.append(district)
        if contact_number is not None:
            update_fields.append('contact_number = %s')
            update_values.append(contact_number)
        if total_area is not None:
            update_fields.append('total_area_of_paddy_land = %s')
            update_values.append(total_area)
        
        if not update_fields:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Add user_id to values for WHERE clause
        update_values.append(user_id)
        
        # Execute update
        update_sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(update_sql, tuple(update_values))
        conn.commit()
        
        # Fetch and return updated user
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            user_dict = dict(zip(columns, row))
            cursor.close()
            conn.close()
            return jsonify(user_dict), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404
            
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
