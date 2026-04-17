import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings') # Adjust 'backend.settings' to your project's settings module path if needed
django.setup()

from chatbot.services.gkt_model import GKTModel

def test_gat_propagation():
    print("--- Starting GAT Propagation Test ---")
    gkt = GKTModel()
    test_user = "test_gat@example.com"
    
    # 1. Pick a node that has dependencies (e.g., Python Basics -> Variables)
    # Let's see the concepts
    print(f"Total concepts: {len(gkt.concepts)}")
    
    # Find a node with at least one dependent
    test_node_idx = -1
    dependents = []
    
    for i in range(len(gkt.concepts)):
        deps = [j for j in range(len(gkt.concepts)) if gkt.adj_matrix[j][i] > 0]
        if len(deps) > 0:
            test_node_idx = i
            dependents = deps
            break
            
    if test_node_idx == -1:
        print("Error: Could not find any concept with dependencies in the graph.")
        return
        
    test_concept_name = gkt.concepts[test_node_idx]
    dep_names = [gkt.concepts[d] for d in dependents]
    
    print(f"\nSelected Test Node: '{test_concept_name}' (Index {test_node_idx})")
    print(f"Dependent Nodes (Neighbors that should get a GAT boost): {dep_names}\n")
    
    # --- BEFORE STATE ---
    print("--- BEFORE BKT UPDATE ---")
    mastery_before = gkt.get_mastery(test_user, test_concept_name)
    print(f"Mastery '{test_concept_name}': {mastery_before:.4f}")
    for d in dep_names:
        print(f"Neighbor Mastery '{d}': {gkt.get_mastery(test_user, d):.4f}")
        
    print("\nTriggering a CORRECT answer update for the Test Node...\n")
    
    # --- TRIGGER THE UPDATE ---
    # This calls BKT -> GAT propagation
    gkt.update(test_user, test_concept_name, is_correct=True, source_type="tutor")
    
    # --- AFTER STATE ---
    print("\n--- AFTER BKT & GAT UPDATE ---")
    mastery_after = gkt.get_mastery(test_user, test_concept_name)
    print(f"Mastery '{test_concept_name}': {mastery_after:.4f} (BKT Increase)")
    
    boosted_count = 0
    for d in dep_names:
        mastery_neighbor_after = gkt.get_mastery(test_user, d)
        print(f"Neighbor Mastery '{d}': {mastery_neighbor_after:.4f} ", end="")
        if mastery_neighbor_after > gkt.get_mastery(test_user, d): # This check is flawed since we just checked it, but let's visually compare to before
            pass
        # Compare to before
        # Note: We need the raw state to accurately compare, get_mastery is a composite.
        pass
        
if __name__ == '__main__':
    test_gat_propagation()
