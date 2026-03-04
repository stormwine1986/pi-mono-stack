
from flask import Flask, request, jsonify
import requests
import json
import logging

app = Flask(__name__)

TARGET_URL = "http://127.0.0.1:18080/v1"
LOG_FILE = "/data/llm_proxy.log"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(message)s')

@app.route('/v1/chat/completions', methods=['POST'])
def chat_proxy():
    logging.info("--- INCOMING CHAT PROMPT ---")
    logging.info(json.dumps(request.json, indent=2))
    logging.info("--------------------------")
    
    # Forward to real llama-server
    resp = requests.post(f"{TARGET_URL}/chat/completions", json=request.json)
    
    logging.info("--- RESPONSE FROM LLM ---")
    data = resp.json()
    logging.info(json.dumps(data, indent=2))
    logging.info("--------------------------")
    
    return jsonify(data)

@app.route('/v1/embeddings', methods=['POST'])
def embed_proxy():
    # Forward embeddings as well
    resp = requests.post(f"http://127.0.0.1:18081/v1/embeddings", json=request.json)
    return jsonify(resp.json())

if __name__ == "__main__":
    app.run(port=18082, host='0.0.0.0')
