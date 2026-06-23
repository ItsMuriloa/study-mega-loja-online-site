from datetime import datetime
import secrets

try:
    from .config import DELIVERY_METHODS, ORDER_STATUS
    from .database import connect_db, row_to_dict
except ImportError:
    from config import DELIVERY_METHODS, ORDER_STATUS
    from database import connect_db, row_to_dict


class ApiError(Exception):
    # Erro de negocio com codigo HTTP. Exemplo: 400 para dado invalido.
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def generate_pickup_code():
    # Codigo entregue ao cliente para confirmar a retirada no balcao.
    return f"HV-{secrets.randbelow(9000) + 1000}-{secrets.randbelow(9000) + 1000}"


def create_notification(conn, order_id, message):
    conn.execute(
        "INSERT INTO notifications (order_id, message, created_at) VALUES (?, ?, ?)",
        (order_id, message, now_iso()),
    )


def get_order(conn, order_id):
    # Une pedido, produto e loja para devolver uma visao completa ao frontend.
    return conn.execute(
        """
        SELECT
            o.id,
            o.customer_name,
            o.delivery_method,
            o.quantity,
            o.status,
            o.pickup_code,
            o.created_at,
            o.updated_at,
            p.id AS product_id,
            p.name AS product_name,
            p.price AS product_price,
            s.id AS store_id,
            s.name AS store_name,
            s.address AS store_address,
            s.city AS store_city
        FROM orders o
        JOIN products p ON p.id = o.product_id
        LEFT JOIN stores s ON s.id = o.store_id
        WHERE o.id = ?
        """,
        (order_id,),
    ).fetchone()


def list_stores(city=None, product_id=None):
    # Lista lojas ativas. Com product_id, inclui tambem o estoque em cada loja.
    sql = """
        SELECT s.id, s.name, s.city, s.zip_code, s.address, s.capacity, s.active
        FROM stores s
        WHERE s.active = 1
    """
    params = []

    if city:
        sql += " AND lower(s.city) LIKE lower(?)"
        params.append(f"%{city}%")

    if product_id:
        sql = """
            SELECT
                s.id, s.name, s.city, s.zip_code, s.address, s.capacity, s.active,
                COALESCE(i.quantity, 0) AS stock
            FROM stores s
            LEFT JOIN inventory i ON i.store_id = s.id AND i.product_id = ?
            WHERE s.active = 1
        """
        params = [product_id]
        if city:
            sql += " AND lower(s.city) LIKE lower(?)"
            params.append(f"%{city}%")

    with connect_db() as conn:
        rows = conn.execute(sql + " ORDER BY s.city, s.name", params).fetchall()
        return [row_to_dict(row) for row in rows]


def list_products(store_id=None):
    # Lista produtos. Com store_id, mostra o estoque local daquela unidade.
    if store_id:
        sql = """
            SELECT p.id, p.name, p.category, p.price, COALESCE(i.quantity, 0) AS stock
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.id AND i.store_id = ?
            ORDER BY p.name
        """
        params = [store_id]
    else:
        sql = "SELECT id, name, category, price FROM products ORDER BY name"
        params = []

    with connect_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [row_to_dict(row) for row in rows]


def list_orders():
    with connect_db() as conn:
        rows = conn.execute(
            """
            SELECT id, customer_name, delivery_method, store_id, product_id, quantity,
                   status, pickup_code, created_at, updated_at
            FROM orders
            ORDER BY id DESC
            """
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def find_order(order_id):
    with connect_db() as conn:
        order = get_order(conn, order_id)
        if not order:
            raise ApiError(404, "Pedido nao encontrado.")
        return row_to_dict(order)


def list_notifications(order_id):
    with connect_db() as conn:
        order = get_order(conn, order_id)
        if not order:
            raise ApiError(404, "Pedido nao encontrado.")

        rows = conn.execute(
            """
            SELECT id, order_id, message, created_at
            FROM notifications
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def create_order(payload):
    # Regras principais do checkout: validar dados, conferir estoque,
    # criar pedido, baixar estoque e registrar a primeira notificacao.
    customer_name = str(payload.get("customer_name", "Cliente MegaLoja")).strip()
    delivery_method = payload.get("delivery_method")
    store_id = payload.get("store_id")
    product_id = payload.get("product_id")
    quantity = int(payload.get("quantity", 1))

    if not customer_name:
        raise ApiError(400, "Informe o nome do cliente.")
    if delivery_method not in DELIVERY_METHODS:
        raise ApiError(400, "delivery_method deve ser 'entrega_padrao' ou 'retirar_na_loja'.")
    if not product_id:
        raise ApiError(400, "Informe product_id.")
    if quantity < 1:
        raise ApiError(400, "quantity deve ser maior que zero.")
    if delivery_method == "retirar_na_loja" and not store_id:
        raise ApiError(400, "store_id e obrigatorio para retirada na loja.")

    with connect_db() as conn:
        product = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise ApiError(404, "Produto nao encontrado.")

        if delivery_method == "retirar_na_loja":
            # Click & Collect exige loja ativa e estoque suficiente antes de criar o pedido.
            store = conn.execute("SELECT id FROM stores WHERE id = ? AND active = 1", (store_id,)).fetchone()
            if not store:
                raise ApiError(404, "Loja nao encontrada.")

            stock = conn.execute(
                "SELECT quantity FROM inventory WHERE store_id = ? AND product_id = ?",
                (store_id, product_id),
            ).fetchone()
            available = stock["quantity"] if stock else 0
            if available < quantity:
                raise ApiError(409, "Estoque insuficiente na loja selecionada.")

        pickup_code = generate_pickup_code() if delivery_method == "retirar_na_loja" else None
        timestamp = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO orders (
                customer_name, delivery_method, store_id, product_id, quantity,
                status, pickup_code, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_name,
                delivery_method,
                store_id,
                product_id,
                quantity,
                "aguardando_preparacao",
                pickup_code,
                timestamp,
                timestamp,
            ),
        )
        order_id = cursor.lastrowid

        if delivery_method == "retirar_na_loja":
            # A baixa de estoque acontece no momento em que o pedido e confirmado.
            conn.execute(
                """
                UPDATE inventory
                SET quantity = quantity - ?
                WHERE store_id = ? AND product_id = ?
                """,
                (quantity, store_id, product_id),
            )
            create_notification(
                conn,
                order_id,
                "Pedido recebido. A loja iniciou a separacao para retirada.",
            )
        else:
            create_notification(conn, order_id, "Pedido recebido para entrega padrao.")

        return row_to_dict(get_order(conn, order_id))


def update_order_status(order_id, payload):
    # Simula o fluxo operacional da loja: preparar, liberar retirada,
    # confirmar retirada ou cancelar o pedido.
    new_status = payload.get("status")
    pickup_code = payload.get("pickup_code")

    if new_status not in ORDER_STATUS:
        raise ApiError(400, "Status invalido.")

    with connect_db() as conn:
        order = get_order(conn, order_id)
        if not order:
            raise ApiError(404, "Pedido nao encontrado.")

        current_status = order["status"]
        if current_status in {"retirado", "cancelado"}:
            raise ApiError(409, "Pedido ja esta encerrado.")

        if new_status == "retirado" and order["delivery_method"] == "retirar_na_loja":
            # A retirada so e concluida se o codigo informado bater com o codigo do pedido.
            if pickup_code != order["pickup_code"]:
                raise ApiError(403, "Codigo de retirada invalido.")

        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, now_iso(), order_id),
        )

        messages = {
            "aguardando_preparacao": "Pedido voltou para aguardando preparacao.",
            "pronto_retirada": "Pedido pronto para retirada. Codigo liberado ao cliente.",
            "retirado": "Pedido retirado no balcao com sucesso.",
            "cancelado": "Pedido cancelado. Estoque deve ser revisado pela loja.",
        }
        create_notification(conn, order_id, messages[new_status])
        return row_to_dict(get_order(conn, order_id))
