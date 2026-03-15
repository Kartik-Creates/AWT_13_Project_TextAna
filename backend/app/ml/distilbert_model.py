"""
Backward-compatible shim for the old DistilBERT analyzer.

The project has migrated to XLM-RoBERTa for toxicity detection. To avoid
breaking older imports, this module simply re-exports the new analyzer
under the previous names.
"""

from .roberta_model import RobertaAnalyzer, roberta_analyzer

DistilBERTAnalyzer = RobertaAnalyzer  # type: ignore
distilbert_analyzer = roberta_analyzer