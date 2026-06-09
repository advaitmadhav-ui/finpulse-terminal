# src/processing/sentiment_analyzer.py
import sqlite3
import threading
import os
import sys
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import DB_PATH

# Thread safety lock for resource-heavy transformer inferences
MODEL_LOCK = threading.Lock()

class FinBertAnalyzer:
    def __init__(self):
        print("🧠 Loading FinBERT Transformer model into memory...")
        self.model_name = "ProsusAI/finbert"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        
        # Use GPU execution if a CUDA environment is available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"✅ Model loaded successfully on device: {self.device}")

    def compute_sentiment_float(self, headline: str) -> float:
        """Processes text and returns a continuous floating point score between -1.0 and 1.0."""
        with MODEL_LOCK:
            inputs = self.tokenizer(headline, padding=True, truncation=True, max_length=512, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Extract softmax probabilities
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            
            # FinBERT label layout: [Positive, Negative, Neutral]
            pos_prob = float(probs[0])
            neg_prob = float(probs[1])
            neutral_prob = float(probs[2])
            
            # Calculate a continuous net sentiment float score mapping to [-1.0, 1.0]
            # Higher probability intensities pull the float closer to their absolute boundaries
            net_score = pos_prob - neg_prob
            return round(net_score, 4)

def process_pending_news():
    """Queries database for unprocessed headlines and appends calculated float scores."""
    analyzer = FinBertAnalyzer()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, headline FROM raw_news WHERE sentiment_score IS NULL")
    pending_items = cursor.fetchall()
    
    if not pending_items:
        print("⚪ No pending headlines require sentiment evaluation.")
        conn.close()
        return

    print(f"⚡ Found {len(pending_items)} headlines awaiting evaluation...")
    
    updated_count = 0
    for news_id, headline in pending_items:
        score = analyzer.compute_sentiment_float(headline)
        cursor.execute("UPDATE raw_news SET sentiment_score = ? WHERE id = ?", (score, news_id))
        updated_count += 1

    conn.commit()
    conn.close()
    print(f"💾 Analysis complete. Updated {updated_count} news scores in the database.")

if __name__ == "__main__":
    process_pending_news()