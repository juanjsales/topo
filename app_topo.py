"""
✂️ Personalizados da Rô — Estúdio Automático de Topos
Paleta extraída do logo: coral #E8736A, rosa claro #F2A99B, branco #FFFFFF
Modal de engrenagem para configurar a API Key (sem sidebar obrigatória).
"""

import base64
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
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PAGE_TITLE = "Personalizados da Rô"
PAGE_ICON  = "✂️"
MAX_IMAGE_DIMENSION = 1536
MAX_FILE_SIZE_MB    = 10
RETRY_ATTEMPTS      = 3
RETRY_DELAY_SECONDS = 5  # Aumentado um pouco para dar tempo de a cota por minuto respirar
GEMINI_ANALYSIS_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL    = "imagen-3.0-generate-002"  # Atualizado para o modelo estável de produção

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght=600;700&family=Nunito:wght=400;600;700;800&display=swap');

:root {
    --coral:       #E8736A;
    --coral-dark:  #C95549;
    --coral-light: #F2A99B;
    --coral-pale:  #FDE8E6;
    --cream:       #FFF7F6;
    --white:       #FFFFFF;
    --text:        #2A1210;
    --text-mid:    #6B3A36;
    --text-light:  #A07470;
    --border:      #F0D5D2;
    --shadow:      0 4px 24px rgba(232,115,106,0.10);
    --shadow-lg:   0 16px 48px rgba(232,115,106,0.18);
    --radius:      18px;
    --radius-lg:   28px;
}

* { font-family: 'Nunito', sans-serif; }

#MainMenu, header, footer { visibility: hidden; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

.stApp { background: var(--cream); }
.block-container { padding-top: 1.5rem !important; max-width: 1000px !important; }

/* Topbar */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1rem 1.8rem;
    margin-bottom: 1.8rem;
    box-shadow: var(--shadow);
}
.topbar-brand { display: flex; align-items: center; gap: 0.75rem; }
.topbar-logo {
    width: 44px; height: 44px;
    background: var(--coral-pale);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
}
.topbar-name {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.6rem; font-weight: 700;
    color: var(--coral); line-height: 1;
}
.topbar-sub {
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-light); margin-top: 3px;
}

/* Steps */
.steps-row { display: flex; gap: 0.9rem; margin-bottom: 1.8rem; }
.step {
    flex: 1; background: var(--white);
    border: 1px solid var(--border); border-radius: var(--radius);
    padding: 1.2rem 1.4rem; box-shadow: var(--shadow);
    transition: transform 0.2s ease;
}
.step:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.step-num {
    width: 26px; height: 26px; background: var(--coral); color: var(--white);
    border-radius: 50%; font-size: 0.78rem; font-weight: 800;
    display: flex; align-items: center; justify-content: center; margin-bottom: 0.6rem;
}
.step h4 { margin: 0 0 0.25rem; color: var(--text); font-size: 0.9rem; font-weight: 700; }
.step p  { margin: 0; color: var(--text-light); font-size: 0.8rem; line-height: 1.5; }

/* Labels */
.zone-label {
    font-size: 0.68rem; font-weight: 800;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--coral); margin-bottom: 0.3rem;
}

/* File info */
.file-info {
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.2rem 1.4rem;
    box-shadow: var(--shadow); font-size: 0.85rem;
    color: var(--text-mid); line-height: 1.9;
}
.file-info strong { color: var(--text); }

/* Analysis box */
.analysis-box {
    background: var(--coral-pale);
    border-left: 4px solid var(--coral);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 1rem 1.3rem; margin: 1rem 0;
    font-size: 0.86rem; color: var(--text-mid); line-height: 1.75;
}

/* Result cards */
.result-wrap {
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.3rem; box-shadow: var(--shadow);
}
.result-wrap h4 { margin: 0 0 0.8rem; color: var(--text); font-size: 0.92rem; font-weight: 700; }

/* Buttons */
.stButton > button {
    background: var(--coral) !important; color: var(--white) !important;
    border: none !important; border-radius: 999px !important;
    padding: 0.75rem 2rem !important; font-weight: 800 !important;
    font-size: 0.95rem !important; letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 16px rgba(232,115,106,0.35) !important;
    font-family: 'Nunito', sans-serif !important;
}
.stButton > button:hover {
    background: var(--coral-dark) !important; transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(232,115,106,0.45) !important;
}
.stDownloadButton > button {
    background: var(--coral-light) !important; color: var(--white) !important;
    border: none !important; border-radius: 999px !important;
    padding: 0.65rem 1.5rem !important; font-weight: 700 !important;
    font-family: 'Nunito', sans-serif !important; transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover { background: var(--coral) !important; transform: translateY(-1px) !important; }

/* Gear button específico */
div[data-testid="column"]:last-child .stButton > button {
    background: var(--coral-pale) !important;
    color: var(--coral) !important;
    border: 1.5px solid var(--border) !important;
    box-shadow: none !important;
    padding: 0.55rem 0.7rem !important;
    font-size: 1.1rem !important;
    width: 42px !important; height: 42px !important;
    border-radius: 50% !important;
    margin-top: 0.8rem;
}
div[data-testid="column"]:last-child .stButton > button:hover {
    background: var(--coral) !important; color: var(--white) !important;
    transform: rotate(30deg) !important;
    box-shadow: 0 4px 12px rgba(232,115,106,0.3) !important;
}

/* Progress */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--coral-light), var(--coral)) !important;
    border-radius: 999px !important;
}

/* Upload */
[data-testid="stFileUploadDropzone"] {
    border: 2px dashed var(--coral-light) !important;
    border-radius: var(--radius) !important;
    background: var(--coral-pale) !important;
}

/* Alerts */
.stAlert { border-radius: var(--radius) !important; }

/* Text input */
.stTextInput > div > div > input {
    border-radius: 12px !important; border: 1.5px solid var(--border) !important;
    background: var(--cream) !important; font-family: 'Nunito', sans-serif !important;
}

/* Expander (settings panel) */
[data-testid="stExpander"] {
    border: 1.5px solid var(--border) !important; border-radius: var(--radius) !important;
    background: var(--white) !important; box-shadow: var(--shadow-lg) !important;
    overflow: hidden !important; margin-bottom: 1.5rem !important;
}

hr { border-color: var(--border) !important; }
</style>
"""

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
- Arrange elements in a clean grid, 2-3 columns, evenly spaced
- No overlapping, no touching borders between elements
- Include 3-5 size variants of the most important element (small to large)

ILLUSTRATION STYLE:
- Flat vector-style illustration, bold outlines (2-3 px black stroke)
- Bright, saturated solid colors matching the originals
- No gradients, no drop shadows, no textures, no glow
- Crisp, clean silhouette edges - essential for die-cutting
- Cute children's party aesthetic, cheerful and playful

OUTPUT FORMAT:
- Landscape A4 proportion (297 x 210 mm ratio)
- All elements clearly separated and ready to cut
"""


def retry(attempts=RETRY_ATTEMPTS, delay=RETRY_DELAY_SECONDS):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    logger.warning(f"Tentativa {i}/{attempts}: {e}")
                    if i < attempts:
                        time.sleep(delay * i)
            raise last_exc
        return wrapper
    return decorator


def validar_arquivo(f) -> Optional[str]:
    if f is None:
        return None
    if f.size / 1024 / 1024 > MAX_FILE_SIZE_MB:
        return f"Arquivo muito grande ({f.size/1024/1024:.1f} MB). Limite: {MAX_FILE_SIZE_MB} MB."
    ext = f.name.rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        return f"Formato '{ext}' não suportado. Use PNG, JPG ou WEBP."
    return None


def redimensionar_se_necessario(img: Image.Image) -> Image.Image:
    w, h = img.size
    if max(w, h) <= MAX_IMAGE_DIMENSION:
        return img
    s = MAX_IMAGE_DIMENSION / max(w, h)
    return img.resize((int(w * s), int(h * s)), Image.LANCZOS)


def imagem_para_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@st.cache_resource(show_spinner=False)
def carregar_client(api_key: str):
    if not api_key:
        raise ValueError("API Key não informada.")
    return genai.Client(api_key=api_key)


@retry()
def extrair_descricao(client, imagem: Image.Image) -> str:
    resp = client.models.generate_content(
        model=GEMINI_ANALYSIS_MODEL,
        contents=[PROMPT_ANALISE, imagem],
    )
    return resp.text.strip()


def _open_image_from_bytes(raw_data):
    if raw_data is None:
        return None
    if isinstance(raw_data, Image.Image):
        return raw_data
    if isinstance(raw_data, (bytes, bytearray)):
        try:
            return Image.open(io.BytesIO(raw_data))
        except Exception:
            return None
    if isinstance(raw_data, str):
        try:
            decoded = base64.b64decode(raw_data)
            return Image.open(io.BytesIO(decoded))
        except Exception:
            try:
                return Image.open(io.BytesIO(raw_data.encode("utf-8")))
            except Exception:
                return None
    if isinstance(raw_data, dict):
        for key in ("image", "inline_data", "data", "content", "bytes", "base64"):
            if key in raw_data:
                img = _open_image_from_bytes(raw_data[key])
                if img is not None:
                    return img

    for attr in ("data", "content", "image", "bytes", "base64"):
        if hasattr(raw_data, attr):
            try:
                img = _open_image_from_bytes(getattr(raw_data, attr))
                if img is not None:
                    return img
            except Exception:
                pass

    return None


def _extract_image_from_part(part):
    if hasattr(part, "as_image"):
        try:
            img = part.as_image()
            if isinstance(img, Image.Image):
                return img
        except Exception:
            pass

    for attr in ("inline_data", "image", "data", "content", "bytes", "base64"):
        raw = getattr(part, attr, None)
        img = _open_image_from_bytes(raw)
        if img is not None:
            return img

    if isinstance(part, dict):
        return _open_image_from_bytes(part)

    return None


@retry()
def gerar_folha(client, descricao: str, imagem: Image.Image) -> Image.Image:
    # Construímos o prompt detalhado usando a descrição que o passo 1 gerou
    prompt = PROMPT_GENERATION_TEMPLATE.format(descricao_elementos=descricao)
    
    # O modelo Imagen exige que passemos apenas o texto no contents
    config = types.GenerateContentConfig(response_modalities=["IMAGE"])
    result = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=prompt,  # Passamos apenas o prompt em texto aqui
        config=config,
    )

    # Tenta extrair imagem de cada parte do resultado (mantém os seus fallbacks que estão ótimos)
    for part in getattr(result, "parts", []):
        img = _extract_image_from_part(part)
        if isinstance(img, Image.Image):
            return img.convert("RGB")

    for attr in ("image", "output", "output_image", "output_images", "data", "result"):
        img = _open_image_from_bytes(getattr(result, attr, None))
        if isinstance(img, Image.Image):
            return img.convert("RGB")

    logger.warning("Nenhuma imagem encontrada no resultado do Gemini: %s", repr(result))
    raise RuntimeError("O motor de imagem não retornou uma mídia válida. Tente novamente.")


def gerar_mascara(img: Image.Image, min_area: int = 200) -> Image.Image:
    img_cv = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    lower  = np.array([220, 220, 220], dtype=np.uint8)
    upper  = np.array([255, 255, 255], dtype=np.uint8)
    fg     = cv2.bitwise_not(cv2.inRange(img_cv, lower, upper))
    k_close = np.ones((5, 5), np.uint8)
    k_open  = np.ones((3, 3), np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k_close, iterations=2)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  k_open,  iterations=1)
    contornos, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    h, w = fg.shape
    tela = np.full((h, w), 255, dtype=np.uint8)
    for c in contornos:
        if cv2.contourArea(c) < min_area:
            continue
        eps = 0.001 * cv2.arcLength(c, True)
        cs  = cv2.approxPolyDP(c, eps, True)
        cv2.drawContours(tela, [cs], -1, 0, thickness=cv2.FILLED)
    k_dil = np.ones((3, 3), np.uint8)
    tela  = cv2.bitwise_not(cv2.dilate(cv2.bitwise_not(tela), k_dil, iterations=2))
    return Image.fromarray(tela).convert("RGB")


def main():
    st.set_page_config(
        page_title=PAGE_TITLE, page_icon=PAGE_ICON,
        layout="wide", initial_sidebar_state="collapsed",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False

    # Topbar + botão engrenagem
    col_brand, col_gear = st.columns([11, 1])
    with col_brand:
        st.markdown(
            """
            <div class='topbar'>
                <div class='topbar-brand'>
                    <div class='topbar-logo'>🎀</div>
                    <div>
                        <div class='topbar-name'>Personalizados da Rô</div>
                        <div class='topbar-sub'>Estúdio Automático de Topos</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_gear:
        if st.button("⚙️", help="Configurar API Key", key="btn_gear"):
            st.session_state.show_settings = not st.session_state.show_settings

    # Painel de configurações (expander controlado por estado)
    if st.session_state.show_settings:
        with st.expander("⚙️  Configurações — Google AI Studio API Key", expanded=True):
            nova_key = st.text_input(
                "Cole sua API Key aqui",
                value=st.session_state.api_key,
                type="password",
                placeholder="AIza...",
                help="Obtenha gratuitamente em aistudio.google.com",
            )
            col_s, col_c, col_tip = st.columns([1, 1, 4])
            with col_s:
                if st.button("💾 Salvar", key="btn_save"):
                    st.session_state.api_key = nova_key.strip()
                    st.session_state.show_settings = False
                    st.rerun()
            with col_c:
                if st.button("🗑️ Limpar", key="btn_clear"):
                    st.session_state.api_key = ""
                    st.rerun()
            with col_tip:
                st.markdown(
                    "<small style='color:#A07470'>🔒 A chave fica apenas nesta sessão e nunca é armazenada em servidor.</small>",
                    unsafe_allow_html=True,
                )

    api_key = st.session_state.api_key

    # Steps
    st.markdown(
        """
        <div class='steps-row'>
            <div class='step'>
                <div class='step-num'>1</div>
                <h4>Envie a referência</h4>
                <p>Foto ou print do topo do bolo. JPG, PNG ou WEBP até 10 MB.</p>
            </div>
            <div class='step'>
                <div class='step-num'>2</div>
                <h4>IA recria os elements</h4>
                <p>Gemini identifica o tema e gera folha isolada com fundo branco.</p>
            </div>
            <div class='step'>
                <div class='step-num'>3</div>
                <h4>Baixe e corte</h4>
                <p>Folha colorida + máscara prontas para o Silhouette Studio.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Upload
    st.markdown("<div class='zone-label'>Imagem de referência</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Arraste ou clique para selecionar",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )

    erro = validar_arquivo(uploaded)
    if erro:
        st.error(f"❌ {erro}")
        return

    if uploaded is None:
        st.info("📂 Envie uma imagem para começar.")
        if not api_key:
            st.warning("⚠️ Lembre de configurar sua API Key clicando no ⚙️ acima.")
        return

    img_original = redimensionar_se_necessario(Image.open(uploaded).convert("RGB"))
    w, h = img_original.size

    col_img, col_info = st.columns([1, 1])
    with col_img:
        st.image(img_original, caption="Referência enviada", use_container_width=True)
    with col_info:
        st.markdown(
            f"""
            <div class='file-info'>
                <strong>📄 Arquivo:</strong> {uploaded.name}<br>
                <strong>📦 Tamanho:</strong> {uploaded.size/1024:.0f} KB<br>
                <strong>📐 Dimensões:</strong> {w} × {h} px<br>
                <strong>🔑 API Key:</strong> {'✅ Configurada' if api_key else '❌ Não configurada'}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not api_key:
            st.warning("⚠️ Configure a API Key clicando no ⚙️ no topo da página.")
            return

    if not api_key:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 2])
    with col_btn:
        iniciar = st.button("✂️ Gerar Folha de Corte")

    if not iniciar:
        return

    try:
        client = carregar_client(api_key)
    except ValueError as e:
        st.error(str(e))
        return

    progresso = st.progress(0)
    status    = st.empty()

    try:
        status.markdown("🔍 **Passo 1/3** — Identificando elementos do topo…")
        progresso.progress(5)
        descricao = extrair_descricao(client, img_original)
        progresso.progress(30)

        st.markdown(
            f"<div class='analysis-box'><strong>Elementos identificados:</strong><br>"
            f"{descricao.replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )

        status.markdown("🎨 **Passo 2/3** — Gerando folha limpa com IA…")
        img_colorida = gerar_folha(client, descricao, img_original)
        progresso.progress(70)

        status.markdown("✂️ **Passo 3/3** — Criando máscara de corte…")
        mascara = gerar_mascara(img_colorida)
        progresso.progress(100)
        status.success("🎉 Pronto! Baixe os arquivos abaixo.")

        st.markdown("---")
        st.markdown("<div class='zone-label'>Resultado</div>", unsafe_allow_html=True)

        col_c, col_m = st.columns(2)
        with col_c:
            st.markdown("<div class='result-wrap'><h4>🖼️ Folha de Elementos</h4>", unsafe_allow_html=True)
            st.image(img_colorida, caption="Pronta para imprimir", use_container_width=True)
            st.download_button(
                "💾 Baixar Folha Colorida (.png)",
                data=imagem_para_bytes(img_colorida),
                file_name="topo_elementos.png",
                mime="image/png",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_m:
            st.markdown("<div class='result-wrap'><h4>✂️ Máscara de Corte</h4>", unsafe_allow_html=True)
            st.image(mascara, caption="Importe no Silhouette Studio", use_container_width=True)
            st.download_button(
                "💾 Baixar Máscara de Corte (.png)",
                data=imagem_para_bytes(mascara),
                file_name="topo_mascara_corte.png",
                mime="image/png",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.info(
            "💡 **Silhouette Studio:** Importe a Máscara como traço de corte e a Folha Colorida "
            "como imagem de impressão. Use o modo **Print & Cut** para alinhar automaticamente."
        )

    except RuntimeError as e:
        progresso.empty(); status.empty()
        st.error(f"❌ {e}")
        logger.exception("Erro no pipeline")
    except Exception as e:
        progresso.empty(); status.empty()
        st.error("❌ Erro inesperado:")
        st.exception(e)
        logger.exception("Erro inesperado")


if __name__ == "__main__":
    main()
