from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import sqlite3

try:
    from .config import DB_PATH
    from .services import (
        ApiError,
        create_order,
        find_order,
        list_notifications,
        list_orders,
        list_products,
        list_stores,
        update_order_status,
    )
except ImportError:
    from config import DB_PATH
    from services import (
        ApiError,
        create_order,
        find_order,
        list_notifications,
        list_orders,
        list_products,
        list_stores,
        update_order_status,
    )


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "MegaLojaAPI/1.0"

    def do_OPTIONS(self):
        # Atende a verificacao CORS feita pelo navegador antes de alguns requests.
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Centraliza as consultas da API: saude, lojas, produtos, pedidos e notificacoes.
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            if path == "/":
                self.show_api_index()
            elif path == "/api/health":
                self.respond_json({"status": "online", "database": str(DB_PATH.name)})
            elif path == "/api/stores":
                self.respond_json(
                    {
                        "stores": list_stores(
                            city=query.get("city", [None])[0],
                            product_id=query.get("product_id", [None])[0],
                        )
                    }
                )
            elif path == "/api/products":
                self.respond_json({"products": list_products(query.get("store_id", [None])[0])})
            elif path == "/api/orders":
                self.respond_json({"orders": list_orders()})
            elif path.startswith("/api/orders/") and path.endswith("/notifications"):
                order_id = self.extract_id(path, "/api/orders/", "/notifications")
                self.respond_json({"notifications": list_notifications(order_id)})
            elif path.startswith("/api/orders/"):
                order_id = self.extract_id(path, "/api/orders/")
                self.respond_json({"order": find_order(order_id)})
            else:
                self.respond_error(404, "Rota nao encontrada.")
        except ApiError as exc:
            self.respond_error(exc.status, exc.message)
        except ValueError as exc:
            self.respond_error(400, str(exc))
        except sqlite3.Error as exc:
            self.respond_error(500, f"Erro no banco de dados: {exc}")

    def do_POST(self):
        # No MVP, o POST principal cria um pedido a partir do checkout.
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/api/orders":
                self.respond_json({"order": create_order(self.read_json())}, status=201)
            else:
                self.respond_error(404, "Rota nao encontrada.")
        except ApiError as exc:
            self.respond_error(exc.status, exc.message)
        except ValueError as exc:
            self.respond_error(400, str(exc))
        except sqlite3.Error as exc:
            self.respond_error(500, f"Erro no banco de dados: {exc}")

    def do_PATCH(self):
        # Atualiza o status do pedido, simulando a acao do funcionario da loja.
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path.startswith("/api/orders/") and path.endswith("/status"):
                order_id = self.extract_id(path, "/api/orders/", "/status")
                self.respond_json({"order": update_order_status(order_id, self.read_json())})
            else:
                self.respond_error(404, "Rota nao encontrada.")
        except ApiError as exc:
            self.respond_error(exc.status, exc.message)
        except ValueError as exc:
            self.respond_error(400, str(exc))
        except sqlite3.Error as exc:
            self.respond_error(500, f"Erro no banco de dados: {exc}")

    def show_api_index(self):
        self.respond_json(
            {
                "name": "MegaLoja Click & Collect API",
                "status": "online",
                "message": "Use uma das rotas abaixo para testar o backend.",
                "routes": {
                    "health": "GET /api/health",
                    "stores": "GET /api/stores",
                    "stores_with_stock": "GET /api/stores?product_id=201",
                    "products": "GET /api/products",
                    "products_by_store": "GET /api/products?store_id=1",
                    "orders": "GET /api/orders",
                    "create_order": "POST /api/orders",
                    "update_order_status": "PATCH /api/orders/{id}/status",
                    "order_notifications": "GET /api/orders/{id}/notifications",
                },
            }
        )

    def extract_id(self, path, prefix, suffix=""):
        # Extrai o ID numerico de URLs como /api/orders/1/status.
        value = path.removeprefix(prefix)
        if suffix:
            value = value.removesuffix(suffix)
        if not value.isdigit():
            raise ValueError("ID invalido na URL.")
        return int(value)

    def read_json(self):
        # Converte o corpo da requisicao HTTP em dicionario Python.
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("JSON invalido.") from exc

    def respond_json(self, data, status=200):
        # Padroniza todas as respostas da API em JSON com suporte a CORS.
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_error(self, status, message):
        self.respond_json({"error": message}, status=status)

    def send_cors_headers(self):
        # Permite que o frontend em HTML acesse a API mesmo estando em outra porta.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {format % args}")
