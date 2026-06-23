import sqlite3

try:
    from .config import DB_PATH
except ImportError:
    from config import DB_PATH


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    # row_factory permite acessar colunas pelo nome, por exemplo row["name"].
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row):
    return dict(row) if row else None


def init_db():
    with connect_db() as conn:
        # O schema representa o fluxo principal: lojas, produtos, estoque,
        # pedidos e notificacoes geradas durante a retirada.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                zip_code TEXT NOT NULL,
                address TEXT NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 20,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                store_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (store_id, product_id),
                FOREIGN KEY (store_id) REFERENCES stores(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                delivery_method TEXT NOT NULL,
                store_id INTEGER,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL,
                pickup_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (store_id) REFERENCES stores(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
            """
        )
        seed_stores(conn)
        seed_products(conn)
        seed_inventory(conn)


def seed_stores(conn):
    store_count = conn.execute("SELECT COUNT(*) AS total FROM stores").fetchone()["total"]
    if store_count > 0:
        return

    # Dados iniciais para demonstrar a escolha de loja fisica.
    conn.executemany(
        """
        INSERT INTO stores (id, name, city, zip_code, address, capacity)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "Havan Canoas Centro", "Canoas", "92010-000", "Av. Guilherme Schell, 5000", 35),
            (2, "Havan Canoas Shopping", "Canoas", "92020-000", "Av. dos Estados, 450", 25),
            (3, "Havan Sao Leopoldo Bourbon", "Sao Leopoldo", "93010-000", "Av. Primeiro de Marco, 900", 20),
        ],
    )


def seed_products(conn):
    product_count = conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
    if product_count > 0:
        return

    # Catalogo minimo usado pelo frontend do MVP.
    conn.executemany(
        "INSERT INTO products (id, name, category, price) VALUES (?, ?, ?, ?)",
        [
            (201, 'Smart TV 4K Crystal UHD 55" Wi-Fi Bluetooth HDR', "eletronicos", 2549.00),
            (202, "Smartphone Android 5G Pro 256GB Camera Tripla", "eletronicos", 1799.00),
            (203, "Furadeira de Impacto Profissional Mandril 1/2 Reversivel", "casa", 389.90),
            (204, "Maleta de Ferramentas Completa Aco Cromo 142 Pecas", "casa", 249.00),
            (205, "Geladeira Frost Free Duplex 410L Inox Digital", "eletrodomesticos", 3899.00),
            (206, "Sofa Retratil Tecido Suede", "eletrodomesticos", 1450.00),
        ],
    )


def seed_inventory(conn):
    inventory_count = conn.execute("SELECT COUNT(*) AS total FROM inventory").fetchone()["total"]
    if inventory_count > 0:
        return

    # Cada tupla liga loja, produto e quantidade disponivel naquela unidade.
    inventory = [
        (1, 201, 5), (2, 201, 0), (3, 201, 4),
        (1, 202, 12), (2, 202, 8), (3, 202, 0),
        (1, 203, 25), (2, 203, 14), (3, 203, 35),
        (1, 204, 0), (2, 204, 6), (3, 204, 15),
        (1, 205, 3), (2, 205, 0), (3, 205, 2),
        (1, 206, 4), (2, 206, 3), (3, 206, 0),
    ]
    conn.executemany(
        "INSERT INTO inventory (store_id, product_id, quantity) VALUES (?, ?, ?)",
        inventory,
    )
