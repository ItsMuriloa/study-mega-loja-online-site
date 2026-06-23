from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "megaloja.db"

# Estados permitidos no ciclo de vida de um pedido Click & Collect.
ORDER_STATUS = {
    "aguardando_preparacao",
    "pronto_retirada",
    "retirado",
    "cancelado",
}

# Modalidades aceitas pelo checkout do MVP.
DELIVERY_METHODS = {"entrega_padrao", "retirar_na_loja"}
