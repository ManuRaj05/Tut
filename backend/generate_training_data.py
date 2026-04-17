import os
import json
import sys

# Ensure backend modules are accessible
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from simulate_pykt_synthetic import generate_student_data

def generate_and_save_dataset():
    print("Generating Synthetic Dataset for GNN Training...")
    
    # Generate 500 students per scenario to have a large enough dataset for training
    scenarios = ["steady", "expert", "struggler", "noisy"]
    dataset = []
    
    for sc in scenarios:
        # Increase n_students for a robust training set
        dataset.extend(generate_student_data(n_students=500, n_steps=60, scenario=sc))
    
    print(f"Generated {len(dataset)} student traces.")
    
    # Format and save to research_dataset.json
    output_path = os.path.join(os.path.dirname(__file__), "research_dataset.json")
    
    try:
        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=4)
        print(f"Successfully saved training dataset to: {output_path}")
    except IOError as e:
        print(f"Failed to save dataset: {e}")

if __name__ == "__main__":
    generate_and_save_dataset()
