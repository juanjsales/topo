# Topo Backend API

Este diretório contém o backend FastAPI para o app móvel.

## Como usar

1. Crie um arquivo `.env` a partir do exemplo:
   ```bash
   cp backend_api/.env.example backend_api/.env
   # ou no Windows PowerShell:
   # Copy-Item backend_api\.env.example backend_api\.env
   ```
2. Defina sua chave Gemini em `backend_api/.env`:
   ```text
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
3. Instale dependências:
   ```bash
   pip install -r backend_api/requirements.txt
   ```
4. Execute o servidor:
   ```bash
   uvicorn backend_api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Rotas

- `GET /health` — verifica se o servidor está no ar.
- `POST /process` — envia uma imagem e processa com Gemini para gerar a folha colorida e a máscara.

## Observações

- O backend aceita `PNG`, `JPG`, `JPEG` e `WEBP`.
- A chave Gemini pode ser passada via `api_key` no formulário ou usando `GEMINI_API_KEY` no servidor.
- Para executar via Docker, utilize o arquivo `docker-compose.topo.yaml` no diretório raiz:
  ```bash
  docker compose -f docker-compose.topo.yaml up --build
  ```
