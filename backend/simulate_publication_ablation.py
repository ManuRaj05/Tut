import os
import sys
import random
import torch
import numpy as np
from sklearn.metrics import roc_auc_score

# Ensure backend modules are in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from calculate_research_auc import RealMGKT
from simulate_pykt_synthetic import generate_student_data

# --- ABLATION VARIANTS ---

class FullMGKT(RealMGKT):
    def __init__(self, params):
        super().__init__(params)
        self.name = "Full MGKT"

class NoGraphMGKT(RealMGKT):
    def __init__(self, params):
        super().__init__(params)
        self.name = "No-Graph"
        # Zero out all neighbor propagation, leaving only self-loops
        self.adj = torch.eye(4, dtype=torch.float32)
        self._recompute_mastery()

class NoWeightsMGKT(RealMGKT):
    def __init__(self, params):
        super().__init__(params)
        self.name = "No-Weights"
        # Homogeneous tracking weights instead of modality-specific
        uniform_param = {"p_slip": 0.15, "p_guess": 0.18, "p_transit": 0.15}
        self.params = {
            "tutor": uniform_param,
            "code": uniform_param,
            "debug": uniform_param
        }

class NoPrereqsMGKT(RealMGKT):
    def __init__(self, params):
        super().__init__(params)
        self.name = "No-Prereqs"
        # Everything naturally flows everywhere (structurally inconsistent propagation)
        self.adj = torch.ones((4, 4), dtype=torch.float32)
        self._recompute_mastery()

# --- RUNNER ---

def run_ablation():
    print("Generating Synthetic Dataset for 4 Scenarios (1500 students)...")
    scenarios = ["steady", "expert", "struggler", "noisy"]
    dataset = []
    for sc in scenarios:
        dataset.extend(generate_student_data(n_students=50, n_steps=30, scenario=sc))
    
    print(f"Generated {len(dataset)} traces.")
    
    # Best optimized MGKT params from our grid search optimization
    base_params = {
        "tutor": {"p_slip": 0.10, "p_guess": 0.15, "p_transit": 0.20},
        "code": {"p_slip": 0.15, "p_guess": 0.10, "p_transit": 0.20},
        "debug": {"p_slip": 0.05, "p_guess": 0.10, "p_transit": 0.35}
    }
    
    models = [
        FullMGKT(base_params),
        NoGraphMGKT(base_params),
        NoWeightsMGKT(base_params),
        NoPrereqsMGKT(base_params)
    ]
    
    results = {}
    
    # We will log the average propagation influence mathematically as well
    # Propagation metric: Average mastery gain on node X when an adjacent node Y is tested and correct.
    propagation_deltas = {m.name: [] for m in models}

    for student in dataset:
        cat = student["category"]
        if cat not in results:
            results[cat] = {m.name: {"y_true": [], "y_pred": []} for m in models}

        events = student["events"]
        seq_len = len(events)
        if seq_len < 2: continue

        q_seq = [e[2] for e in events]
        r_seq = [e[1] for e in events]
        s_seq = [e[0] for e in events]

        for m in models: m.reset()
        
        for i in range(seq_len):
            source, is_correct, node_idx = s_seq[i], r_seq[i], q_seq[i]
            
            for m in models:
                # Get neighbor states before update to calculate propagation impact
                pre_states = m.cached_preds.clone().detach()
                
                # Predict
                pred = pre_states[node_idx].item()
                results[cat][m.name]["y_true"].append(is_correct)
                results[cat][m.name]["y_pred"].append(pred)

                # Update
                m.update(is_correct, source)
                
                # Check Propagation (how much did adjacent un-tested nodes shift?)
                post_states = m.cached_preds.clone().detach()
                if is_correct:
                    # Collect shift in all nodes EXCEPT the one we just interacted with
                    shifts = []
                    for n in range(4):
                        if n != node_idx:
                            shifts.append((post_states[n] - pre_states[n]).item())
                    propagation_deltas[m.name].extend(shifts)

    # Print Table
    output_log = []
    output_log.append("\n" + "="*80)
    output_log.append(f"{'PUBLICATION-LEVEL ABLATION STUDY RESULTS' :^80}")
    output_log.append("="*80)
    output_log.append(f"{'Variant':<20} | {'Mean Propagation':<20} | {'Mean AUC (Overall)':<20}")
    output_log.append("-" * 65)
    
    # Calculate Overall AUC and Mean Propagation
    ablation_stats = []
    for m in models:
        all_true = []
        all_pred = []
        for cat in scenarios:
            all_true.extend(results[cat][m.name]["y_true"])
            all_pred.extend(results[cat][m.name]["y_pred"])
        
        overall_auc = roc_auc_score(all_true, all_pred)
        
        # Calculate Mean Propagation Magnitude (how much neighboring concepts moved after success)
        mean_prop = np.mean(np.abs(propagation_deltas[m.name])) if len(propagation_deltas[m.name]) > 0 else 0.0
        
        output_log.append(f"{m.name:<20} | {mean_prop:<20.4f} | {overall_auc:<20.4f}")
        ablation_stats.append((m.name, mean_prop, overall_auc))
        
    output_log.append("\n" + "="*80)
    output_log.append(f"{'AUC BREAKDOWN PER PROFILE' :^80}")
    output_log.append("="*80)
    output_log.append(f"{'Learner Profile':<20} | {'Variant':<20} | {'AUC Score':<15}")
    output_log.append("-" * 65)
    
    display_cats = {"steady": "Steady", "expert": "Expert", "struggler": "Struggler", "noisy": "Noisy"}
    for cat in scenarios:
        for m in models:
            y_true = results[cat][m.name]["y_true"]
            y_pred = results[cat][m.name]["y_pred"]
            if len(set(y_true)) > 1:
                auc = roc_auc_score(y_true, y_pred)
                output_log.append(f"{display_cats[cat]:<20} | {m.name:<20} | {auc:.4f}")
    
    output_log.append("="*80)
    
    final_output = "\n".join(output_log)
    print(final_output)
    
    with open("ablation_results.txt", "w", encoding="utf-8") as f:
        f.write(final_output)

if __name__ == "__main__":
    run_ablation()
