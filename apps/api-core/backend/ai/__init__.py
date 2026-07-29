"""
Módulos de IA ligeros para Orion POS v3.

Submódulos:
    - stockout_forecast: Random Forest para predecir quiebre de stock.
    - ocr_invoice:       OCR de facturas (Tesseract + parser).
    - nlp_assistant:     Asistente contextual (RAG + gpt-4o-mini opcional).

Todos los módulos importan dependencias opcionales con `try/except` para que
el web service principal arranque aunque las libs de IA no estén instaladas.
Las dependencias viven en `requirements-ml.txt` y se instalan en el cron worker.

Documentación: docs/AI_MODULES.md
"""
