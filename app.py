from flask import Flask, request, jsonify, send_from_directory, g
import sqlite3, os, hashlib

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'taxol.db')


# ======================
# 🔧 INISIALISASI DATABASE
# ======================
def init_db(force_recreate=False):
    if force_recreate and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        vehicle_type TEXT,
        plate_number TEXT,
        address TEXT,
        status TEXT DEFAULT 'aktif'
    );

    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        pickup TEXT,
        destination TEXT,
        service TEXT,
        distance REAL,
        duration TEXT,
        price REAL,
        payment_method TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    );
    """)

    # Admin default
    cur.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", (
        "admin",
        hashlib.sha256("admin123".encode()).hexdigest()
    ))

    conn.commit()
    conn.close()


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


# ======================
# 👤 REGISTER DRIVER
# ======================
@app.route('/register', methods=['POST'])
def register_driver():
    data = request.get_json() or {}
    required = ["full_name", "email", "phone", "vehicle_type", "plate_number", "address"]

    if not all(data.get(f) for f in required):
        return jsonify({"error": "Mohon lengkapi semua data"}), 400

    db = get_db()

    # Password otomatis = hash nomor HP
    password_hash = hashlib.sha256(data["phone"].encode()).hexdigest()

    try:
        db.execute("""
            INSERT INTO drivers (full_name, email, phone, password, vehicle_type, plate_number, address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["full_name"], data["email"], data["phone"], password_hash,
            data["vehicle_type"], data["plate_number"], data["address"]
        ))
        db.commit()
        return jsonify({"message": "✅ Pendaftaran driver berhasil! Gunakan nomor HP sebagai password."})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Nomor telepon sudah terdaftar"}), 400


@app.route('/api/drivers', methods=['GET'])
def get_drivers():
    db = get_db()
    rows = db.execute("""
        SELECT id, full_name, email, phone, vehicle_type, plate_number, address, status
        FROM drivers
        ORDER BY id DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])



# ======================
# 🔑 LOGIN DRIVER
# ======================
@app.route('/login_driver', methods=['POST'])
def login_driver():
    data = request.get_json() or {}
    phone, password = data.get("phone"), data.get("password")

    if not phone or not password:
        return jsonify({"error": "Nomor telepon dan password wajib diisi"}), 400

    hash_pw = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    user = db.execute(
        "SELECT * FROM drivers WHERE phone = ? AND password = ?", (phone, hash_pw)
    ).fetchone()

    if not user:
        return jsonify({"error": "Nomor telepon atau password salah"}), 401

    return jsonify({"message": "Login berhasil", "driver": dict(user)})



# ======================
# 🧾 TRIPS (RIWAYAT ORDER)
# ======================
@app.route('/api/trips', methods=['GET'])
def get_trips():
    db = get_db()
    rows = db.execute("SELECT * FROM trips ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/trips', methods=['POST'])
def create_trip():
    data = request.get_json() or {}
    fields = ['customerName', 'pickup', 'destination', 'service',
              'distance', 'duration', 'price', 'paymentMethod']
    values = [data.get(f) for f in fields]

    if not all(values[:3]):
        return jsonify({'error': 'Data tidak lengkap'}), 400

    db = get_db()
    db.execute("""
        INSERT INTO trips (customer_name, pickup, destination, service, distance, duration, price, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, tuple(values))
    db.commit()
    return jsonify({'status': 'ok'})


# ======================
# 🛡️ ADMIN PANEL (API)
# ======================
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    username, password = data.get("username"), data.get("password")

    if not username or not password:
        return jsonify({"error": "Isi username dan password"}), 400

    db = get_db()
    row = db.execute(
        "SELECT * FROM admin WHERE username = ? AND password = ?",
        (username, hashlib.sha256(password.encode()).hexdigest())
    ).fetchone()

    if not row:
        return jsonify({"error": "Login admin gagal"}), 401

    return jsonify({"message": "Login admin berhasil"})


@app.route('/admin/drivers', methods=['GET'])
def admin_drivers():
    db = get_db()
    rows = db.execute("SELECT * FROM drivers ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/admin/trips', methods=['GET'])
def admin_trips():
    db = get_db()
    rows = db.execute("SELECT * FROM trips ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


# ======================
# 🌐 FRONTEND
# ======================
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    for folder in ['public', '.', 'dist', 'build']:
        root = os.path.join(os.path.dirname(__file__), folder)
        full = os.path.join(root, path)
        if os.path.exists(full):
            file_to_serve = path if os.path.isfile(full) else 'index.html'
            try:
                return send_from_directory(root, file_to_serve)
            except Exception:
                pass
    return jsonify({'message': 'API TAXOL aktif'})


# ======================
# 🚀 RUN APP
# ======================
if __name__ == '__main__':
    init_db()
    print("✅ Server TAXOL aktif di http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
