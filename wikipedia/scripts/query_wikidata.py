import sys
import json
import urllib.request
import urllib.parse

API_ENDPOINT = "https://www.wikidata.org/w/api.php"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "Gemini-CLI-Wikidata-Skill/1.0 (https://github.com/google/gemini-cli)"

def make_request(params):
    query_string = urllib.parse.urlencode(params)
    url = f"{API_ENDPOINT}?{query_string}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    
    with urllib.request.urlopen(req) as response:
        if response.status != 200:
            raise Exception(f"HTTP error! status: {response.status}")
        return json.loads(response.read().decode())

def execute_sparql(query):
    params = {
        "query": query,
        "format": "json"
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{SPARQL_ENDPOINT}?{query_string}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                raise Exception(f"HTTP error! status: {response.status}")
            data = json.loads(response.read().decode())
            
            vars_ = data["head"]["vars"]
            results = data["results"]["bindings"]
            
            print(f"Found {len(results)} results:\n")
            
            if len(results) > 0:
                # Print header
                print(" | ".join(vars_))
                print("-" * (len(" | ".join(vars_)) + 5))
                
                # Print rows
                for result in results:
                    row = []
                    for var in vars_:
                        if var in result:
                            row.append(result[var]["value"])
                        else:
                            row.append("-")
                    print(" | ".join(row))
            else:
                print("No results found.")

    except Exception as e:
        print(f"Error executing SPARQL query: {e}")
        sys.exit(1)

def search(query, search_type="item"):
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "format": "json",
        "type": search_type
    }

    try:
        data = make_request(params)
        
        if "search" in data and len(data["search"]) > 0:
            print(f"Found {len(data['search'])} {search_type} results for \"{query}\":\n")
            for result in data["search"]:
                description = result.get("description", "No description available")
                print(f"ID: {result['id']}")
                print(f"Label: {result['label']}")
                print(f"Description: {description}")
                print("---")
        else:
            print(f"No {search_type} results found.")

    except Exception as e:
        print(f"Error searching Wikidata: {e}")
        sys.exit(1)

def get_entity_data(qid):
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as response:
        if response.status != 200:
            raise Exception(f"HTTP error! status: {response.status}")
        data = json.loads(response.read().decode())
        return data["entities"][qid]

def get_entity(qid, pid=None):
    try:
        entity = get_entity_data(qid)
        label = entity.get("labels", {}).get("en", {}).get("value", qid)
        
        if pid:
            claims = entity.get("claims", {}).get(pid, [])
            print(f"# {label} ({qid}) - Property {pid}")
            if not claims:
                print(f"No values found for property {pid}.")
            for claim in claims:
                mainsnak = claim.get("mainsnak", {})
                datavalue = mainsnak.get("datavalue", {})
                value = datavalue.get("value")
                
                if isinstance(value, dict):
                    if "text" in value: # Monolingual text
                        print(f"- {value['text']}")
                    elif "time" in value: # Time/Date
                        print(f"- {value['time']}")
                    elif "id" in value: # Entity ID
                        print(f"- {value['id']}")
                    elif "amount" in value: # Quantity
                        print(f"- {value['amount']} {value.get('unit', '')}")
                    else:
                        print(f"- {json.dumps(value)}")
                else:
                    print(f"- {value}")
        else:
            description = entity.get("descriptions", {}).get("en", {}).get("value", "No description")
            print(f"# {label} ({qid})")
            print(f"Description: {description}\n")
            print("Claims (Top level):")
            claims = entity.get("claims", {})
            for prop_id, claim_list in list(claims.items())[:10]:
                print(f"- Property: {prop_id} ({len(claim_list)} values)")
            if len(claims) > 10:
                print(f"... and {len(claims) - 10} more properties.")
            print("\nUse 'get <qid> <pid>' for specific values.")

    except Exception as e:
        print(f"Error retrieving entity {qid}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 query_wikidata.py <search|property|get|sparql> <args...>")
        sys.exit(1)

    command = sys.argv[1]
    
    if command == "search":
        search(" ".join(sys.argv[2:]), search_type="item")
    elif command == "property":
        search(" ".join(sys.argv[2:]), search_type="property")
    elif command == "get":
        qid = sys.argv[2]
        pid = sys.argv[3] if len(sys.argv) > 3 else None
        get_entity(qid, pid)
    elif command == "sparql":
        execute_sparql(" ".join(sys.argv[2:]))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)