import os
import time
import io
import base64
from pathlib import Path
import logging
from google import genai
from google.genai import types
from PIL import Image
import cv2
import numpy as np

# Configuração de Logs básicos para o terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CONFIGURAÇÕES GERAIS E API (COTA ATIVA)
# ==============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

BASE_DIR = Path(os.environ.get(
    "TOPO_AGENT_BASE_DIR",
    r"C:\Users\Juan Sales\OneDrive\Desktop\Personalizados\topo\Imagens",
)).expanduser()

INPUT_PATH = BASE_DIR / os.environ.get("TOPO_AGENT_INPUT_NAME", "teste.jpg")
OUTPUT_COLOR_PATH = BASE_DIR / os.environ.get("TOPO_AGENT_COLOR_OUTPUT_NAME", "topo_fiel_pronto.png")
OUTPUT_MASK_PATH = BASE_DIR / os.environ.get("TOPO_AGENT_MASK_OUTPUT_NAME", "topo_mascara_corte.png")
ARCHIVE_DIR = BASE_DIR / "processed"
POLL_SECONDS = int(os.environ.get("TOPO_AGENT_POLL_SECONDS", "5"))
MIN_CONTOUR_AREA = int(os.environ.get("TOPO_AGENT_MIN_CONTOUR_AREA", "150"))

GEMINI_ANALYSIS_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL    = "gemini-2.5-flash" # Atualizado para evitar o bloqueio 429

def carregar_client_gemini():
    if not GEMINI_API_KEY:
        raise RuntimeError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    return genai.Client(api_key=GEMINI_API_KEY)

# Prompts do Agente
PROMPT_ANALISE = """
You are an expert product illustrator specializing in cake topper design.
Analyze the image and identify ONLY the decorative topper elements (figures, letters,
number candles, themed cutouts, banners, stars, crowns, etc.).
IGNORE: the cake tiers, frosting, background, candles without decorative shape, plates and stands.

Return a concise English description structured as:
- Main theme/character(s): ...
- Secondary elements: ...
- Color palette: ...
- Style notes (flat, 3-D, glittery, etc.): ...
"""

def criar_prompt_geracao(descricao_elementos):
    return f"""
    Create a professional printable craft sheet for Silhouette Studio / Cricut cutting machines.
    
    ELEMENTS TO INCLUDE: {descricao_elementos}
    
    STRICT LAYOUT RULES:
    - Pure white background (#FFFFFF), no exceptions
    - Each element must be completely isolated with at least 8 px white border around it
    - Arrange elements in a clean grid, 2-3 columns, evenly spaced
    - No overlapping, no touching borders between elements
    
    ILLUSTRATION STYLE:
    - Flat vector-style illustration, bold outlines (2-3 px black stroke)
    - Bright, saturated solid colors matching the originals
    - No gradients, no drop shadows, no textures, no glow
    - Crisp, clean silhouette edges - essential for die-cutting
    """

# ==============================================================================
# FUNÇÕES AUXILIARES DE TRATAMENTO DE IMAGEM DA API
# ==============================================================================
def _open_image_from_bytes(raw_data):
    if raw_data is None: return None
    if isinstance(raw_data, Image.Image): return raw_data
    if isinstance(raw_data, (bytes, bytearray)):
        try: return Image.open(io.BytesIO(raw_data))
        except Exception: return None
    if isinstance(raw_data, str):
        try:
            decoded = base64.b64decode(raw_data)
            return Image.open(io.BytesIO(decoded))
        except Exception:
            try: return Image.open(io.BytesIO(raw_data.encode("utf-8")))
            except Exception: return None
    if isinstance(raw_data, dict):
        for key in ("image", "inline_data", "data", "content", "bytes", "base64"):
            if key in raw_data:
                img = _open_image_from_bytes(raw_data[key])
                if img is not None: return img
    for attr in ("data", "content", "image", "bytes", "base64"):
        if hasattr(raw_data, attr):
            try:
                img = _open_image_from_bytes(getattr(raw_data, attr))
                if img is not None: return img
            except Exception: pass
    return None

def _extract_image_from_part(part):
    if hasattr(part, "as_image"):
        try:
            img = part.as_image()
            if isinstance(img, Image.Image): return img
        except Exception: pass
    for attr in ("inline_data", "image", "data", "content", "bytes", "base64"):
        raw = getattr(part, attr, None)
        img = _open_image_from_bytes(raw)
        if img is not None: return img
    if isinstance(part, dict): return _open_image_from_bytes(part)
    return None

# ==============================================================================
# 2. MOTOR DO AGENTE (EXECUÇÃO FLUXO COMPLETO)
# ==============================================================================
def rodar_fluxo_agente_completo():
    if not INPUT_PATH.exists():
        return False

    print("\n" + "="*70)
    print("=== AGENTE AUTÔNOMO ATIVADO: PROCESSANDO TOPO DE BOLO ===")
    print("="*70)
    
    print(f"\n[Passo 1] Imagem detectada! Iniciando análise conceitual com Gemini...")
    img_pil = Image.open(INPUT_PATH).convert("RGB")

    try:
        client = carregar_client_gemini()
        response_analise = client.models.generate_content(
            model=GEMINI_ANALYSIS_MODEL,
            contents=[PROMPT_ANALISE, img_pil]
        )
        descricao_elementos = response_analise.text.strip()
        print("[Sucesso] Elementos mapeados com inteligência artificial.")
        print(f"-> Mapeamento:\n{descricao_elementos}\n")
    except Exception as e:
        print(f"[ERRO FASE 1] Falha na análise de imagem: {e}")
        return False

    # Intervalo de segurança para gerenciamento saudável da API
    time.sleep(4)

    # --- FASE 2: GERAÇÃO DA FOLHA COLORIDA ---
    print("[Passo 2] Gemini Flash recriando os elementos em alta fidelidade...")
    prompt_final_imagem = criar_prompt_geracao(descricao_elementos)
    
    try:
        config_interacao = types.GenerateContentConfig(response_modalities=['IMAGE'])
        resultado_imagem = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[prompt_final_imagem, img_pil],
            config=config_interacao
        )
        
        imagem_final = None
        # Varre as partes da resposta buscando pela imagem gerada
        for part in getattr(resultado_imagem, "parts", []):
            img = _extract_image_from_part(part)
            if isinstance(img, Image.Image):
                imagem_final = img.convert("RGB")
                break
                
        # Fallbacks caso venha estruturado em outro campo do payload
        if imagem_final is None:
            for attr in ("image", "output", "output_image", "output_images", "data", "result"):
                img = _open_image_from_bytes(getattr(resultado_imagem, attr, None))
                if isinstance(img, Image.Image):
                    imagem_final = img.convert("RGB")
                    break

        if imagem_final is not None:
            imagem_final.save(OUTPUT_COLOR_PATH)
            print(f"[Sucesso] Folha limpa colorida salva em: {OUTPUT_COLOR_PATH}")
        else:
            print("[ERRO FASE 2] API executou mas nenhuma imagem válida foi extraída do resultado.")
            return False
            
    except Exception as e:
        print(f"[ERRO FASE 2] Falha na geração da nova imagem: {e}")
        return False

    # Pausa estratégica para sincronia de escrita do arquivo em disco
    time.sleep(2)

    # --- FASE 3: DETECÇÃO DE SILHUETA E MÁSCARA AUTOMÁTICA ---
    print("\n[Passo 3] OpenCV assumindo o controle: Extraindo linhas de contorno...")
    try:
        img_recriada = cv2.imread(str(OUTPUT_COLOR_PATH))
        altura, largura, _ = img_recriada.shape
        
        cinza = cv2.cvtColor(img_recriada, cv2.COLOR_BGR2GRAY)
        borrado = cv2.GaussianBlur(cinza, (5, 5), 0)
        # Ajustado para 250 para limpar variações sutis no fundo branco
        _, thresh = cv2.threshold(borrado, 250, 255, cv2.THRESH_BINARY_INV)
        
        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        tela_mascara = np.ones((altura, largura, 3), dtype=np.uint8) * 255
        
        elementos_contados = 0
        for c in contornos:
            if cv2.contourArea(c) < MIN_CONTOUR_AREA:
                continue
            # Desenha preenchendo a silhueta em preto (0, 0, 0)
            cv2.drawContours(tela_mascara, [c], -1, (0, 0, 0), thickness=cv2.FILLED)
            elementos_contados += 1
            
        cv2.imwrite(str(OUTPUT_MASK_PATH), tela_mascara)
        print(f"[Sucesso] Máscara de corte gerada perfeitamente com {elementos_contados} facas.")
        print(f"[Sucesso] Arquivo salvo em: {OUTPUT_MASK_PATH}")
        
        # --- ARQUIVANDO ORIGINAL ---
        ARCHIVE_DIR.mkdir(exist_ok=True, parents=True)
        archive_path = ARCHIVE_DIR / INPUT_PATH.name
        
        # Copia e remove para evitar travas de permissão entre volumes do Windows
        if archive_path.exists():
            archive_path.unlink()
        INPUT_PATH.replace(archive_path)
        print(f"\n[Concluído] Imagem original movida para: {archive_path}")
        return True
        
    except Exception as e:
        print(f"[ERRO FASE 3] Falha no processamento local da silhueta: {e}")
        return False

# ==============================================================================
# 3. LOOP DE AUTOMAÇÃO CONTÍNUA (WATCHDOG)
# ==============================================================================
if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("[ERRO] Variável de ambiente GEMINI_API_KEY não encontrada. Configure-a no Windows antes de rodar.")
    else:
        print("="*70)
        print(" O AGENTE ESTÁ ATIVO E MONITORANDO A SUA PASTA DE IMPRESSÃO ")
        print(f" Entrada: {INPUT_PATH}")
        print(f" Saída colorida: {OUTPUT_COLOR_PATH}")
        print(f" Saída máscara: {OUTPUT_MASK_PATH}")
        print(f" Arquivo processado arquivado em: {ARCHIVE_DIR}")
        print(f" A cada {POLL_SECONDS} segundos a pasta será verificada.")
        print(" Para fechar o agente, pressione CTRL + C no terminal.")
        print("="*70)
        
        while True:
            rodar_fluxo_agente_completo()
            time.sleep(POLL_SECONDS)
