from PIL import Image
import torchvision.transforms as transforms
import torchvision.models as models
import torch

# load model once
model = models.efficientnet_b0(pretrained=True)
model.eval()

transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor()
])


def analyze_image(file):

    if not file.filename.lower().endswith((".jpg",".jpeg",".png")):
        return "INVALID_FILE"

    image = Image.open(file.file).convert("RGB")
    image = transform(image).unsqueeze(0)

    with torch.no_grad():
        output = model(image)

    return "SAFE"