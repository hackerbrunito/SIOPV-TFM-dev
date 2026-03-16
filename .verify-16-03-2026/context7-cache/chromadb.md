# ChromaDB — Context7 Cache

## Current Version: chromadb 0.5+

## Key API Patterns

### Client Setup
- `import chromadb`
- `client = chromadb.PersistentClient(path="./chroma_db")` — persistent storage
- `client = chromadb.HttpClient(host="localhost", port=8000)` — server mode
- `client = chromadb.EphemeralClient()` — in-memory (testing only)

### Collections
- `collection = client.get_or_create_collection("name", metadata={"hnsw:space": "cosine"})`
- `client.get_collection("name")` — get existing
- `client.delete_collection("name")` — delete

### CRUD Operations
```python
collection.add(
    ids=["id1", "id2"],
    documents=["text1", "text2"],
    metadatas=[{"source": "nvd"}, {"source": "epss"}],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],  # optional if using embedding function
)
results = collection.query(
    query_texts=["search query"],
    n_results=10,
    where={"source": "nvd"},
)
collection.update(ids=["id1"], documents=["updated text"])
collection.delete(ids=["id1"])
```

### Query Results
- `results["ids"]` — list of id lists
- `results["documents"]` — list of document lists
- `results["distances"]` — list of distance lists
- `results["metadatas"]` — list of metadata lists

### Best Practices
- Use `PersistentClient` for production (data survives restarts)
- Use `get_or_create_collection` for idempotent initialization
- Set `hnsw:space` to match your similarity metric (cosine, l2, ip)
- Use metadata filters in `where` clause for efficient filtering
