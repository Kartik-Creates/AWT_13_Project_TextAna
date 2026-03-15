from transformers import CLIPProcessor, CLIPModel
from PIL import Image

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


def analyze_multimodal(text, image_file):

    image = Image.open(image_file.file).convert("RGB")

    inputs = processor(text=[text], images=image, return_tensors="pt", padding=True)

    outputs = model(**inputs)

    similarity = outputs.logits_per_image.item()

    if similarity < 10:
        return "MISMATCH"

    return "MATCH"