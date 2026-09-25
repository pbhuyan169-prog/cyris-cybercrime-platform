import json
import os
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

class CyrisGraphEngine:
    def __init__(self, data_path="mock_data.json"):
        self.data_path = data_path
        if HAS_NX:
            self.graph = nx.Graph()
        else:
            self.adj = {}
            self.node_types = {}
        self.build_graph()

    def build_graph(self):
        """Loads JSON data and builds the graph nodes and edges."""
        if not os.path.exists(self.data_path):
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            complaints = json.load(f)

        for item in complaints:
            c_id = item.get("complaint_id")
            if not c_id:
                continue

            if HAS_NX:
                self.graph.add_node(c_id, type="complaint", details=item)
            else:
                self.node_types[c_id] = "complaint"
                self.adj.setdefault(c_id, set())

            # Link entities (UPI, Phone, IP) to the complaint
            entities = [
                (item.get("upi_id"), "upi"),
                (item.get("phone_number"), "phone"),
                (item.get("ip_address"), "ip")
            ]

            for entity_val, entity_type in entities:
                if entity_val:
                    if HAS_NX:
                        self.graph.add_node(entity_val, type=entity_type)
                        self.graph.add_edge(c_id, entity_val)
                    else:
                        self.node_types[entity_val] = entity_type
                        self.adj.setdefault(c_id, set()).add(entity_val)
                        self.adj.setdefault(entity_val, set()).add(c_id)

    def find_connected_cases(self, complaint_id):
        """Finds all connected complaints via shared entities (within 2 hops)."""
        if HAS_NX:
            if complaint_id not in self.graph:
                return []
            subgraph = nx.single_source_shortest_path_length(self.graph, complaint_id, cutoff=2)
            return [
                node for node, dist in subgraph.items() 
                if self.graph.nodes[node].get("type") == "complaint" and node != complaint_id
            ]

        if complaint_id not in self.adj:
            return []
        
        # BFS 2 hops
        visited = {complaint_id: 0}
        queue = [complaint_id]
        while queue:
            curr = queue.pop(0)
            dist = visited[curr]
            if dist < 2:
                for nxt in self.adj.get(curr, []):
                    if nxt not in visited:
                        visited[nxt] = dist + 1
                        queue.append(nxt)

        return [
            n for n, d in visited.items()
            if self.node_types.get(n) == "complaint" and n != complaint_id
        ]

    def get_fraud_rings(self):
        """Clusters connected components and identifies multi-complaint fraud rings."""
        if HAS_NX:
            components = list(nx.connected_components(self.graph))
            rings = []
            for index, comp in enumerate(components):
                complaints_in_cluster = [n for n in comp if self.graph.nodes[n].get("type") == "complaint"]
                if len(complaints_in_cluster) > 1:
                    rings.append({
                        "ring_id": f"RING-{index + 1}",
                        "linked_complaints_count": len(complaints_in_cluster),
                        "complaint_ids": complaints_in_cluster
                    })
            return sorted(rings, key=lambda x: x["linked_complaints_count"], reverse=True)

        visited = set()
        components = []
        for node in list(self.adj.keys()):
            if node not in visited:
                comp = set()
                q = [node]
                visited.add(node)
                while q:
                    curr = q.pop(0)
                    comp.add(curr)
                    for nxt in self.adj.get(curr, []):
                        if nxt not in visited:
                            visited.add(nxt)
                            q.append(nxt)
                components.append(comp)

        rings = []
        for index, comp in enumerate(components):
            c_nodes = [n for n in comp if self.node_types.get(n) == "complaint"]
            if len(c_nodes) > 1:
                rings.append({
                    "ring_id": f"RING-{index + 1}",
                    "linked_complaints_count": len(c_nodes),
                    "complaint_ids": c_nodes
                })
        return sorted(rings, key=lambda x: x["linked_complaints_count"], reverse=True)


if __name__ == "__main__":
    # Dynamically resolve mock_data.json relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_data_path = os.path.join(base_dir, "mock_data.json")

    engine = CyrisGraphEngine(default_data_path)
    print("Detected Fraud Rings:")
    print(json.dumps(engine.get_fraud_rings()[:3], indent=2))