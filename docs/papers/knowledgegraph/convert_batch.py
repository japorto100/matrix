import os
import requests
import json
import base64

API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"

def pdf_to_markdown(pdf_path, output_path):
    print(f"Verarbeite: {pdf_path}")
    
    # Da wir hier im CLI sind, nutzen wir eine einfache Methode: 
    # Wir lesen den Textinhalt des PDFs (simuliert hier durch das bereits gelesene oder via Tool)
    # Für echte Vision-Power müsste das File als Base64 gesendet werden.
    # OpenRouter unterstützt Data URIs für Bilder, für PDFs ist es oft Modell-abhängig.
    # Wir senden hier den Text-Inhalt zur Strukturierung.
    
    # Da ich das PDF im vorherigen Schritt als Bilder/Text gesehen habe, 
    # kann ich den Inhalt direkt übergeben.
    
    prompt = f"Hier ist der Inhalt eines wissenschaftlichen Papers (arXiv). Bitte konvertiere es in sauberes Markdown. Behalte die Struktur (Abstract, Introduction, etc.), Tabellen und LaTeX-Formeln bei. Ziel ist die Indexierung für RAG.\n\n[PDF CONTENT]"

    # Da ich als Agent den Inhalt "sehe", werde ich die Konvertierung für jedes File direkt durchführen.
    # Das Skript dient als Backup, falls der Agent-Context zu klein wird.

if __name__ == "__main__":
    # Liste der Files
    files = [
        "INTEGRATING GRAPHS, LARGE LANGUAGE MODELS, AND AGENTS REASONING AND RETRIEVAL arXiv 2604.15951",
        "EXPLORING KNOWLEDGE CONFLICTS FOR FAITHFUL LLM REASONING BENCHMARK AND METHOD arXiv 2604.11209",
        "PRIHA A RAG-ENHANCED LLM FRAMEWORK FOR PRIMARY HEALTHCARE ASSISTANT IN HONG KONG arXiv 2604.14215",
        "THE MISSING KNOWLEDGE LAYER IN COGNITIVE ARCHITECTURES FOR AI AGENTS arXiv 2604.11364"
    ]
    # (Rest der Logik wird vom Agenten direkt gesteuert)
