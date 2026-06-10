from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "megaloja.db"

ORDER_STATUS = {
    "aguardando_preparacao",
    "pronto_retirada",
    "retirado",
    "cancelado",
}

DELIVERY_METHODS = {"entrega_padrao", "retirar_na_loja"}
