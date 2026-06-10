from http.server import ThreadingHTTPServer

try:
    from .api import ApiHandler
    from .database import init_db
except ImportError:
    from api import ApiHandler
    from database import init_db


def run(host="127.0.0.1", port=5000):
    init_db()
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"MegaLoja API rodando em http://{host}:{port}")
    print("Pressione Ctrl+C para encerrar.")
    server.serve_forever()


if __name__ == "__main__":
    run()
