from transformers import pipeline

classifier = None

def load_model():
    global classifier
    classifier = pipeline("sentiment-analysis")

def analyze_text(text: str):

    result = classifier(text)[0]

    label = result["label"]
    score = result["score"]

    if label == "NEGATIVE" and score > 0.8:
        return "BLOCK"

    if label == "NEGATIVE":
        return "FLAG"

    return "ALLOW"

# following is decision logic

def decision_engine(text_result, image_result="SAFE"):

    if text_result == "BLOCK":
        return "BLOCK"

    if text_result == "FLAG":
        return "FLAG"

    if image_result == "BLOCK":
        return "BLOCK"

    return "ALLOW"
