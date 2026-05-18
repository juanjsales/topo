import io
import os
import time

import cv2
import numpy as np
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

PAGE_TITLE = "✂️ Personalizados da Rô — Estúdio Automático de Topos"
PAGE_ICON = "🏔️"

PROMPT_ANALISE = """
Você é um assistente especializado em identificar apenas os elementos de topo do bolo.
Ignore o bolo, o fundo, velas, suporte e outras decorações não relacionadas ao topo.
Responda em inglês com uma descrição clara dos elementos a serem recriados em um layout de corte.
"""

PROMPT_GENERATION_TEMPLATE = """
A printable sheet for cake toppers and scrapbooking paper crafts.
The sheet must contain exactly these elements: {descricao_elementos}.
The result must use a pure white background (#FFFFFF), no shadows, no gradients,
and each object must be isolated, non-overlapping, and easy to cut.
Rendering: flat vector-style illustration, cute children theme, bright saturated colors,
crisp edges, strong contrast, clean shapes for silhouette cutting.
"""


def aplicar_css_personalizado():
    st.markdown(
        """
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}

            .stButton > button {
                background-color: #2563EB;
                color: white;
                border-radius: 8px;
                border: none;
                padding: 0.75rem 1rem;
                font-weight: 600;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }

            .stButton > button:hover {
                background-color: #1D4ED8;
                box-shadow: 0 8px 18px rgba(37, 99, 235, 0.25);
                transform: translateY(-1px);
            }

            .stTextInput > div > div > input,
            .stFileUploader {
                border-radius: 10px;
                border: 1px solid #E5E7EB;
            }

            .stFileUploader {
                background-color: #F8FAFC;
                border: 2px dashed #93C5FD !important;
            }

            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 2rem !important;
                max-width: 1200px;
            }

            .hero {
                padding: 2rem;
                border-radius: 24px;
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(16, 185, 129, 0.12));
                border: 1px solid rgba(59, 130, 246, 0.18);
                box-shadow: 0 30px 80px rgba(15, 23, 42, 0.08);
                margin-bottom: 1.5rem;
            }

            .hero h1 {
                margin-bottom: 0.25rem;
                font-size: 2.6rem;
                letter-spacing: -0.04em;
            }

            .hero p {
                font-size: 1.05rem;
                line-height: 1.8;
                color: #334155;
            }

            .step-card {
                background: #ffffff;
                border-radius: 18px;
                padding: 1.4rem;
                border: 1px solid #E2E8F0;
                box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
                margin-bottom: 1rem;
            }

            .step-card h3 {
                margin-top: 0;
                margin-bottom: 0.5rem;
                color: #0F172A;
            }

            .step-card p {
                margin: 0;
                color: #475569;
            }

            .stButton > button,
            .stDownloadButton > button {
                background-color: #2563EB;
                color: white;
                border-radius: 999px;
                border: none;
                padding: 0.85rem 1.2rem;
                font-weight: 700;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover {
                background-color: #1D4ED8;
                box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
                transform: translateY(-1px);
            }

            .stTextInput > div > div > input,
            .stFileUploader,
            .stMarkdown {
                border-radius: 14px;
            }

            .stProgress > div > div > div {
                background: linear-gradient(90deg, #3B82F6, #10B981);
            }

            .stAlert {
                border-radius: 18px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def criar_prompt_geracao(descricao_elementos: str) -> str:
    return PROMPT_GENERATION_TEMPLATE.format(descricao_elementos=descricao_elementos)


def carregar_client_gemini(api_key: str):
    if not api_key:
        raise ValueError("A API Key do Gemini não foi informada.")
    return genai.Client(api_key=api_key)


def extrair_descricao_gemini(client, imagem: Image.Image) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_ANALISE, imagem],
    )
    return response.text.strip()


def gerar_folha_colorida(client, descricao_elementos: str, imagem: Image.Image) -> Image.Image:
    prompt_final = criar_prompt_geracao(descricao_elementos)
    config_interacao = types.GenerateContentConfig(response_modalities=["IMAGE"])
    resultado = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt_final, imagem],
        config=config_interacao,
    )

    for part in resultado.parts:
        if hasattr(part, "as_image"):
            imagem_final = part.as_image()
            if isinstance(imagem_final, Image.Image):
                return imagem_final.convert("RGB")

    raise RuntimeError("A API do Gemini não retornou uma imagem válida.")


def gerar_mascara_de_corte(img_colorida: Image.Image, min_area: int = 150) -> Image.Image:
    img_cv = cv2.cvtColor(np.array(img_colorida.convert("RGB")), cv2.COLOR_RGB2BGR)
    cinza = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    borrado = cv2.GaussianBlur(cinza, (5, 5), 0)
    _, thresh = cv2.threshold(borrado, 245, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)

    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    altura, largura = thresh.shape
    tela_mascara = np.full((altura, largura), 255, dtype=np.uint8)

    for c in contornos:
        if cv2.contourArea(c) < min_area:
            continue
        cv2.drawContours(tela_mascara, [c], -1, 0, thickness=cv2.FILLED)

    return Image.fromarray(tela_mascara).convert("RGB")


def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    aplicar_css_personalizado()

    st.markdown(
        """
        <div class='hero'>
            <h1>{title}</h1>
            <p>Transforme prints de bolos e referências em folhas limpas com máscaras de corte automáticas para o <strong>Silhouette Studio</strong>, em apenas alguns cliques.</p>
        </div>
        """.format(title=PAGE_TITLE),
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.markdown(
        """
        <div class='step-card'>
            <h3>1. Envio</h3>
            <p>Faça upload da foto ou print do bolo de cliente. Qualquer imagem clara serve.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col2.markdown(
        """
        <div class='step-card'>
            <h3>2. Processamento</h3>
            <p>Gemini analisa e recria os elementos principais do topo com fundo branco.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col3.markdown(
        """
        <div class='step-card'>
            <h3>3. Download</h3>
            <p>Baixe a folha de corte e a máscara pronta para usar no Silhouette Studio.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("---")

    with st.sidebar:
        st.header("🔑 Configurações")
        api_key_input = st.text_input("Google AI Studio API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
        st.markdown(
            """
            **Como usar:**
            1. Cole sua chave de API válida acima.
            2. Faça o upload da imagem de referência.
            3. Clique em **Processar e Recriar Topo**.
            4. Baixe a folha colorida e a máscara de corte.
            """
        )
        st.markdown("---")
        st.subheader("Dicas rápidas")
        st.write(
            "- Use imagens com boa iluminação e foco no topo do bolo.\n"
            "- Evite fotos com bordas muito escuras ou fundos complexos.\n"
            "- Arquivos JPG/PNG funcionam melhor."
        )
        st.info("Sua chave de API fica segura no navegador enquanto o app estiver aberto.")

    api_key = api_key_input.strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    uploaded_file = st.file_uploader("Arraste ou selecione a imagem de referência", type=["png", "jpg", "jpeg"])

    if uploaded_file is None:
        st.info("Envie uma imagem para iniciar o processamento.")
        return

    img_original = Image.open(uploaded_file).convert("RGB")
    col_upload, col_preview = st.columns([1, 1])
    with col_preview:
        st.image(img_original, caption="Referência Original Enviada", use_container_width=True)

    if not api_key:
        st.warning("API Key não informada. Configure `GEMINI_API_KEY` no ambiente ou cole na barra lateral.")
        return

    if st.button("🚀 Processar e Recriar Topo"):
        try:
            client = carregar_client_gemini(api_key)
            status_box = st.info("Passo 1/3: analisando elementos do topo com Gemini...")
            progress = st.progress(5)
            descricao_elementos = extrair_descricao_gemini(client, img_original)
            progress.progress(30)

            status_box.info("Passo 2/3: gerando folha limpa e separada...")
            time.sleep(1)
            imagem_colorida = gerar_folha_colorida(client, descricao_elementos, img_original)
            progress.progress(65)

            status_box.info("Passo 3/3: criando máscara de corte com OpenCV...")
            mascara = gerar_mascara_de_corte(imagem_colorida)
            progress.progress(100)
            status_box.success("🎉 Processamento concluído com sucesso!")

            st.write("### 📥 Resultado Pronto para o Silhouette Studio")
            col_resultado_cor, col_resultado_mascara = st.columns(2)

            with col_resultado_cor:
                st.image(imagem_colorida, caption="Folha de Elementos Limpa", use_container_width=True)
                buf_cor = io.BytesIO()
                imagem_colorida.save(buf_cor, format="PNG")
                st.download_button(
                    label="💾 Baixar Imagem Colorida (.png)",
                    data=buf_cor.getvalue(),
                    file_name="topo_fiel_pronto.png",
                    mime="image/png",
                )

            with col_resultado_mascara:
                st.image(mascara, caption="Máscara de Corte", use_container_width=True)
                buf_masc = io.BytesIO()
                mascara.save(buf_masc, format="PNG")
                st.download_button(
                    label="💾 Baixar Máscara de Corte (.png)",
                    data=buf_masc.getvalue(),
                    file_name="topo_mascara_corte.png",
                    mime="image/png",
                )

        except Exception as error:
            st.error("Ocorreu um erro durante o processamento. Veja mais detalhes abaixo.")
            st.exception(error)


if __name__ == "__main__":
    main()





