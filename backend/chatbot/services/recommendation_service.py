
import numpy as np
from .gkt_model import GKTModel

class RecommendationService:
    """
    Dynamic Recommendation Engine.
    uses GKT Mastery State + Graph Structure to recommend the next best step.
    """
    def __init__(self):
        self.gkt = GKTModel()

    def get_next_best_step(self, user_email, topic_name):
        """
        Determines the next optimal concept to teach.
        Strategy:
        1. Identify all concepts related to 'topic_name' (Subgraph).
        2. Filter out concepts that are already Mastered (Score > 0.85).
        3. Among the remaining, find the one with the highest "Readiness":
           - Readiness = Average Mastery of its Prerequisites.
           - If Prereqs are not mastered, we shouldn't teach this yet.
        """
        # 1. Get User State
        vectors = self.gkt._get_user_vectors(user_email)
        
        # Use 'tutor' vector for Prerequisite Readiness (Conceptual Understanding)
        # If 'tutor' key missing (legacy), try to use 'vectors' itself if it's a list
        if isinstance(vectors, dict):
             tutor_vec = vectors.get("tutor", [])
        elif isinstance(vectors, list):
             tutor_vec = vectors
        else:
             tutor_vec = []

        candidates = []
        for idx, concept in enumerate(self.gkt.concepts):
            # Use actual true composite mastery (Tutor + Code + Debug) for the threshold
            mastery = self.gkt.get_mastery(user_email, concept)
            
            if mastery >= 0.80:
                continue # Already mastered
                
            # Check Prerequisites (Incoming Edges in Adj Matrix)
            prereq_indices = np.where(self.gkt.adj_matrix[idx] > 0)[0]
            
            if len(prereq_indices) == 0:
                # No prereqs? Foundational concept. High readiness.
                readiness = 1.0
            else:
                # Avg composite mastery of prereqs
                prereq_masteries = []
                for p_idx in prereq_indices:
                     p_concept = self.gkt.concepts[p_idx]
                     prereq_masteries.append(self.gkt.get_mastery(user_email, p_concept))

                readiness = sum(prereq_masteries) / len(prereq_indices)
            
            # Additional Heuristic: Is this concept related to the requested "topic"?
            if topic_name.lower() in getattr(concept, 'lower', lambda: str(concept).lower())(): 
                 pass # Could boost here

            candidates.append({
                "concept": concept,
                "readiness": readiness,
                "current_mastery": mastery
            })
            
        if not candidates:
            return None # All mastered!
            
        # 1. Filter: Only nodes with Readiness > 0.60 are eligible for study
        eligible_candidates = [c for c in candidates if c["readiness"] > 0.60]
        
        if not eligible_candidates:
            # Fallback: if no node meets >60% readiness, just take the one with the highest readiness available
            # This prevents soft-locks if the student is struggling with prerequisites.
            candidates.sort(key=lambda x: (x["readiness"], x["current_mastery"]), reverse=True)
            best_candidate = candidates[0]
            print(f"[Recommender] Fallback (No node >60% ready). Best Step: {best_candidate['concept']} (Readiness: {best_candidate['readiness']:.2f})")
            return best_candidate["concept"]
            
        # 2. Sort: Among eligible nodes (Readiness > 0.60), pick the one with MINIMUM mastery
        # We sort ascending by current_mastery to prioritize the least known topic. 
        # Tie-breaker: Highest readiness.
        eligible_candidates.sort(key=lambda x: (x["current_mastery"], -x["readiness"]))
        
        best_candidate = eligible_candidates[0]
        
        print(f"[Recommender] Best Step: {best_candidate['concept']} (Readiness: {best_candidate['readiness']:.2f})")
        return best_candidate["concept"]
