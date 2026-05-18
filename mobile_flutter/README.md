# Topo Mobile Flutter

Este diretório contém o esqueleto inicial do app Flutter para consumir a API do backend Python.

## Passos rápidos

1. Instale o Flutter: https://flutter.dev/docs/get-started/install
2. Crie o projeto básico (se ainda não existir):
   ```bash
   cd topo
   flutter create mobile_flutter
   ```
3. Substitua `mobile_flutter/lib/main.dart` e `mobile_flutter/pubspec.yaml` pelos arquivos daqui.
4. Ajuste `backendUrl` em `lib/api_service.dart` para o endereço do servidor FastAPI.
5. Execute:
   ```bash
   cd mobile_flutter
   flutter pub get
   flutter run
   ```

## O que o app faz

- permite selecionar uma imagem da galeria
- envia a imagem e a API Key para o backend
- recebe descrição, imagem gerada e máscara
- mostra os resultados no dispositivo

## Observações

- Em emuladores Android, use `10.0.2.2` para acessar o servidor local.
- Para produção, altere `backendUrl` para o endereço público do seu backend.
