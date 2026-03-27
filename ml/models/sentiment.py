"""
ml/models/sentiment.py — Sentiment scoring using finBERT.
Pre-trained on financial text, maps news headlines to -1.0 to 1.0.
"""
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from loguru import logger


class SentimentScorer:
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"[sentiment] Loading {model_name} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def score_text(self, text: str) -> Dict[str, float]:
        """
        Score a single headline/summary.
        Returns: {label: str, score: float, compound: float}
        finBERT output: [positive, negative, neutral]
        """
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = torch.nn.functional.softmax(outputs.logits, dim=-1)

        pos, neg, neu = scores[0].cpu().numpy()

        # Compound score: pos - neg (simple version)
        compound = float(pos - neg)

        labels = ["positive", "negative", "neutral"]
        best_label = labels[int(torch.argmax(scores))]

        return {
            "label":    best_label,
            "score":    float(torch.max(scores)),
            "compound": compound,
        }

    def score_batch(self, texts: List[str]) -> List[float]:
        """Return list of compound scores for a batch of texts."""
        if not texts:
            return []
        inputs = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # compound = positive - negative
        scores = scores.cpu().numpy()
        return [float(s[0] - s[1]) for s in scores]
