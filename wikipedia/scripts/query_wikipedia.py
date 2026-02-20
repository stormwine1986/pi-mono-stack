import sys
import json
import urllib.request
import urllib.parse
import re

API_ENDPOINT = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "Gemini-CLI-Wikipedia-Skill/1.0 (https://github.com/google/gemini-cli)"

def make_request(params):
    query_string = urllib.parse.urlencode(params)
    url = f"{API_ENDPOINT}?{query_string}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    
    with urllib.request.urlopen(req) as response:
        if response.status != 200:
            raise Exception(f"HTTP error! status: {response.status}")
        return json.loads(response.read().decode())

def search(query):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": ""
    }

    try:
        data = make_request(params)
        
        if "query" in data and "search" in data["query"] and len(data["query"]["search"]) > 0:
            print(f"Found {len(data['query']['search'])} results for \"{query}\":\n")
            for result in data["query"]["search"]:
                # Simple HTML tag stripping
                snippet = re.sub(r'<[^>]*>?', '', result["snippet"]).replace('&quot;', '"')
                print(f"Title: {result['title']}")
                print(f"Snippet: {snippet}")
                print("---")
        else:
            print("No results found.")

    except Exception as e:
        print(f"Error searching Wikipedia: {e}")
        sys.exit(1)

def get_page(title, full_page=False):
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "disableeditsection": "true"
    }

    if not full_page:
        params["section"] = 0

    try:
        import html2text
        data = make_request(params)
        
        if "parse" not in data or "text" not in data["parse"]:
            print(f"Page \"{title}\" not found.")
        else:
            parse_data = data["parse"]
            html_content = parse_data["text"]["*"]
            
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0  # Disable line wrapping
            h.baseurl = "https://en.wikipedia.org/wiki/"
            
            markdown_content = h.handle(html_content)
            if not full_page:
                print(f"# {parse_data['title']} (Summary)\n")
            else:
                print(f"# {parse_data['title']}\n")
            print(markdown_content)

    except ImportError:
        print("Error: 'html2text' library is not installed. Please rebuild the Docker image.")
        sys.exit(1)
    except Exception as e:
        print(f"Error retrieving page: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 query_wikipedia.py <search|page|fullpage> <query|title>")
        sys.exit(1)

    command = sys.argv[1]
    input_str = " ".join(sys.argv[2:])

    if command == "search":
        search(input_str)
    elif command == "page":
        get_page(input_str, full_page=False)
    elif command == "fullpage":
        get_page(input_str, full_page=True)
    else:
        print("Unknown command. Use \"search\", \"page\", or \"fullpage\".")
        sys.exit(1)