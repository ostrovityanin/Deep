"""
DeepGaze III Heatmap API — для Timeweb App Platform (Flask)
"""
import io
import base64
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS

import torch
import deepgaze_pytorch
from scipy.ndimage import zoom as scipy_zoom
from scipy.special import logsumexp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)
CORS(app)

# Загрузка модели при старте
DEVICE = "cpu"
model = deepgaze_pytorch.DeepGazeIII(pretrained=True).to(DEVICE)
model.eval()

# Центральная фиксация
centerbias_template = np.zeros((1024, 1024))


def make_heatmap(image_pil, alpha=0.5):
    """Генерирует heatmap и overlay"""
    img = np.array(image_pil.convert("RGB"))
    h, w = img.shape[:2]

    # Resize для модели (макс 1024)
    scale = min(1.0, 1024 / max(h, w))
    new_h, new_w = int(h * scale), int(w * scale)

    img_resized = np.array(image_pil.resize((new_w, new_h), Image.LANCZOS).convert("RGB"))
    img_tensor = torch.tensor(img_resized.transpose(2, 0, 1)[np.newaxis], dtype=torch.float32).to(DEVICE)

    centerbias = scipy_zoom(centerbias_template, (new_h / 1024, new_w / 1024), order=0, mode="nearest")
    centerbias -= logsumexp(centerbias)
    centerbias_tensor = torch.tensor(centerbias[np.newaxis, np.newaxis], dtype=torch.float32).to(DEVICE)

    with torch.no_grad():
        log_density = model(img_tensor, centerbias_tensor)

    prediction = log_density.squeeze().cpu().numpy()
    prediction = np.exp(prediction)
    prediction = prediction / prediction.max()

    # Масштабируем обратно
    prediction_full = scipy_zoom(prediction, (h / new_h, w / new_w), order=1, mode="nearest")

    # Heatmap
    fig, ax = plt.subplots(1, 1, figsize=(w / 100, h / 100), dpi=100)
    ax.imshow(prediction_full, cmap="jet", vmin=0, vmax=1)
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    buf_heatmap = io.BytesIO()
    fig.savefig(buf_heatmap, format="png", bbox_inches="tight", pad_inches=0, dpi=100)
    plt.close(fig)
    buf_heatmap.seek(0)

    # Overlay
    fig2, ax2 = plt.subplots(1, 1, figsize=(w / 100, h / 100), dpi=100)
    ax2.imshow(img)
    ax2.imshow(prediction_full, cmap="jet", alpha=alpha, vmin=0, vmax=1)
    ax2.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    buf_overlay = io.BytesIO()
    fig2.savefig(buf_overlay, format="png", bbox_inches="tight", pad_inches=0, dpi=100)
    plt.close(fig2)
    buf_overlay.seek(0)

    return buf_heatmap, buf_overlay


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    alpha = float(request.form.get("alpha", 0.5))

    try:
        image = Image.open(file.stream)
    except Exception:
        return jsonify({"error": "Invalid image"}), 400

    try:
        buf_heatmap, buf_overlay = make_heatmap(image, alpha)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    heatmap_b64 = base64.b64encode(buf_heatmap.read()).decode()
    overlay_b64 = base64.b64encode(buf_overlay.read()).decode()

    return jsonify({
        "heatmap": heatmap_b64,
        "overlay": overlay_b64,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
