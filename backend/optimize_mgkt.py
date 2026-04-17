import os
import sys
import random
import torch
import numpy as np
from sklearn.metrics import roc_auc_score
from itertools import product

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calculate_research_auc import RealMGKT
from simulate_pykt_synthetic import generate_student_data

def evaluate_params(dataset, tutor_p, code_p, debug_p):
    params = {
        "tutor": {"p_slip": tutor_p[0], "p_guess": tutor_p[1], "p_transit": tutor_p[2]},
        "code": {"p_slip": code_p[0], "p_guess": code_p[1], "p_transit": code_p[2]},
        "debug": {"p_slip": debug_p[0], "p_guess": debug_p[1], "p_transit": debug_p[2]}
    }
    
    mgkt = RealMGKT(params)
    
    y_true = []
    y_pred = []
    
    for student in dataset:
        events = student["events"]
        if len(events) < 2: continue
        
        mgkt.reset()
        for e in events:
            source, is_correct, node_idx = e[0], e[1], e[2]
            
            # Predict
            pred = mgkt.cached_preds[node_idx].item()
            y_true.append(is_correct)
            y_pred.append(pred)
            
            # Update
            mgkt.update(is_correct, source)
    
    return roc_auc_score(y_true, y_pred)

def main():
    print("Generating Dataset...")
    dataset = []
    for sc in ["steady", "expert", "struggler", "noisy"]:
        dataset.extend(generate_student_data(n_students=50, n_steps=30, scenario=sc))
        
    print("Running Grid Search...")
    
    # We will search a smaller space for each modality to keep it fast
    tutor_space = [
        (0.05, 0.20, 0.15),
        (0.10, 0.15, 0.20),
        (0.10, 0.20, 0.10)
    ]
    code_space = [
        (0.15, 0.10, 0.20),
        (0.20, 0.05, 0.25),
        (0.20, 0.10, 0.15)
    ]
    debug_space = [
        (0.05, 0.05, 0.30),
        (0.10, 0.05, 0.25),
        (0.05, 0.10, 0.35)
    ]
    
    best_auc = 0
    best_params = None
    
    for t in tutor_space:
        for c in code_space:
            for d in debug_space:
                auc = evaluate_params(dataset, t, c, d)
                if auc > best_auc:
                    best_auc = auc
                    best_params = (t, c, d)
                    print(f"New Best AUC: {auc:.4f} | Tutor: {t} Code: {c} Debug: {d}")

if __name__ == "__main__":
    main()
