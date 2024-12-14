import sys
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

def predict(texts, model_path="./steam-reviews/tasks/hate_speech_model"):
    model_path = os.path.abspath(model_path)
    
    # 모델과 토크나이저 로드
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    encodings = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors="pt"
    )
    with torch.no_grad():
        outputs = model(
            input_ids=encodings["input_ids"],
            attention_mask=encodings["attention_mask"]
        )
    probabilities = torch.softmax(outputs.logits, dim=-1).numpy()

    results = [{"label": prob.argmax(), "probability": max(prob)} for prob in probabilities]
    return results


if __name__ == "__main__":
    texts = sys.argv[1:]
    predictions = predict(texts)
    print(predictions)
