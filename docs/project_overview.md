# Loops Moderation System: Architecture & Workflow Overview

This document provides a comprehensive overview of the `Loops Moderation System`, explaining the core workflow, the moderation pipeline, and the resource utilization (CPU and Memory) of the integrated Machine Learning models.

---

## 1. System Functionality & Workflow

The architecture operates as a robust multi-layered filtering system ensuring compliance with community guidelines. Every submission passes through an sequential pipeline that analyzes intent, toxicity, visual content, and technical relevance.

### Overall Pipeline Workflow

1. **Input Reception (`moderation_service.py`)**  
   The system accepts text and/or base64 encoded images.
2. **Text Normalization (`preprocessing.py` & `text_normalizer.py`)**  
   Text is stripped of obscuring characters, leetspeak, disguised URLs, and normalized (lowercased, repetitive chars squeezed) for optimal ML inspection.
3. **Rule-Based Engine (`rule_engine.py`)**  
   - Runs deterministic checks: keyword matching, regular expressions for spam/scams/URLs, and calculates a base `tech_relevance_score`.
   - **Content Mixing Check:** Slices the text into sentences to detect whether users are trying to bypass the filter by appending technical words to otherwise abusive text.

4. **Advanced ML Text Analysis**  
   If text is present, it flows into:
   - **Ensemble Moderator (`multitask_model.py`)**: Uses HuggingFace transformers (`unitary/toxic-bert` & `dehatebert`) to flag hate speech, toxicity, and threats.
   - **Intent Entity Filter (`intent_entity_filter.py`)**: Uses `spaCy` (NER and dependency parsing) alongside complex pattern matching to detect severe risks like "Credential Theft" or "Malware deployment instructions."
   - **Tech Context Filter (`tech_context_filter.py`)**: For borderline texts, evaluates zero-shot probabilities via the `nli-deberta-v3-base` model to distinguish actual tech tutorials from malicious guides.

5. **Image Processing (If applicable)**  
   - **NSFW Detection**: Uses `nsfw_image_detection` (Vision Transformer) to scan for sexually explicit imagery.
   - **Tech Image Relevance**: Uses `OpenAI CLIP` to map the image contents against tech-related concepts. If the image is highly technical, strict tech-text rules are relaxed.

6. **Decision Engine (`decision_engine.py`)**  
   Aggregates flags and scores from all the components above to issue a final verdict `(ALLOW or BLOCK)`. This layer enforces strict priorities (e.g., blocking Hate Speech takes absolute precedence over off-topic failures).

7. **Explanation Building (`explanation_builder.py`)**  
   Formats the discrete rejection codes into user-friendly textual explanations (e.g., translating `cyber_harm_intent` to "Contains instructions on exploiting vulnerabilities").

---

## 2. Machine Learning Models Summary

The system orchestrates *five* deep learning models and *one* traditional NLP linguistic model. Because loading ML models is highly resource-intensive, the system utilizes a **Lazy Loading Singleton (`model_loader.py`)** to guarantee each model only consumes memory when strictly needed and initializes exactly once per worker process.

| Component | Model Hub Identifier | Architecture / Type | Purpose | Size |
| :--- | :--- | :--- | :--- | :--- |
| **Toxicity** | `unitary/toxic-bert` | BERT (110M params) | Multi-label toxicity and threat checking. | ~420 MB |
| **Hate Speech** | `Hate-speech-CNERG/dehatebert` | BERT (110M params) | Dedicated hate speech validation. | ~420 MB |
| **Tech/Malware Context** | `cross-encoder/nli-deberta-v3-base` | DeBERTa V3 (86M params) | Distinguishes deep tech context from cyber-harm instructions via NLI. | ~350 MB |
| **Tech Visuals** | `openai/clip-vit-base-patch32` | CLIP / ViT (~150M params) | Determines if an image depicts a technical environment or concept. | ~600 MB |
| **Visual NSFW** | `Falconsai/nsfw_image_detection` | ViT (86M params) | Traps sexually explicit or inappropriate graphics. | ~340 MB |
| **Linguistics & NER** | `spacy: en_core_web_sm` | CNN (Trigram) | Maps verbs/nouns for complex cyber threat intents. | ~15 MB |

---

## 3. CPU Usage & Resource Footprint

### Memory Consumption (RAM)
When the application first boots, memory usage is relatively low (~200MB). However, as live traffic strikes the various capabilities (text toxicity, visual scanning, zero-shot classification), the cache initializes these weights into active memory. 
* **Peak Footprint:** Once all vision and transformer models are loaded into the standard pipeline, expect the Python process to occupy **~2.2 GB up to ~2.6 GB** of system RAM. 

### Processor Utilization (CPU)
Machine learning inference requires massive mathematical matrix multiplications. 
* **If running entirely on CPU:** You will notice brief, intense **100% CPU thread utilization** during inference peaks. 
  * Running a standard text string through both `toxic-bert` and `DeBERTa` requires between **50ms - 200ms** depending on server clock speed.
  * Running `OpenAI CLIP` and `ViT NSFW` on a single image is mathematically heavy and can take between **200ms - 600ms** on CPU.
* **If running on GPU (CUDA):** `model_loader.py` actively looks for `torch.cuda.is_available()`. If a discrete GPU is found, calculations shift to VRAM, reducing host CPU usage during inference close to zero, and reducing inference times to under **15ms**.

### Scaling Strategies
If CPU usage causes the server to drag or time-out under load, the recommended strategies are:
1. Increase worker parallelism cautiously (e.g., using `uvicorn --workers 2`), ensuring server RAM allows `2.5GB * Workers`.
2. Move to a GPU-backed cloud instance (e.g., AWS `g4dn.xlarge` or minimal Nvidia T4), which will effortlessly handle concurrent loads for this specific model stack.
3. Fallback Mechanism: `multitask_model.py` ships with a `FallbackModerator`. During catastrophic memory limits, you can bypass huge transformers and route through lightweight Regex and strict keywords to maintain 0% CPU overhead while resolving infrastructure issues.
