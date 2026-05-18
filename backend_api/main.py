import base64
import io
import logging
import os
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("topo_api")

app = FastAPI(
    title="Personalizados da Rô API",
    description="Servidor backend para processar imagens com Gemini e gerar topofolhas para o app móvel.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_IMAGE_DIMENSION = 1536
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
DEFAULT_API_KEY = os.environ.get("GEMINI_API_KEY", "")


class ProcessResponse(BaseModel):
    description: str
    image_color_base64: str
    mask_image_base64: str


def validate_upload(filename: str) -> None:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Formato não suportado. Envie PNG, JPG ou WEBP.")


def resize_image(img: Image.Image) -> Image.Image:
    w, h = img.size
    if max(w, h) <= MAX_IMAGE_DIMENSION:
        return img
    scale = MAX_IMAGE_DIMENSION / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def get_client(api_key: str):
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key do Gemini não informada.")
    return genai.Client(api_key=api_key)


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


def image_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _extract_text_from_response(result) -> str:
    if hasattr(result, "text") and result.text:
        return str(result.text).strip()
    if hasattr(result, "output_text") and result.output_text:
        return str(result.output_text).strip()
    if hasattr(result, "output") and result.output:
        return str(result.output).strip()
    for part in getattr(result, "parts", []):
        if isinstance(part, str):
            return part.strip()
        if hasattr(part, "text") and part.text:
            return str(part.text).strip()
        if hasattr(part, "output_text") and part.output_text:
            return str(part.output_text).strip()
    return ""


def generate_description(client, image: Image.Image) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Você é um assistente especializado em identificar apenas os elementos de topo do bolo. Ignore o bolo, o fundo, velas, suporte e outras decorações não relacionadas ao topo. Responda em inglês com uma descrição clara dos elementos a serem recriados em um layout de corte.",
            image,
        ],
    )
    description = _extract_text_from_response(response)
    if not description:
        logger.warning("Gemini returned an empty description response: %s", repr(response))
        raise HTTPException(status_code=502, detail="Gemini não retornou descrição válida.")
    return description


def generate_topo_image(client, description: str, image: Image.Image) -> Image.Image:
    prompt = f"A printable sheet for cake toppers and scrapbooking paper crafts. The sheet must contain exactly these elements: {description}. The result must use a pure white background (#FFFFFF), no shadows, no gradients, and each object must be isolated, non-overlapping, and easy to cut. Rendering: flat vector-style illustration, cute children theme, bright saturated colors, crisp edges, strong contrast, clean shapes for silhouette cutting."
    config = types.GenerateContentConfig(response_modalities=["IMAGE"])
    result = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt, image],
        config=config,
    )
    for part in getattr(result, "parts", []):
        img = _extract_image_from_part(part)
        if isinstance(img, Image.Image):
            return img.convert("RGB")
    image_candidate = _extract_image_from_part(result)
    if isinstance(image_candidate, Image.Image):
        return image_candidate.convert("RGB")
    logger.warning("Nenhuma imagem encontrada no resultado do Gemini: %s", repr(result))
    raise HTTPException(status_code=502, detail="Gemini não retornou imagem válida.")


def generate_mask(img: Image.Image, min_area: int = 200) -> Image.Image:
    img_cv = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    lower = np.array([220, 220, 220], dtype=np.uint8)
    upper = np.array([255, 255, 255], dtype=np.uint8)
    fg = cv2.bitwise_not(cv2.inRange(img_cv, lower, upper))
    k_close = np.ones((5, 5), np.uint8)
    k_open = np.ones((3, 3), np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k_close, iterations=2)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, k_open, iterations=1)
    contornos, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    h, w = fg.shape
    mask = np.full((h, w), 255, dtype=np.uint8)
    for c in contornos:
        if cv2.contourArea(c) < min_area:
            continue
        eps = 0.001 * cv2.arcLength(c, True)
        cs = cv2.approxPolyDP(c, eps, True)
        cv2.drawContours(mask, [cs], -1, 0, thickness=cv2.FILLED)
    mask = cv2.bitwise_not(cv2.dilate(cv2.bitwise_not(mask), np.ones((3, 3), np.uint8), iterations=2))
    return Image.fromarray(mask).convert("RGB")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process", response_model=ProcessResponse)
async def process_image(file: UploadFile = File(...), api_key: Optional[str] = Form(None)):
    validate_upload(file.filename)
    key = api_key.strip() if api_key else DEFAULT_API_KEY
    if not key:
        raise HTTPException(status_code=400, detail="A variável GEMINI_API_KEY não está definida no servidor e nenhuma chave foi enviada.")

    content = await file.read()
    try:
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Não foi possível abrir a imagem: {exc}")

    image = resize_image(image)
    client = get_client(key)

    description = generate_description(client, image)
    topo_image = generate_topo_image(client, description, image)
    mask_image = generate_mask(topo_image)

    return ProcessResponse(
        description=description,
        image_color_base64=image_to_base64(topo_image),
        mask_image_base64=image_to_base64(mask_image),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
