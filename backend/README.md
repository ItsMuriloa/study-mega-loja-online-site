# Backend do MVP - MegaLoja Click & Collect

Backend em Python para atender aos requisitos principais do fluxo Click & Collect:

- RF01: selecao da modalidade de entrega;
- RF02: escolha da loja fisica;
- RF03: geracao de codigo de retirada;
- RF04: notificacao de status do pedido.

## Tecnologias

- Python 3;
- servidor HTTP nativo do Python;
- SQLite como banco de dados local;
- API REST com respostas em JSON.

O backend nao depende de bibliotecas externas. O banco `megaloja.db` e criado automaticamente na primeira execucao.

## Estrutura dos arquivos

```text
backend/
  app.py        # ponto de entrada da aplicacao
  api.py        # rotas HTTP e respostas JSON
  services.py   # regras de negocio do Click & Collect
  database.py   # conexao SQLite, criacao de tabelas e dados iniciais
  config.py     # constantes do projeto
```

## Como executar

Na raiz do projeto:

```bash
python backend/app.py
```

A API ficara disponivel em:

```text
http://127.0.0.1:5000
```

Ao abrir esse endereco no navegador, a API mostra uma lista das rotas disponiveis.

## Modelo de dados

O banco possui as tabelas principais:

- `stores`: lojas fisicas disponiveis para retirada;
- `products`: produtos exibidos no MVP;
- `inventory`: estoque de cada produto por loja;
- `orders`: pedidos criados pelo cliente;
- `notifications`: historico de notificacoes de cada pedido.

## Endpoints principais

```http
GET /api/health
```

Verifica se a API esta online.

```http
GET /api/stores
GET /api/stores?city=Canoas
GET /api/stores?product_id=201
```

Lista lojas fisicas. Quando `product_id` e informado, a resposta inclui o estoque daquele produto em cada loja.

```http
GET /api/products
GET /api/products?store_id=1
```

Lista produtos. Quando `store_id` e informado, a resposta inclui o estoque local.

```http
POST /api/orders
```

Cria um pedido. Exemplo para Click & Collect:

```json
{
  "customer_name": "Cliente MegaLoja",
  "delivery_method": "retirar_na_loja",
  "store_id": 1,
  "product_id": 201,
  "quantity": 1
}
```

O backend valida a loja, verifica estoque, registra o pedido, baixa o estoque e gera um `pickup_code`.

```http
PATCH /api/orders/1/status
```

Atualiza o status do pedido. Exemplo:

```json
{
  "status": "pronto_retirada"
}
```

Status aceitos:

- `aguardando_preparacao`;
- `pronto_retirada`;
- `retirado`;
- `cancelado`.

Para marcar como retirado, envie tambem o codigo de retirada:

```json
{
  "status": "retirado",
  "pickup_code": "HV-1234-5678"
}
```

```http
GET /api/orders
GET /api/orders/1
GET /api/orders/1/notifications
```

Consulta pedidos e notificacoes geradas durante o fluxo.

## Fluxo validado no MVP

1. Cliente seleciona a modalidade `retirar_na_loja`.
2. Sistema lista lojas disponiveis e estoque por unidade.
3. Cliente escolhe a loja e cria o pedido.
4. Backend registra o pedido como `aguardando_preparacao`.
5. Backend gera um codigo de retirada.
6. Funcionario altera o status para `pronto_retirada`.
7. Cliente recebe a notificacao e pode retirar o pedido usando o codigo.
