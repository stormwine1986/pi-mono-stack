
import chromadb
client = chromadb.PersistentClient(path="/data/chroma_db")
print(f"Collections: {client.list_collections()}")
for col in client.list_collections():
    c = client.get_collection(col.name)
    print(f"Collection {col.name} count: {c.count()}")
    print(f"Collection {col.name} peek: {c.peek(limit=5)}")
