from neo4j import GraphDatabase
import json
import logging
logging.basicConfig(level=logging.ERROR)

uri = "neo4j://localhost:7687"
try:
    driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))
    driver.verify_connectivity()
    print("Neo4j is UP")
    with driver.session() as session:
        result = session.run("MATCH (n:Concept) RETURN n.name as name ORDER BY n.name")
        nodes = [record["name"] for record in result]
        print(f"Loaded {len(nodes)} nodes.")
        
        python_idx = -1
        for i, n in enumerate(nodes):
            if "python" in n.lower():
                print(f"[{i}] {n}")
                python_idx = i
                
    with open("backend/chatbot/services/user_state.json", "r") as f:
        data = json.load(f)
        user_data = data.get("abcd@gmail.com", {})
        
        if python_idx != -1:
            print(f"Mastery tutor: {user_data.get('tutor', [])[python_idx] if len(user_data.get('tutor', [])) > python_idx else 'N/A'}")
            print(f"Mastery code:  {user_data.get('code', [])[python_idx] if len(user_data.get('code', [])) > python_idx else 'N/A'}")
            print(f"Mastery debug: {user_data.get('debug', [])[python_idx] if len(user_data.get('debug', [])) > python_idx else 'N/A'}")
        
except Exception as e:
    print(f"Neo4j Error: {e}")
