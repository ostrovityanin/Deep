import os
import io
import base64
import logging

import numpy as np
import torch
from scipy.ndimage import zoom
from scipy.special import logsumexp
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DEVICE = torch.device("cpu")
model = None


def load_model():
    global model
    if model is not None:
        return
    logger.info("Loading DeepGaze IIE model (CPU)...")
    from deepgaze_pytorch import DeepGazeIIE
    model = DeepGazeIIE(pretrained=True).to(DEVICE)
    model.eval()
    logger.info("Model loaded successfully.")


def make_centerbias(shape, sigma_frac=0.4):
    h, w = shape
    y = np.linspace(-1, 1, h)
    x = np.linspace(-1, 1, w)
    X, Y = np.meshgrid(x, y)
    centerbias = np.exp(-0.5 * (X**2 + Y**2) / sigma_frac**2)
    centerbias /= centerbias.sum()
    return np.log(centerbias)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None})


@app.route("/predict", methods=["POST"])
def predict():
    load_model()

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    alpha = float(request.form.get("alpha", 0.5))
    file = request.files["image"]
    img = Image.open(file.stream).convert("RGB")
    original_size = img.size  # (W, H)

    # Resize for inference
    input_size = (768, 1024)
    img_resized = img.resize((input_size[1], input_size[0]), Image.BILINEAR)
    img_np = np.array(img_resized).astype(np.float32)

    tensor = torch.tensor(img_np.transpose(2, 0, 1)[np.newaxis, ...]).to(DEVICE)
    centerbias_tensor = torch.tensor(
        make_centerbias(input_size)[np.newaxis, np.newaxis, ...]
    ).float().to(DEVICE)

    with torch.no_grad():
        log_density = model(tensor, centerbias_tensor)

    log_density_np = log_density.cpu().numpy()[0, 0]
    # Resize back to original
    scale_h = original_size[1] / log_density_np.shape[0]
    scale_w = original_size[0] / log_density_np.shape[1]
    log_density_full = zoom(log_density_np, (scale_h, scale_w), order=1)
    log_density_full -= logsumexp(log_density_full)
    heatmap = np.exp(log_density_full)

    # Heatmap image
    fig, ax = plt.subplots(figsize=(original_size[0] / 100, original_size[1] / 100), dpi=100)
    ax.imshow(heatmap, cmap="inferno")
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    buf_h = io.BytesIO()
    fig.savefig(buf_h, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf_h.seek(0)
    heatmap_b64 = base64.b64encode(buf_h.read()).decode()

    # Overlay image
    fig, ax = plt.subplots(figsize=(original_size[0] / 100, original_size[1] / 100), dpi=100)
    ax.imshow(np.array(img))
    ax.imshow(heatmap, cmap="inferno", alpha=alpha)
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    buf_o = io.BytesIO()
    fig.savefig(buf_o, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf_o.seek(0)
    overlay_b64 = base64.b64encode(buf_o.read()).decode()

    return jsonify({"heatmap": heatmap_b64, "overlay": overlay_b64})


if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
