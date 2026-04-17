import os
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

# Append current directory to path so relative imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the data generator and models from existing scripts
from simulate_pykt_synthetic import generate_student_data
from calculate_research_auc import RealBKT, RealMGKT
from pykt.models.dkt import DKT

def main():
    print("Generating Dataset for ROC plotting...")
    scenarios = ["steady", "expert", "struggler", "noisy"]
    dataset = []
    for sc in scenarios:
        dataset.extend(generate_student_data(n_students=50, n_steps=30, scenario=sc))
    
    print(f"Generated {len(dataset)} traces.")

    num_c = 4
    emb_size = 32
    device = torch.device("cpu")

    dkt_model = DKT(num_c, emb_size).to(device)
    dkt_model.eval()

    params = {
        "BKT": {"p_learn": 0.05, "p_transit": 0.05, "p_guess": 0.40, "p_slip": 0.40},
        "MGKT": {
            "tutor": {"p_slip": 0.10, "p_guess": 0.15, "p_transit": 0.20},
            "code": {"p_slip": 0.15, "p_guess": 0.10, "p_transit": 0.20},
            "debug": {"p_slip": 0.05, "p_guess": 0.10, "p_transit": 0.35}
        }
    }

    bkt_model = RealBKT(params["BKT"])
    mgkt_model = RealMGKT(params["MGKT"])

    y_true_all = {"BKT": [], "DKT": [], "MGKT": []}
    y_pred_all = {"BKT": [], "DKT": [], "MGKT": []}

    print("Evaluating models to gather prediction arrays...")
    for student in dataset:
        events = student["events"]
        seq_len = len(events)
        if seq_len < 2: continue

        q_seq = [e[2] for e in events]
        r_seq = [e[1] for e in events]
        s_seq = [e[0] for e in events]

        bkt_model.reset()
        mgkt_model.reset()
        
        for i in range(seq_len):
            source, is_correct, node_idx = s_seq[i], r_seq[i], q_seq[i]
            
            y_true_all["BKT"].append(is_correct)
            y_pred_all["BKT"].append(bkt_model.mastery)
            
            y_true_all["MGKT"].append(is_correct)
            y_pred_all["MGKT"].append(mgkt_model.cached_preds[node_idx].item())

            bkt_model.update(is_correct)
            mgkt_model.update(is_correct, source)
        
        q_tensor = torch.tensor([q_seq], dtype=torch.long)
        r_tensor = torch.tensor([r_seq], dtype=torch.long)

        with torch.no_grad():
            y_dkt = dkt_model(q_tensor, r_tensor)
            for i in range(seq_len):
                if i == 0:
                    y_pred_all["DKT"].append(0.5)
                else:
                    y_pred_all["DKT"].append(y_dkt[0, i-1, q_seq[i]].item())
                y_true_all["DKT"].append(r_seq[i])

    print("Plotting ROC Curves...")
    plt.figure(figsize=(10, 8))
    
    colors = {'BKT': 'blue', 'DKT': 'orange', 'MGKT': 'green'}
    
    for model_name in ["BKT", "DKT", "MGKT"]:
        fpr, tpr, _ = roc_curve(y_true_all[model_name], y_pred_all[model_name])
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, color=colors[model_name], lw=2, label=f'{model_name} (AUC = {roc_auc:.3f})')
        
    plt.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate', fontsize=14)
    plt.ylabel('True Positive Rate', fontsize=14)
    plt.title('Receiver Operating Characteristic (ROC) Comparison', fontsize=16)
    plt.legend(loc="lower right", fontsize=12)
    plt.grid(alpha=0.3)
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auc_comparison_curve.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Saved plot perfectly to {out_path}")

if __name__ == "__main__":
    main()
