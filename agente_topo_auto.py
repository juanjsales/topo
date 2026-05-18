import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image
import cv2
import numpy as np

# ==============================================================================
# 1. CONFIGURAÇÕES GERAIS E API (COTA ATIVA)
# ==============================================================================
# Pegando a chave de API das variáveis de ambiente por segurança
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


def carregar_client_gemini():
    if not GEMINI_API_KEY:
        raise RuntimeError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    return genai.Client(api_key=GEMINI_API_KEY)

# Prompts do Agente
PROMPT_ANALISE = """
Você é um agente especialista em design de personalizados para scrapfesta.
Analise cuidadosamente esta imagem de bolo ou print de rede social.
Identifique APENAS os elementos que compõem o topo do bolo (os apliques de papel).

Gere uma descrição consolidada em INGLÊS de todos esses elementos reunidos, focando em um estilo limpo, infantil e fofo. 
Não descreva o bolo, fundos ou doces da estrutura.
"""

def criar_prompt_geracao(descricao_elementos):
    return f"""
    A printable sheet for cake toppers, scrapfesta, silhouette cutting. 
    The sheet contains exactly these elements: {descricao_elementos}. 
    Please RECREATE these elements with high fidelity, replicating the style, colors, and design of the provided reference image.
    All elements must be arranged completely separate from each other on a clean, solid, pure white background. 
    High definition, cute children illustration style, vector look, bright colors, defined edges, no shadows, no gradients, isolated components perfect for die-cut and print-and-cut.
    """

# ==============================================================================
# 2. MOTOR DO AGENTE (EXECUÇÃO FLUXO COMPLETO)
# ==============================================================================
def rodar_fluxo_agente_completo():
    print("\n" + "="*70)
    print("=== AGENTE AUTÔNOMO ACTIVADO: PROCESSANDO TOPO DE BOLO ===")
    print("="*70)
    
    if not INPUT_PATH.exists():
        print(f"[Aguardando] Nenhuma imagem encontrada para processar em: {INPUT_PATH}")
        return False

    print(f"\n[Passo 1] Imagem detectada! Iniciando análise conceitual com Gemini...")
    img_pil = Image.open(INPUT_PATH)

    try:
        client = carregar_client_gemini()
        response_analise = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[PROMPT_ANALISE, img_pil]
        )
        descricao_elementos = response_analise.text.strip()
        print("[Sucesso] Elementos mapeados com inteligência artificial.")
    except Exception as e:
        print(f"[ERRO FASE 1] Falha na análise de imagem: {e}")
        return False

    # Intervalo de segurança para gerenciamento saudável dos seus tokens
    time.sleep(4)

    # --- FASE 2: GERAÇÃO DA FOLHA COLORIDA ---
    print("\n[Passo 2] Gemini Flash Image recriando os elementos em alta fidelidade...")
    prompt_final_imagem = criar_prompt_geracao(descricao_elementos)
    
    try:
        config_interacao = types.GenerateContentConfig(response_modalities=['IMAGE'])
        resultado_imagem = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt_final_imagem, img_pil],
            config=config_interacao
        )
        
        imagem_salva = False
        for part in resultado_imagem.parts:
            if part.inline_data is not None or hasattr(part, 'as_image'):
                imagem_final = part.as_image()
                imagem_final.save(OUTPUT_COLOR_PATH)
                print(f"[Sucesso] Folha limpa colorida salva em: {OUTPUT_COLOR_PATH}")
                imagem_salva = True
                break
                
        if not imagem_salva:
            print("[ERRO FASE 2] API executou mas não retornou a mídia estruturada.")
            return False
            
    except Exception as e:
        print(f"[ERRO FASE 2] Falha na geração da nova imagem: {e}")
        return False

    # Pequena pausa para garantir a gravação do arquivo em disco antes do OpenCV ler
    time.sleep(2)

    # --- FASE 3: DETECÇÃO DE SILHUETA E MÁSCARA AUTOMÁTICA ---
    print("\n[Passo 3] OpenCV assumindo o controle: Extraindo linhas de contorno...")
    try:
        img_recriada = cv2.imread(str(OUTPUT_COLOR_PATH))
        altura, largura, _ = img_recriada.shape
        
        cinza = cv2.cvtColor(img_recriada, cv2.COLOR_BGR2GRAY)
        borrado = cv2.GaussianBlur(cinza, (3, 3), 0)
        _, thresh = cv2.threshold(borrado, 245, 255, cv2.THRESH_BINARY_INV)
        
        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        tela_mascara = np.ones((altura, largura, 3), dtype=np.uint8) * 255
        
        elementos_contados = 0
        for c in contornos:
            if cv2.contourArea(c) < 150:
                continue
            cv2.drawContours(tela_mascara, [c], -1, (0, 0, 0), thickness=cv2.FILLED)
            elementos_contados += 1
            
        cv2.imwrite(str(OUTPUT_MASK_PATH), tela_mascara)
        print(f"[Sucesso] Máscara de corte gerada perfeitamente com {elementos_contados} facas.")
        print(f"[Sucesso] Arquivo salvo em: {OUTPUT_MASK_PATH}")
        
        # --- ARQUIVO ORIGINAL ---
        ARCHIVE_DIR.mkdir(exist_ok=True, parents=True)
        archive_path = ARCHIVE_DIR / INPUT_PATH.name
        INPUT_PATH.replace(archive_path)
        print(f"\n[Concluído] Imagem original movida para o arquivo de processados: {archive_path}")
        return True
        
    except Exception as e:
        print(f"[ERRO FASE 3] Falha no processamento local da silhueta: {e}")
        return False

# ==============================================================================
# 3. LOOP DE AUTOMAÇÃO CONTÍNUA (WATCHDOG)
# ==============================================================================
if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("[ERRO] Variável de ambiente GEMINI_API_KEY não encontrada. Configure-a no seu Windows antes de rodar.")
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
            # O script fica vigiando a pasta a cada POLL_SECONDS
            rodar_fluxo_agente_completo()
            time.sleep(POLL_SECONDS)
