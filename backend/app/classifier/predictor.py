"""
backend/app/classifier/predictor.py

Singleton predictor for ConvNeXt document layout classification.
Loads classifier.pt once, exposes predict(image_bytes) -> PredictionOut
and predict_topk(image_bytes, k) -> list[tuple[str, float]].
CPU-only, p95 < 1.0s on modern laptop hardware.
"""
import io
import time
from pathlib import Path

import structlog
import torch
import torch.nn as nn
import torchvision.transforms as T  # noqa: N812
from PIL import Image

# ------------------------------------------------------------------
# Pydantic schema (temporary – will move to app/domain/contracts.py
# once M2 commits it. The real one will be identical in shape.)
# ------------------------------------------------------------------
from pydantic import BaseModel, Field


class PredictionOut(BaseModel):
    label: str = Field(..., description="Predicted layout class, one of 16 RVL-CDIP classes")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Softmax confidence for the predicted label"
    )
    latency_ms: float | None = Field(None, description="Inference time in milliseconds")

# ------------------------------------------------------------------
# Module-level constants (derived from training; keep in sync with
# the model card and training transforms)
# ------------------------------------------------------------------
IMAGE_SIZE = 384
MEAN = [0.485, 0.456, 0.406]
STD  = [0.229, 0.224, 0.225]

# The 16 classes in the order they appear in the torchvision ImageFolder
# during training. Must match exactly the class_to_idx from the dataset.
CLASSES = [
    "letter", "form", "email", "handwritten", "advertisement",
    "scientific report", "scientific publication", "specification",
    "file folder", "news article", "budget", "invoice",
    "presentation", "questionnaire", "resume", "memo"
]

# ------------------------------------------------------------------
# Predictor singleton
# ------------------------------------------------------------------
class Predictor:
    """
    Loads the ConvNeXt weights once and exposes a CPU-based prediction
    method. The constructor is private – use get_predictor() to obtain
    the process-wide singleton.
    """
    def __init__(self, weights_path: Path) -> None:
        self.weights_path = weights_path
        self._model: nn.Module | None = None
        self._transform = self._build_transform()
        self._load_model()

    def _build_transform(self) -> T.Compose:
        """Deterministic evaluation transform: grayscale → RGB → resize → normalize."""
        return T.Compose([
            T.Grayscale(3),                          # single-channel TIFF → 3 channels
            T.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            T.ToTensor(),
            T.Normalize(mean=MEAN, std=STD),
        ])

    def _load_model(self) -> None:
        """Instantiate the same backbone architecture and load saved state_dict."""
        from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny

        log = structlog.get_logger()
        log.info("predictor.loading_weights", path=str(self.weights_path))

        # Recreate the exact model used in training (ConvNeXt Tiny by default)
        model = convnext_tiny(weights=ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
        in_features = model.classifier[2].in_features
        model.classifier[2] = nn.Linear(in_features, len(CLASSES))

        state = torch.load(self.weights_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        self._model = model

    def predict(self, image_bytes: bytes) -> PredictionOut:
        """
        Run inference on raw TIFF bytes and return a structured prediction.

        Args:
            image_bytes: Raw bytes of a grayscale TIFF image.

        Returns:
            PredictionOut containing predicted label and confidence.

        Raises:
            RuntimeError: if model not loaded (shouldn't happen after init).
            PIL.UnidentifiedImageError: if bytes are not a valid image.
        """
        if self._model is None:
            raise RuntimeError("Predictor model not loaded – call _load_model first")

        log = structlog.get_logger()

        # Decode and preprocess
        img = Image.open(io.BytesIO(image_bytes)).convert("L")   # ensure grayscale
        tensor = self._transform(img).unsqueeze(0)                # add batch dim

        # Inference (no gradients, more efficient than no_grad)
        start_time = time.perf_counter()
        with torch.inference_mode():
            output = self._model(tensor)
            probs = torch.softmax(output, dim=1)
            conf, idx = torch.max(probs, dim=1)
        latency_ms = (time.perf_counter() - start_time) * 1000

        label = CLASSES[idx.item()]
        confidence = round(conf.item(), 10)   # high precision for golden-set comparison

        log.info("predictor.inference", label=label, confidence=confidence, latency_ms=latency_ms)
        return PredictionOut(label=label, confidence=confidence, latency_ms=latency_ms)

    # ------------------------------------------------------------------
    # NEW METHOD – for top‑5 in the worker (does NOT affect golden tests)
    # ------------------------------------------------------------------
    def predict_topk(self, image_bytes: bytes, k: int = 5) -> tuple[list[tuple[str, float]], float]:
        """Return top‑k labels and confidences (used by the worker for top‑5)."""
        if self._model is None:
            raise RuntimeError("Model not loaded")

        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        tensor = self._transform(img).unsqueeze(0)

        start_time = time.perf_counter()
        with torch.inference_mode():
            output = self._model(tensor)
            probs = torch.softmax(output, dim=1)
            topk_conf, topk_idx = torch.topk(probs, k, dim=1)
        latency_ms = (time.perf_counter() - start_time) * 1000

        results = []
        for i in range(k):
            label = CLASSES[topk_idx[0, i].item()]
            conf = round(topk_conf[0, i].item(), 10)
            results.append((label, conf))

        log = structlog.get_logger()
        log.info("predictor.inference_topk", top1_label=results[0][0], top1_conf=results[0][1], latency_ms=latency_ms)
        return results, latency_ms


# ------------------------------------------------------------------
# Singleton loader – called by FastAPI lifespan or worker entrypoint
# ------------------------------------------------------------------
_predictor_singleton: Predictor | None = None

def get_predictor(weights_path: Path | None = None) -> Predictor:
    """
    Return the process-wide Predictor singleton. Weights are loaded only once.
    If weights_path is provided on the first call, it is used; subsequent calls
    ignore it (the singleton is immutable).

    Typical usage:
        from app.classifier.predictor import get_predictor
        predictor = get_predictor(Path("app/classifier/models/classifier.pt"))
    """
    global _predictor_singleton
    if _predictor_singleton is None:
        if weights_path is None:
            # Default path inside the project (docker-compose mounts at /app)
            weights_path = Path(__file__).resolve().parent / "models" / "classifier.pt"
        _predictor_singleton = Predictor(weights_path)
    return _predictor_singleton
