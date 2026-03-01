import os
import json
import argparse
from urllib.parse import urlparse
from falkordb import FalkorDB

def escape_str(val):
    if isinstance(val, str):
        val = val.replace('\\', '\\\\').replace("'", "\\'")
        return f"'{val}'"
    return str(val)

def export_graph(graph_name="Graph-001", output_file="/home/pi-mono/.pi/agent/workspace/.irm/EXPORTED_SCHEMA.cypher"):
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    parsed = urlparse(redis_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    
    print(f"[*] Connecting to FalkorDB at {host}:{port}, Graph: {graph_name}...")
    try:
        db = FalkorDB(host=host, port=port)
        graph = db.select_graph(graph_name)
    except Exception as e:
        print(f"[!] Failed to connect: {e}")
        return

    statements = []
    statements.append("// ======================================================================")
    statements.append(f"// Exported Graph Data: {graph_name}")
    statements.append("// Includes all nodes, dynamically calculated betas, percentiles, and edges.")
    statements.append("// ======================================================================")
    statements.append("MATCH (n) DETACH DELETE n;\n")

    print("[*] Formatting Nodes...")
    res_nodes = graph.query("MATCH (n) RETURN ID(n), labels(n), properties(n)")
    
    node_maps = {}
    
    for row in res_nodes.result_set:
        node_id, labels, props = row[0], row[1], row[2]
        label_str = ":".join(labels)
        
        props_str_list = []
        for k, v in props.items():
            props_str_list.append(f"{k}: {escape_str(v)}")
        props_str = ", ".join(props_str_list)
        
        statements.append(f"CREATE (:{label_str} {{{props_str}}})")
        
        # Build unique match clause for relationship linking
        if 'ticker' in props:
            match_str = f"ticker: {escape_str(props['ticker'])}"
        elif 'target' in props and 'name' in props:
             match_str = f"target: {escape_str(props['target'])}, name: {escape_str(props['name'])}"
        elif 'owner' in props and 'name' in props:
            match_str = f"owner: {escape_str(props['owner'])}, name: {escape_str(props['name'])}"
        elif 'name' in props:
            match_str = f"name: {escape_str(props['name'])}"
        else:
            match_str = props_str
            
        node_maps[node_id] = f"{labels[0]} {{{match_str}}}"
        
    print("[*] Formatting Relationships...")
    res_rels = graph.query("MATCH ()-[r]->() RETURN ID(startNode(r)), type(r), properties(r), ID(endNode(r))")
    
    for row in res_rels.result_set:
        start_id, rel_type, props, end_id = row[0], row[1], row[2], row[3]
        
        start_match = node_maps.get(start_id)
        end_match = node_maps.get(end_id)
        
        if not start_match or not end_match:
            continue
            
        props_str_list = []
        for k, v in props.items():
            props_str_list.append(f"{k}: {escape_str(v)}")
            
        props_attr = " {" + ", ".join(props_str_list) + "}" if props_str_list else ""
        
        stmt = f"MATCH (a:{start_match}), (b:{end_match}) CREATE (a)-[:{rel_type}{props_attr}]->(b)"
        statements.append(stmt)
        
    print(f"[*] Total Nodes Exported: {len(res_nodes.result_set)}")
    print(f"[*] Total Edges Exported: {len(res_rels.result_set)}")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(";\n".join(statements) + ";\n")
        
    print(f"[+] Successfully exported graph to: {output_file}")
    
    export_config(host, port, os.path.dirname(output_file))

def export_config(host, port, out_dir):
    import redis
    print("[*] Exporting Redis Configurations...")
    out_script = os.path.join(out_dir, "EXPORTED_CONFIG.sh")
    
    try:
        r = redis.Redis(host=host, port=port, decode_responses=True)
    except Exception as e:
        print(f"[!] Redis connect err: {e}")
        return
        
    lines = ["#!/bin/bash", "# Auto-generated Redis Configuration Backup", ""]
    
    keys_to_export = ["irm:config:sources"]
    for p_key in r.scan_iter("irm:portfolio:*:holdings:*"):
        keys_to_export.append(p_key)
        
    for key in keys_to_export:
        data = r.hgetall(key)
        if not data:
            continue
        lines.append(f"# {key}")
        lines.append(f"redis-cli -h {host} -p {port} DEL \"{key}\" >/dev/null")
        for k, v in data.items():
            safe_v = v.replace("'", "'\\''")  # quote safety
            lines.append(f"redis-cli -h {host} -p {port} HSET \"{key}\" \"{k}\" '{safe_v}' >/dev/null")
        lines.append("")
        
    with open(out_script, "w") as f:
        f.write("\n".join(lines))
    print(f"[+] Successfully exported Redis Config to: {out_script}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/home/pi-mono/.pi/agent/workspace/.irm/EXPORTED_SCHEMA.cypher")
    args = parser.parse_args()
    export_graph(output_file=args.output)
