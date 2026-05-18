"""
✂️ Personalizados da Rô — Estúdio Automático de Topos
Versão melhorada: prompts mais ricos, UX refinada, retry robusto e cache de sessão.
"""

import io
import os
import time
import logging
from functools import wraps
from typing import Optional

import cv2
import numpy as np
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PAGE_TITLE = "✂️ Personalizados da Rô"
PAGE_ICON = "✂️"
MAX_IMAGE_DIMENSION = 1536       # redimensiona antes de enviar à API
MAX_FILE_SIZE_MB = 10
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

GEMINI_ANALYSIS_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

# ---------------------------------------------------------------------------
# Prompts — melhorados para resultados mais limpos e fiéis
# ---------------------------------------------------------------------------
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

Keep the description focused and actionable for an illustrator recreating these elements.
"""

PROMPT_GENERATION_TEMPLATE = """
Create a professional printable craft sheet for Silhouette Studio / Cricut cutting machines.

ELEMENTS TO INCLUDE: {descricao_elementos}

STRICT LAYOUT RULES:
- Pure white background (#FFFFFF), no exceptions
- Each element must be completely isolated with at least 8 px white border around it
- Arrange elements in a clean grid, 2–3 columns, evenly spaced
- No overlapping, no touching borders between elements
- Include 3–5 size variants of the most important element (small → large)

ILLUSTRATION STYLE:
- Flat vector-style illustration, bold outlines (2–3 px black stroke)
- Bright, saturated solid colors matching the originals
- No gradients, no drop shadows, no textures, no glow
- Crisp, clean silhouette edges — essential for die-cutting
- Cute children's party aesthetic, cheerful and playful

OUTPUT FORMAT:
- Landscape A4 proportion (297 × 210 mm ratio)
- All elements clearly separated and ready to cut
"""

# ---------------------------------------------------------------------------
# CSS — visual artesanal/editorial com paleta quente
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@400;500;600&display=swap');

:root {
    --brand-primary: #D4622A;
    --brand-secondary: #F0A04B;
    --brand-accent: #3B6B8F;
    --bg-cream: #FDF8F3;
    --bg-card: #FFFFFF;
    --text-dark: #1C1410;
    --text-mid: #5C4A3A;
    --text-light: #8C7A6A;
    --border: #EDE4D8;
    --shadow-soft: 0 4px 24px rgba(28,20,16,0.08);
    --shadow-strong: 0 16px 48px rgba(28,20,16,0.14);
    --radius: 16px;
    --radius-lg: 24px;
}

* { font-family: 'DM Sans', sans-serif; }

#MainMenu, header, footer { visibility: hidden; }

.stApp { background-color: var(--bg-cream); }

/* ── Hero ──────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #FFF4EB 0%, #FDE8D4 60%, #EDF4F9 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '✂';
    position: absolute;
    right: 2.5rem; top: 1.5rem;
    font-size: 7rem;
    opacity: 0.06;
    line-height: 1;
}
.hero h1 {
    font-family: 'Playfair Display', serif;
    font-size: 2.8rem;
    font-weight: 900;
    color: var(--brand-primary);
    margin: 0 0 0.5rem;
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.hero p {
    color: var(--text-mid);
    font-size: 1.05rem;
    line-height: 1.75;
    margin: 0;
    max-width: 620px;
}

/* ── Step cards ────────────────────────────────── */
.step-grid { display: flex; gap: 1rem; margin-bottom: 2rem; }
.step-card {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.4rem 1.6rem;
    box-shadow: var(--shadow-soft);
    position: relative;
}
.step-num {
    display: inline-block;
    width: 28px; height: 28px;
    background: var(--brand-primary);
    color: white;
    border-radius: 50%;
    font-size: 0.85rem;
    font-weight: 700;
    line-height: 28px;
    text-align: center;
    margin-bottom: 0.75rem;
}
.step-card h3 { margin: 0 0 0.3rem; color: var(--text-dark); font-size: 1rem; font-weight: 600; }
.step-card p  { margin: 0; color: var(--text-light); font-size: 0.88rem; line-height: 1.55; }

/* ── Section label ─────────────────────────────── */
.section-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--brand-primary);
    margin-bottom: 0.4rem;
}

/* ── Result card ───────────────────────────────── */
.result-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.4rem;
    box-shadow: var(--shadow-soft);
    margin-bottom: 1rem;
}
.result-card h4 { margin: 0 0 0.75rem; color: var(--text-dark); font-size: 0.95rem; font-weight: 600; }

/* ── Análise box ───────────────────────────────── */
.analysis-box {
    background: #FEFBF7;
    border-left: 4px solid var(--brand-secondary);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    font-size: 0.88rem;
    color: var(--text-mid);
    line-height: 1.7;
}

/* ── Streamlit overrides ───────────────────────── */
.stButton > button {
    background: var(--brand-primary) !important;
    color: white !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 0.75rem 2rem !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 16px rgba(212,98,42,0.3) !important;
}
.stButton > button:hover {
    background: #B8521F !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(212,98,42,0.4) !important;
}
.stDownloadButton > button {
    background: var(--brand-accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 0.65rem 1.5rem !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover {
    background: #2D5472 !important;
    transform: translateY(-1px) !important;
}
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--brand-primary), var(--brand-secondary)) !important;
    border-radius: 999px !important;
}
.stFileUploader {
    border-radius: var(--radius) !important;
    border: 2px dashed var(--brand-secondary) !important;
    background: #FEFBF7 !important;
}
.stAlert { border-radius: var(--radius) !important; }
.stTextInput > div > div > input {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
    background: #FEFBF7 !important;
}
.block-container {
    padding-top: 2rem !important;
    max-width: 1100px !important;
}
.sidebar .stMarkdown { font-size: 0.9rem; color: var(--text-mid); }
</style>
"""

# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def retry(attempts: int = RETRY_ATTEMPTS, delay: float = RETRY_DELAY_SECONDS):
    """Decorator de retry com backoff linear para chamadas à API."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    logger.warning(f"Tentativa {attempt}/{attempts} falhou: {exc}")
                    if attempt < attempts:
                        time.sleep(delay * attempt)
            raise last_exc
        return wrapper
    return decorator


def validar_arquivo(uploaded_file) -> Optional[str]:
    """Retorna mensagem de erro ou None se o arquivo for válido."""
    if uploaded_file is None:
        return None
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return f"Arquivo muito grande ({size_mb:.1f} MB). Limite: {MAX_FILE_SIZE_MB} MB."
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        return f"Formato '{ext}' não suportado. Use PNG, JPG ou WEBP."
    return None


def redimensionar_se_necessario(img: Image.Image) -> Image.Image:
    """Redimensiona mantendo proporção se alguma dimensão exceder o limite."""
    w, h = img.size
    if max(w, h) <= MAX_IMAGE_DIMENSION:
        return img
    escala = MAX_IMAGE_DIMENSION / max(w, h)
    novo_w, novo_h = int(w * escala), int(h * escala)
    logger.info(f"Redimensionando imagem: {w}×{h} → {novo_w}×{novo_h}")
    return img.resize((novo_w, novo_h), Image.LANCZOS)


def imagem_para_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Camada Gemini — com retry e cache de sessão
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def carregar_client_gemini(api_key: str):
    if not api_key:
        raise ValueError("API Key não informada.")
    return genai.Client(api_key=api_key)


@retry()
def extrair_descricao_gemini(client, imagem: Image.Image) -> str:
    """Analisa a imagem e retorna descrição dos elementos do topo."""
    response = client.models.generate_content(
        model=GEMINI_ANALYSIS_MODEL,
        contents=[PROMPT_ANALISE, imagem],
    )
    return response.text.strip()


@retry()
def gerar_folha_colorida(client, descricao_elementos: str, imagem: Image.Image) -> Image.Image:
    """Gera a folha de elementos limpa via Gemini Image."""
    prompt_final = PROMPT_GENERATION_TEMPLATE.format(descricao_elementos=descricao_elementos)
    config = types.GenerateContentConfig(response_modalities=["IMAGE"])

    resultado = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=[prompt_final, imagem],
        config=config,
    )

    for part in resultado.parts:
        if hasattr(part, "as_image"):
            img = part.as_image()
            if isinstance(img, Image.Image):
                return img.convert("RGB")

    raise RuntimeError("A API do Gemini não retornou imagem válida. Tente novamente.")


# ---------------------------------------------------------------------------
# Processamento de máscara — melhorado
# ---------------------------------------------------------------------------

def gerar_mascara_de_corte(img_colorida: Image.Image, min_area: int = 200) -> Image.Image:
    """
    Gera máscara de corte com contornos suavizados e tolerância de cor ajustada.
    Retorna imagem em escala de cinza (branco = fundo, preto = área de corte).
    """
    img_rgb = np.array(img_colorida.convert("RGB"))
    img_cv  = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    # 1. Subtrai fundo branco com tolerância de cor (lida com JPG artefatos)
    lower_white = np.array([220, 220, 220], dtype=np.uint8)
    upper_white = np.array([255, 255, 255], dtype=np.uint8)
    mascara_branco = cv2.inRange(img_cv, lower_white, upper_white)
    foreground_mask = cv2.bitwise_not(mascara_branco)

    # 2. Fecha buracos internos e remove ruído
    kernel_close = np.ones((5, 5), np.uint8)
    kernel_open  = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(foreground_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN,  kernel_open,  iterations=1)

    # 3. Encontra contornos externos
    contornos, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    altura, largura = cleaned.shape
    tela = np.full((altura, largura), 255, dtype=np.uint8)

    for c in contornos:
        if cv2.contourArea(c) < min_area:
            continue
        # Suaviza contorno levemente
        epsilon = 0.001 * cv2.arcLength(c, True)
        c_smooth = cv2.approxPolyDP(c, epsilon, True)
        cv2.drawContours(tela, [c_smooth], -1, 0, thickness=cv2.FILLED)

    # 4. Dilata 2 px para folga de corte
    kernel_dilate = np.ones((3, 3), np.uint8)
    tela = cv2.dilate(cv2.bitwise_not(tela), kernel_dilate, iterations=2)
    tela = cv2.bitwise_not(tela)

    return Image.fromarray(tela).convert("RGB")


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Hero ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class='hero'>
            <h1>Personalizados da Rô</h1>
            <p>Transforme qualquer foto de bolo em folhas limpas com máscaras de corte prontas
            para o <strong>Silhouette Studio</strong> — em segundos, sem edição manual.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Steps ───────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class='step-grid'>
            <div class='step-card'>
                <div class='step-num'>1</div>
                <h3>Envie a referência</h3>
                <p>Foto ou print do topo do bolo. JPG, PNG ou WEBP até 10 MB.</p>
            </div>
            <div class='step-card'>
                <div class='step-num'>2</div>
                <h3>IA recria os elementos</h3>
                <p>Gemini identifica o tema e gera uma folha isolada com fundo branco.</p>
            </div>
            <div class='step-card'>
                <div class='step-num'>3</div>
                <h3>Baixe e corte</h3>
                <p>Folha colorida + máscara de corte prontas para o Silhouette Studio.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar ─────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔑 API Key")
        api_key_input = st.text_input(
            "Google AI Studio API Key",
            type="password",
            value=os.environ.get("GEMINI_API_KEY", ""),
            help="Obtenha sua chave em aistudio.google.com",
        )
        st.markdown("---")
        st.markdown("**Como usar**")
        st.markdown(
            "1. Cole a API Key acima\n"
            "2. Envie a imagem de referência\n"
            "3. Clique em **Gerar Folha de Corte**\n"
            "4. Baixe os arquivos prontos"
        )
        st.markdown("---")
        st.markdown("**💡 Dicas para melhores resultados**")
        st.markdown(
            "- Prefira fotos com boa iluminação\n"
            "- O topo deve estar bem visível\n"
            "- Evite fundos muito escuros\n"
            "- JPG/PNG funcionam melhor que WEBP"
        )
        st.markdown("---")
        st.caption("🔒 Sua chave fica apenas nesta sessão e nunca é armazenada.")

    api_key = (api_key_input or "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()

    # ── Upload ───────────────────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Imagem de referência</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Arraste ou clique para selecionar",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )

    erro_arquivo = validar_arquivo(uploaded_file)
    if erro_arquivo:
        st.error(f"❌ {erro_arquivo}")
        return

    if uploaded_file is None:
        st.info("📂 Envie uma imagem para começar.")
        return

    # Preview da imagem original
    img_original = Image.open(uploaded_file).convert("RGB")
    img_original = redimensionar_se_necessario(img_original)

    col_prev, col_info = st.columns([1, 1])
    with col_prev:
        st.image(img_original, caption="Referência enviada", use_container_width=True)
    with col_info:
        w, h = img_original.size
        st.markdown(
            f"""
            <div class='result-card'>
                <h4>📋 Detalhes do arquivo</h4>
                <p><strong>Nome:</strong> {uploaded_file.name}</p>
                <p><strong>Tamanho:</strong> {uploaded_file.size / 1024:.0f} KB</p>
                <p><strong>Dimensões:</strong> {w} × {h} px</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not api_key:
            st.warning("⚠️ Insira sua API Key na barra lateral para continuar.")
            return

        st.markdown("Tudo pronto! Clique abaixo para processar.")

    # ── Botão de processamento ───────────────────────────────────────────────
    if not api_key:
        return

    col_btn, _ = st.columns([1, 2])
    with col_btn:
        iniciar = st.button("🚀 Gerar Folha de Corte", use_container_width=True)

    if not iniciar:
        return

    # ── Pipeline ─────────────────────────────────────────────────────────────
    try:
        client = carregar_client_gemini(api_key)
    except ValueError as e:
        st.error(str(e))
        return

    progresso   = st.progress(0)
    status_text = st.empty()

    try:
        # Passo 1 — Análise
        status_text.markdown("🔍 **Passo 1/3** — Identificando elementos do topo…")
        progresso.progress(5)
        descricao = extrair_descricao_gemini(client, img_original)
        progresso.progress(30)

        # Mostra descrição gerada
        st.markdown(
            f"<div class='analysis-box'><strong>Elementos identificados:</strong><br>{descricao.replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )

        # Passo 2 — Geração de imagem
        status_text.markdown("🎨 **Passo 2/3** — Gerando folha limpa com IA…")
        imagem_colorida = gerar_folha_colorida(client, descricao, img_original)
        progresso.progress(70)

        # Passo 3 — Máscara
        status_text.markdown("✂️ **Passo 3/3** — Criando máscara de corte…")
        mascara = gerar_mascara_de_corte(imagem_colorida)
        progresso.progress(100)
        status_text.success("🎉 Processamento concluído! Baixe os arquivos abaixo.")

        # ── Resultados ───────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("<div class='section-label'>Resultado</div>", unsafe_allow_html=True)

        col_cor, col_mask = st.columns(2)

        with col_cor:
            st.markdown("<div class='result-card'><h4>🖼️ Folha de Elementos</h4>", unsafe_allow_html=True)
            st.image(imagem_colorida, caption="Pronta para imprimir", use_container_width=True)
            st.download_button(
                label="💾 Baixar Folha Colorida (.png)",
                data=imagem_para_bytes(imagem_colorida),
                file_name="topo_elementos.png",
                mime="image/png",
                use_container_width=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_mask:
            st.markdown("<div class='result-card'><h4>✂️ Máscara de Corte</h4>", unsafe_allow_html=True)
            st.image(mascara, caption="Importe no Silhouette Studio", use_container_width=True)
            st.download_button(
                label="💾 Baixar Máscara de Corte (.png)",
                data=imagem_para_bytes(mascara),
                file_name="topo_mascara_corte.png",
                mime="image/png",
                use_container_width=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Dica de uso
        st.info(
            "💡 **Como usar no Silhouette Studio:** Importe a Máscara de Corte como traço de corte "
            "e a Folha Colorida como imagem de impressão. Use o modo Print & Cut para alinhar automaticamente."
        )

    except RuntimeError as e:
        progresso.empty()
        status_text.empty()
        st.error(f"❌ Erro de processamento: {e}")
        st.markdown(
            "**Sugestões:** verifique se a API Key é válida e se a imagem está clara. "
            "Você pode tentar novamente com uma foto diferente."
        )
        logger.exception("Erro no pipeline de processamento")

    except Exception as e:
        progresso.empty()
        status_text.empty()
        st.error("❌ Erro inesperado. Detalhes abaixo:")
        st.exception(e)
        logger.exception("Erro inesperado")


if __name__ == "__main__":
    main()