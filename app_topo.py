"""
✂️ Personalizados da Rô — Estúdio Prático de Topos
Paleta extraída do logo: coral #E8736A, rosa claro #F2A99B, branco #FFFFFF
Versão Simplificada e Funcional: Rembg + OpenCV Inpainting por Desenho Manual (Sem travamentos)
"""

import io
import os
import logging
import cv2
import numpy as np
import streamlit as st
from PIL import Image

try:
    from rembg import remove
except ImportError:
    os.system("pip install rembg")
    from rembg import remove

try:
    import ezdxf
except ImportError:
    os.system("pip install ezdxf")
    import ezdxf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PAGE_TITLE = "Personalizados da Rô"
PAGE_ICON  = "✂️"
MAX_IMAGE_DIMENSION = 1200

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
.stApp { background: var(--cream); }
.block-container { padding-top: 1.5rem !important; max-width: 1000px !important; }

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

.result-wrap {
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.3rem; box-shadow: var(--shadow);
    margin-bottom: 1rem;
}

.stButton > button {
    background: var(--coral) !important; color: var(--white) !important;
    border: none !important; border-radius: 999px !important;
    padding: 0.75rem 2rem !important; font-weight: 800 !important;
}
.stDownloadButton > button {
    background: var(--coral-light) !important; color: var(--white) !important;
    border: none !important; border-radius: 999px !important;
    padding: 0.65rem 1.5rem !important; font-weight: 700 !important;
    width: 100%;
}
</style>
"""

def redimensionar_se_necessario(img: Image.Image) -> Image.Image:
    w, h = img.size
    if max(w, h) <= MAX_IMAGE_DIMENSION:
        return img
    s = MAX_IMAGE_DIMENSION / max(w, h)
    return img.resize((int(w * s), int(h * s)), Image.Resampling.LANCZOS)

def imagem_para_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

def exportar_contornos_para_dxf(folha_corte_np: np.ndarray) -> bytes:
    _, thresh = cv2.threshold(folha_corte_np, 127, 255, cv2.THRESH_BINARY_INV)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    for c in contornos:
        epsilon = 0.002 * cv2.arcLength(c, True)
        contorno_suave = cv2.approxPolyDP(c, epsilon, True)
        pontos_vetor = []
        for p in contorno_suave:
            px, py = p[0]
            pontos_vetor.append((float(px), float(1000 - py)))
            
        if len(pontos_vetor) > 2:
            pontos_vetor.append(pontos_vetor[0])
            msp.add_lwpolyline(pontos_vetor)
            
    out_buf = io.StringIO()
    doc.write(out_buf)
    return out_buf.getvalue().encode('utf-8')

def executar_fluxo_papelaria(img_rgba_limpa, w, h):
    """ Processa os blocos, gera as sangrias e monta a folha A4 final """
    arr_rgba = np.array(img_rgba_limpa)
    alpha = arr_rgba[:, :, 3]
    
    _, thresh = cv2.threshold(alpha, 5, 255, cv2.THRESH_BINARY)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    thresh_fechado = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)
    
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh_fechado, connectivity=8)
    
    assets_coloridos = []
    assets_mascaras = []

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 250 or area > (w * h * 0.65):
            continue
            
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]
        
        m = 20
        x_min, y_min = max(0, x - m), max(0, y - m)
        x_max, y_max = min(w, x + comp_w + m), min(h, y + comp_h + m)
        
        mascara_componente = (labels == i).astype(np.uint8) * 255
        sub_alpha = mascara_componente[y_min:y_max, x_min:x_max]
        sub_rgb = arr_rgba[y_min:y_max, x_min:x_max, :3]
        
        kernel_dilatacao = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
        alpha_dilatado = cv2.dilate(sub_alpha, kernel_dilatacao, iterations=1)
        
        fundo_branco = np.full_like(sub_rgb, 255)
        item_rgb = fundo_branco.copy()
        item_rgb[alpha_dilatado > 0] = [255, 255, 255]
        item_rgb[sub_alpha > 0] = sub_rgb[sub_alpha > 0]
        
        item_corte = np.full_like(alpha_dilatado, 255)
        item_corte[alpha_dilatado == 255] = 0
        
        assets_coloridos.append(Image.fromarray(item_rgb))
        assets_mascaras.append(Image.fromarray(item_corte).convert("RGB"))
        
    if not assets_coloridos:
        return None, None

    largura_a4, altura_a4 = 1414, 1000
    folha_impressao = Image.new("RGB", (largura_a4, altura_a4), "white")
    folha_corte = Image.new("RGB", (largura_a4, altura_a4), "white")
    
    num_assets = len(assets_coloridos)
    colunas = 3 if num_assets >= 3 else num_assets
    margem_grid = 50
    box_w = (largura_a4 - (colunas + 1) * margem_grid) // colunas
    box_h = box_w
    
    x_pos, y_pos = margem_grid, margem_grid
    
    for idx in range(num_assets):
        asset_c = assets_coloridos[idx]
        asset_m = assets_mascaras[idx]
        
        asset_c.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
        asset_m.thumbnail((box_w, box_h), Image.Resampling.NEAREST)
        
        o_x = (box_w - asset_c.width) // 2
        o_y = (box_h - asset_c.height) // 2
        
        folha_impressao.paste(asset_c, (x_pos + o_x, y_pos + o_y))
        folha_corte.paste(asset_m, (x_pos + o_x, y_pos + o_y))
        
        x_pos += box_w + margem_grid
        if x_pos + box_w > largura_a4:
            x_pos = margem_grid
            y_pos += box_h + margem_grid
        if y_pos + box_h > altura_a4:
            break
            
    return folha_impressao, folha_corte

def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown("<div class='topbar'><div class='topbar-brand'><div class='topbar-logo'>✂️</div><div><div class='topbar-name'>Personalizados da Rô</div><div class='topbar-sub'>Estúdio Automático Prático</div></div></div></div>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Selecione a imagem de referência", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")
    
    if uploaded is None:
        return

    img_original = redimensionar_se_necessario(Image.open(io.BytesIO(uploaded.getvalue())).convert("RGB"))
    w, h = img_original.size

    # Passo 1: Isolação de fundo padrão ultra-rápida via rembg
    with st.spinner("Removendo fundo inicial..."):
        img_rgba = remove(img_original)
        arr_rgba = np.array(img_rgba)

    st.markdown("### 🧼 Ajuste Manual: Remova o bolo apagando imperfeições")
    st.write("Use o controle abaixo se o bolo ou rebarbas de palito continuarem aparecendo no resultado.")

    # Cria um limitador de altura simples: tudo abaixo desse corte vira transparente (remove o bolo de vez)
    linha_corte = st.slider("📏 Linha Limite do Bolo (Cortar base inferior da imagem)", min_value=30, max_value=100, value=75, help="Arraste para a esquerda para apagar o bolo de baixo para cima.")
    
    # Aplica o corte geométrico instantâneo na matriz alfa
    limite_pixel = int(h * (linha_corte / 100.0))
    arr_rgba[limite_pixel:, :, 3] = 0
    img_rgba_limpa = Image.fromarray(arr_rgba)

    st.image(img_rgba_limpa, caption="Visualização dos Apliques Isolados (Área transparente oculta o bolo)", width=350)

    if st.button("✂️ Gerar Folha de Impressão e Vetor DXF", use_container_width=True):
        folha_elementos, folha_mascara = executar_fluxo_papelaria(img_rgba_limpa, w, h)
        
        if folha_elementos is None:
            st.error("Nenhum elemento foi detectado acima da linha limite. Ajuste o slider para cima!")
            return

        folha_corte_gray = cv2.cvtColor(np.array(folha_mascara), cv2.COLOR_RGB2GRAY)
        bytes_dxf = exportar_contornos_para_dxf(folha_corte_gray)

        st.success("🎉 Arquivos processados com sucesso!")
        
        col_c, col_m = st.columns(2)
        with col_c:
            st.markdown("<div class='result-wrap'><h4>🖼️ Folha de Impressão (Borda Branca)</h4>", unsafe_allow_html=True)
            st.image(folha_elementos, use_container_width=True)
            st.download_button("💾 Baixar PNG", data=imagem_para_bytes(folha_elementos), file_name="folha_impressao.png", mime="image/png")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_m:
            st.markdown("<div class='result-wrap'><h4>📐 Vetor para Silhouette Studio</h4>", unsafe_allow_html=True)
            st.image(folha_mascara, use_container_width=True)
            st.download_button("📐 Baixar DXF", data=bytes_dxf, file_name="corte_silhouette.dxf", mime="application/dxf")
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
