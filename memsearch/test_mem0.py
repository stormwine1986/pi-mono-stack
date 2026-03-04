
import sys
import os
sys.path.append("/app")
from mem0_client import memory_client

user_id = "7722403902"
agent_id = "0"
prompt = "My favorite color is blue."
response = "I will remember that your favorite color is blue."

print(f"Adding memory for {user_id}...")
memory_client.add_interaction(user_id, agent_id, prompt, response)

print(f"Retrieving memories for {user_id}...")
memories = memory_client.get_all(user_id)
print(f"Raw memories: {memories}")

search_res = memory_client.search("favorite color", user_id)
print(f"Search results: {search_res}")
