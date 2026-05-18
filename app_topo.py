import streamlit as st
import os
import time
import io
import cv2
import numpy as np
from PIL import Image
from google import genai
from google.genai import types

import streamlit as st

def aplicar_css_personalizado():
    st.markdown("""
    <style>
        /* Oculta o menu hambúrguer, o header e o footer do Streamlit */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* Estilização moderna para botões primários */
        .stButton > button {
            background-color: #2563EB; /* Azul moderno */
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.3s ease-in-out;
            width: 100%;
        }
        
        /* Efeito de hover e clique nos botões */
        .stButton > button:hover {
            background-color: #1D4ED8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            transform: translateY(-2px);
            color: white;
        }
        
        .stButton > button:active {
            transform: translateY(0px);
        }

        /* Suaviza as bordas dos campos de input e upload */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 1px solid #E5E7EB;
        }
        
        .stFileUploader {
            border-radius: 12px;
            border: 2px dashed #93C5FD !important;
            background-color: #F8FAFC;
        }

        /* Ajusta o padding superior que o Streamlit deixa muito grande */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        
        /* Títulos com fonte mais elegante */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            color: #1E293B;
        }
    </style>
    """, unsafe_allow_html=True)

# Aplica as configurações globais da página ANTES de qualquer outro elemento
st.set_page_config(
    page_title="Separador Topo", 
    page_icon="🏔️", 
    layout="wide", # Usa todo o espaço horizontal da tela
    initial_sidebar_state="expanded"
)

# Chama a função de CSS
aplicar_css_personalizado()

# Seu código continua aqui...
st.title("🏔️ Separador Topo")


@st.cache_data(show_spinner="Processando imagem com OpenCV...")
def processar_imagem(imagem_bytes):
    # Seu código cv2 aqui...
    return imagem_processada

@st.cache_data(show_spinner="Consultando o Gemini...")
def consultar_gemini(prompt):
    # Seu código genai aqui...
    return resposta


if st.button("Analisar Dados"):
    with st.spinner('Analisando topografia usando IA... Por favor aguarde.'):
        # código longo aqui...
        resultado = consultar_gemini("Analise os dados...")
    
    st.toast('Análise concluída com sucesso!', icon='🎉')
    st.success("Tudo pronto!")
# Controles na barra lateral
with st.sidebar:
    st.header("⚙️ Configurações")
    fator_suavizacao = st.slider("Fator de Suavização (OpenCV)", 1, 10, 5)
    
# Área avançada oculta na tela principal
with st.expander("Ver dados brutos (Debug)"):
    st.write("Dados extraídos:")
    st.json({"status": "ok", "pontos": 154})
if "processamento_concluido" not in st.session_state:
    st.session_state.processamento_concluido = False

# Se o botão for clicado, salvamos o estado
if st.button("Processar"):
    st.session_state.processamento_concluido = True

# Só exibe os botões de download se o estado for True
if st.session_state.processamento_concluido:
    st.download_button("Baixar Resultados", "dados...", "resultado.txt")


# Configuração da página do aplicativo (Tema Dark e Amigável)
st.set_page_config(page_title="Personalizados da Rô - Estúdio IA", page_icon="✂️", layout="wide")

# ==============================================================================
# LÓGICA DO MOTOR DO AGENTE (PROMPTS ENGENHARIA DE IA)
# ==============================================================================
PROMPT_ANALISE = """
[SYSTEM DIRECTIVE: SEMANTIC SEGMENTATION & ATTENTION ISOLATION]
You operate as an advanced vision-language parser specializing in vector graphics and papercraft die-cut engineering.

[INPUT MATRIX EVALUATION]
The input image may contain UI metadata, mobile screenshot elements (status bars, navigation docks, buttons, likes, comments, frames, dark-mode borders), and background noise (tablecloths, room backgrounds, cake structures, frosting, confectionery).

[EXCLUSION FILTER - MANDATORY]
- DROP_ALL: UI_elements, text_overlays_from_social_media, timestamp_metadata, borders.
- IGNORE: cake_body, cake_stands, candles, background_scenery.

[ATTENTION WEIGHTS]
- Focus: 1.0 -> [cake_topper_appliques, papercraft_elements, individual_character_cutouts, name_banners, age_tags].
- Style Extraction: Identify geometry, exact HEX-color palette, stroke widths, inner paths, illustration archetype (flat vector, cute chibi, rounded children illustration).

[OUTPUT SPECIFICATION]
Generate a highly descriptive, structural visual prompt in English. Describe ONLY the isolated papercraft elements found.
"""

def criar_prompt_geracao(descricao_elementos):
    return f"""
    [TASK: IMAGE-TO-IMAGE HIGH-FIDELITY SYNTHESIS]
    [REFERENCE_IMAGE_INFLUENCE: STYLE=1.0, COLOR_PALETTE=1.0, TEXT_CONTENT=1.0, LAYOUT=0.0]
    
    A commercial, ready-to-print sheet for papercraft cake toppers and scrapfesta. 
    The sheet MUST contain exactly these semantic concepts: {descricao_elementos}.
    
    Background: Solid, uniform, pure white background (#FFFFFF). Absolute zero gradient, zero shadows.
    Layout: Multi-element asset sheet. All components must be structurally ISOLATED, separated by clean white spaces, explicitly arranged in a non-overlapping grid grid-like layout perfect for computer vision contour tracing (Silhouette print-and-cut).
    Rendering: High-definition crisp vector asset style, 2D flat design, cute children illustration, vibrant saturated colors, bold defined clean edges, high-contrast borders.
    """

# ==============================================================================
# INTERFACE GRÁFICA DO USUÁRIO (UI / UX)
# ==============================================================================
st.title("✂️ Personalizados da Rô — Estúdio Automático de Topos")
st.markdown("Transforme prints de bolos e referências em folhas limpas com máscaras de corte instantâneas para o **Silhouette Studio**.")
st.write("---")

# Barra lateral para configuração da API Key de forma segura
with st.sidebar:
    st.header("🔑 Configurações")
    api_key_input = st.text_input("Google AI Studio API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    st.markdown("""
    ### Como usar:
    1. Cole sua chave de API válida acima.
    2. Faça o upload do print ou foto do bolo enviado pelo cliente.
    3. Clique em **'Processar e Recriar Topo'**.
    4. Baixe os arquivos gerados direto para a pasta do Silhouette!
    """)

# Área de Upload de Imagem na tela principal (Sintaxe limpa de duas colunas)
col_upload, col_preview = st.columns(2)

with col_upload:
    uploaded_file = st.file_uploader("Arraste ou selecione a foto de referência (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Exibe o preview da imagem que o cliente mandou
    img_original = Image.open(uploaded_file)
    with col_preview:
        st.image(img_original, caption="Referência Original Enviada", use_container_width=True)
        
    # Botão de Ação do App
    if st.button("🚀 Processar e Recriar Topo", type="primary"):
        if not api_key_input:
            st.error("Por favor, insira sua API Key do Gemini na barra lateral esquerda para continuar.")
        else:
            try:
                # Inicializa o cliente do Gemini com a chave fornecida na tela
                client = genai.Client(api_key=api_key_input)
                
                # Criando placeholders de progresso interativos
                status_box = st.info("Passo 1/3: Agente analisando os elementos do print e ignorando as bordas...")
                bar_progresso = st.progress(10)
                
                # --- FASE 1: LEITURA MULTIMODAL DA IA ---
                response_analise = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[PROMPT_ANALISE, img_original]
                )
                descricao_elementos = response_analise.text.strip()
                
                bar_progresso.progress(40)
                status_box.info("Passo 2/3: Gemini 2.5 Flash Image recriando os apliques no fundo branco...")
                time.sleep(2) # Evitar rate limits estritos
                
                # --- FASE 2: GERANDO A NOVA FOLHA DIGITAL ---
                prompt_final_imagem = criar_prompt_geracao(descricao_elementos)
                config_interacao = types.GenerateContentConfig(response_modalities=['IMAGE'])
                
                resultado_imagem = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[prompt_final_imagem, img_original],
                    config=config_interacao
                )
                
                img_colorida_pil = None
                for part in resultado_imagem.parts:
                    if part.inline_data is not None or hasattr(part, 'as_image'):
                        img_obj = part.as_image()
                        if isinstance(img_obj, Image.Image):
                            img_colorida_pil = img_obj
                        else:
                            # Wrapper do SDK não suporta 'format'. Salvar no disco e recarregar converte para PIL real.
                            temp_path = "temp_genai_output.png"
                            img_obj.save(temp_path)
                            img_colorida_pil = Image.open(temp_path).copy()
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        break
                        
                if img_colorida_pil is None:
                    st.error("A API do Gemini processou o pedido, mas não retornou a folha de imagem limpa.")
                else:
                    bar_progresso.progress(70)
                    status_box.info("Passo 3/3: OpenCV extraindo os contornos e gerando a máscara preta...")
                    
                    # --- FASE 3: DETECÇÃO DE SILHUETA LOCAL ---
                    try:
                        # 1. A imagem agora é garantidamente um objeto nativo PIL.Image.Image
                        img_cv = cv2.cvtColor(np.array(img_colorida_pil), cv2.COLOR_RGB2BGR)
                        altura, largura, _ = img_cv.shape
                        
                        # 3. Processamento de imagem tradicional para detecção de bordas
                        cinza = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                        borrado = cv2.GaussianBlur(cinza, (3, 3), 0)
                        _, thresh = cv2.threshold(borrado, 245, 255, cv2.THRESH_BINARY_INV)
                        
                        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        tela_mascara = np.ones((altura, largura, 3), dtype=np.uint8) * 255
                        
                        for c in contornos:
                            if cv2.contourArea(c) < 150:
                                continue
                            cv2.drawContours(tela_mascara, [c], -1, (0, 0, 0), thickness=cv2.FILLED)
                        
                        # Converte a máscara de silhueta de volta para exibição na UI
                        img_mascara_pil = Image.fromarray(cv2.cvtColor(tela_mascara, cv2.COLOR_BGR2RGB))
                        
                        bar_progresso.progress(100)
                        status_box.success("🎉 Arquivos processados com sucesso total!")
                        
                        # Exibindo os resultados lado a lado na tela para download
                        st.write("### 📥 Resultado Pronto para o Silhouette Studio")
                        col_resultado_cor, col_resultado_mascara = st.columns(2)
                        
                        with col_resultado_cor:
                            st.image(img_colorida_pil, caption="1. Folha de Elementos Limpa", use_container_width=True)
                            buf_cor = io.BytesIO()
                            img_colorida_pil.save(buf_cor, format="PNG")
                            st.download_button(label="💾 Baixar Imagem Colorida (.png)", data=buf_cor.getvalue(), file_name="topo_fiel_pronto.png", mime="image/png")
                            
                        with col_resultado_mascara:
                            st.image(img_mascara_pil, caption="2. Máscara de Rastreio (1 Clique)", use_container_width=True)
                            buf_masc = io.BytesIO()
                            img_mascara_pil.save(buf_masc, format="PNG")
                            st.download_button(label="💾 Baixar Máscara de Corte (.png)", data=buf_masc.getvalue(), file_name="topo_mascara_corte.png", mime="image/png")
                            
                    except Exception as e_opencv:
                        st.error(f"Erro no processamento da silhueta (OpenCV): {e_opencv}")
                        
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento do Agente: {e}")
else:
    st.info("Aguardando upload de um print ou foto de bolo para ligar os motores do agente...")