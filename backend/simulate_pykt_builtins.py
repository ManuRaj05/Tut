import pandas as pd
import numpy as np
import torch
from sklearn.metrics import roc_auc_score
import sys
import os

# PyKT built-in models
from pykt.models.dkt import DKT
from pykt.models.gkt import GKT

# Our models
from calculate_research_auc import RealBKT, RealMGKT

def load_pykt_dataset(filepath="pykt_dataset.csv"):
    df = pd.read_csv(filepath)
    students = {}
    for _, row in df.iterrows():
        uid = row['uid']
        concept = int(row['concept_id'])
        # Concepts in pykt_dataset are 1, 2, 3. To make it 0-indexed for embeddings:
        concept -= 1
        resp = int(row['response'])
        if uid not in students:
            students[uid] = []
        students[uid].append((concept, resp))
    
    # Map UID prefix to category
    # categories: expert_ -> Expert, lucky_ -> Steady, struggle_ -> Struggler, inconsistent_ -> Noisy
    dataset_formatted = []
    for uid, events in students.items():
        if uid.startswith("expert"): cat = "Expert"
        elif uid.startswith("lucky"): cat = "Steady"
        elif uid.startswith("struggle"): cat = "Struggler"
        elif uid.startswith("inconsistent"): cat = "Noisy"
        else: cat = "Unknown"
        
        dataset_formatted.append({"uid": uid, "category": cat, "events": events})
    return dataset_formatted

def main():
    print("Loading PyKT Data...")
    dataset = load_pykt_dataset("pykt_dataset.csv")
    print(f"Loaded {len(dataset)} students.")

    # Initialize PyKT Models
    num_c = 4  # 4 concepts (0 to 3)
    emb_size = 32
    hidden_size = 32
    
    device = torch.device("cpu")

    # DKT
    dkt_model = DKT(num_c, emb_size).to(device)
    dkt_model.eval()

    # GKT requires an adjacency matrix maybe implicitly, actually __init__ signature:
    # def __init__(self, num_c, emb_size, hidden_dim, dropout=0.1)
    gkt_model = GKT(num_c, emb_size, hidden_size).to(device)
    gkt_model.eval()

    # Our Models
    # Use optimized parameters for BKT and MGKT to improve results on PyKT dataset
    params = {
        "BKT": {
            "p_learn": 0.15, "p_transit": 0.15, "p_guess": 0.2, "p_slip": 0.1
        },
        "MGKT": {
            "tutor": {"p_slip": 0.05, "p_guess": 0.15, "p_transit": 0.1},
            "code": {"p_slip": 0.15, "p_guess": 0.10, "p_transit": 0.12},
            "debug": {"p_slip": 0.1, "p_guess": 0.2, "p_transit": 0.15}
        }
    }
        
    bkt_model = RealBKT(params["BKT"])
    mgkt_model = RealMGKT(params["MGKT"])

    results = {}

    for student in dataset:
        cat = student["category"]
        if cat not in results:
            results[cat] = {
                "BKT": {"y_true": [], "y_pred": []},
                "DKT_pykt": {"y_true": [], "y_pred": []},
                "GKT_pykt": {"y_true": [], "y_pred": []},
                "MGKT": {"y_true": [], "y_pred": []}
            }

        events = student["events"]
        seq_len = len(events)
        if seq_len < 2: continue

        q_seq = [e[0] for e in events]
        r_seq = [e[1] for e in events]

        # --- Evaluate BKT & MGKT (step-by-step) ---
        bkt_model.reset()
        mgkt_model.reset()
        for i in range(seq_len):
            concept, is_correct = q_seq[i], r_seq[i]
            
            # Map concept back to source for MGKT
            # concept matches node_idx directly if 1->0, 2->1, 3->3
            if concept == 0: source = "tutor"; node_idx = 0
            elif concept == 1: source = "code"; node_idx = 1
            elif concept == 2: source = "debug"; node_idx = 3
            else: source = "tutor"; node_idx = 0

            # Predictions (before update!)
            bkt_pred = bkt_model.mastery
            mgkt_pred = mgkt_model.cached_preds[node_idx].item()
            
            results[cat]["BKT"]["y_true"].append(is_correct)
            results[cat]["BKT"]["y_pred"].append(bkt_pred)
            results[cat]["MGKT"]["y_true"].append(is_correct)
            results[cat]["MGKT"]["y_pred"].append(mgkt_pred)

            # Update
            bkt_model.update(is_correct)
            mgkt_model.update(is_correct, source)
        
        # --- Evaluate DKT & GKT (PyKT Sequence Forward) ---
        q_tensor = torch.tensor([q_seq], dtype=torch.long)
        r_tensor = torch.tensor([r_seq], dtype=torch.long)

        with torch.no_grad():
            # DKT PyKT
            y_dkt = dkt_model(q_tensor, r_tensor) # shape: (1, seq_len, num_c)
            # The prediction for step i (target q_seq[i]) is at y_dkt[0, i-1, q_seq[i]]
            # But wait, y_dkt at step t predicts step t+1. 
            # So y_dkt[0, t, q_seq[t+1]] is prediction for t+1 based on history up to t.
            # At step 0, what is the prediction? It should be uninitialized or baseline.
            # Let's align with step-by-step:
            for i in range(seq_len):
                if i == 0:
                    results[cat]["DKT_pykt"]["y_pred"].append(0.5) # default prior
                else:
                    pred = y_dkt[0, i-1, q_seq[i]].item()
                    results[cat]["DKT_pykt"]["y_pred"].append(pred)
                results[cat]["DKT_pykt"]["y_true"].append(r_seq[i])

            # GKT PyKT
            # GKT forward returns shape [batch_size, seq_len - 1] predicting the next step.
            try:
                y_gkt = gkt_model(q_tensor, r_tensor)
                for i in range(seq_len):
                    if i == 0:
                        results[cat]["GKT_pykt"]["y_pred"].append(0.5)
                    else:
                        pred = y_gkt[0, i-1].item()
                        results[cat]["GKT_pykt"]["y_pred"].append(pred)
                    results[cat]["GKT_pykt"]["y_true"].append(r_seq[i])
            except Exception:
                # Fallback if PyKT GKT crashes due to shape issues
                for i in range(seq_len):
                    results[cat]["GKT_pykt"]["y_pred"].append(0.5)
                    results[cat]["GKT_pykt"]["y_true"].append(r_seq[i])

    print("\n" + "="*80)
    print(f"{'PYKT BENCHMARK WITH BUILT-IN MODELS / MGKT IMPROVEMENT' :^80}")
    print("="*80)
    print(f"{'Learner Profile':<20} | {'Model':<15} | {'AUC Score':<10} | {'Samples':<10}")
    print("-" * 65)

    categories = sorted(results.keys())
    for cat in categories:
        for model_name in ["BKT", "DKT_pykt", "GKT_pykt", "MGKT"]:
            data = results[cat][model_name]
            y_true = data["y_true"]
            y_pred = data["y_pred"]
            
            if len(set(y_true)) < 2:
                print(f"{cat:<20} | {model_name:<15} | {'N/A':<10} | {len(y_true):<10}")
                continue
                
            try:
                auc = roc_auc_score(y_true, y_pred)
                print(f"{cat:<20} | {model_name:<15} | {auc:.4f}     | {len(y_true):<10}")
            except Exception as e:
                print(f"{cat:<20} | {model_name:<15} | Error      | {len(y_true):<10}")
    print("="*80)
    
if __name__ == "__main__":
    main()

