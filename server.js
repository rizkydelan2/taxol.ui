const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const cors = require('cors');

const app = express();
const dbPath = path.join(__dirname, 'taxol.db');

// === Inisialisasi Database ===
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) console.error('Gagal konek ke SQLite:', err);
    else console.log('Terkoneksi ke SQLite database.');
});

// === Buat tabel otomatis kalau belum ada ===
db.run(`
  CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    pickup TEXT,
    destination TEXT,
    service TEXT,
    distance REAL,
    duration TEXT,
    price REAL,
    payment_method TEXT
  )
`);

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// === Endpoint tambah data ===
app.post('/api/trips', (req, res) => {
    const { customerName, pickup, destination, service, distance, duration, price, paymentMethod } = req.body;
    db.run(
        `INSERT INTO trips (customer_name, pickup, destination, service, distance, duration, price, payment_method)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [customerName, pickup, destination, service, distance, duration, price, paymentMethod],
        function (err) {
            if (err) return res.status(500).json({ error: err.message });
            res.json({ id: this.lastID });
        }
    );
});

// === Endpoint ambil semua data ===
app.get('/api/trips', (req, res) => {
    db.all('SELECT * FROM trips ORDER BY id DESC', (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

app.listen(3000, () => console.log('Server berjalan di http://localhost:3000'));