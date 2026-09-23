# Copyright 2026 Google LLC
# Setup script for serverless Vertex AI RAG Corpus

import time
import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-01-0482b2deb94b"
LOCATION = "us-central1"
GCS_PATH = "gs://work-planner-assets-qwiklabs-gcp-01-0482b2deb94b/rag/chicken_salad_recipe.txt"

PARSING_PROMPT = (
    "Extract all ingredients, step-by-step instructions, serving options, and nutritional macros from this recipe."
)

def main():
    print(f"Initializing Vertex AI (Project: {PROJECT_ID}, Location: {LOCATION})...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    try:
        print("Configuring RAG Engine mode to Serverless...")
        rag.update_rag_engine_config(
            rag_engine_config=rag.RagEngineConfig(
                name=cfg,
                rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
            )
        )
    except Exception as e:
        print(f"RAG Engine Config Note: {e}")

    print("Creating RAG Corpus...")
    corpus = rag.create_corpus(
        display_name="chicken-salad-recipe-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    print(f"✅ RAG Corpus Created: {corpus.name}")

    print(f"Importing and indexing {GCS_PATH} into corpus...")
    resp = rag.import_files(
        corpus_name=corpus.name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-2.5-flash",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"✅ File imported successfully! Imported count: {getattr(resp, 'imported_rag_files_count', 1)}")
    
    # Save Corpus Name for agent reference
    with open("rag_corpus_name.txt", "w") as f:
        f.write(corpus.name)
    print(f"Saved Corpus ID to rag_corpus_name.txt")

if __name__ == "__main__":
    main()
