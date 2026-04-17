from ..models import AgentSession
from .tools import MainAgentTools
import json

from .router_agent import RouterAgent
from .planner_agent import PlannerAgent
from .director_agent import DirectorAgent
from .tutor_agent import TutorAgent
from .research_agent import ResearchAgent

class MainAgentOrchestrator:
    def __init__(self, user):
        self.user = user
        self.session = AgentSession.objects(user=user).first()
        if not self.session:
            self.session = AgentSession(user=user)
            self.session.save()
            
        
        self.router = RouterAgent()
        self.planner = PlannerAgent()
        self.director = DirectorAgent()
        self.tutor = TutorAgent()
        self.researcher = ResearchAgent()

    def process_message(self, message):
        """
        Main entry point. Uses Router to dispatch to specialized agents.
        """
        # 1. Save User Message
        self.session.chat_history.append({"sender": "user", "text": message, "timestamp": str(self.session.updated_at)})
        self.session.save()

        # Build History String for Agents
        try:
            history_str = "\n".join([f"{msg.get('sender', 'unknown').upper()}: {msg.get('text', '')}" for msg in self.session.chat_history[-10:]])
        except:
            history_str = ""

        # 2. Check Plan Status
        # If we have an active plan, we prioritize executing it, UNLESS the user explicitly wants to switch.
        # We can use the Router to check for a "PLAN" intent (switch topic) even during a plan.
        
        intent = self.router.route(message)
        print(f"Orchestrator Route: {intent}")

        # 0. Scope Guardrail: If topic is irrelevant, politely decline.
        if not intent.get("is_relevant", True):
            topic = intent.get("topic") or "that topic"
            reply = f"I'm currently specialized in **Python and Computer Science**. While I'd love to help, I don't have the specialized knowledge to teach you about **{topic}**. \n\nWould you like to learn something about Python, like Lists, Loops, or Recursion instead? 🐍"
            self._save_bot_reply(reply)
            return {"reply": reply, "action": None}

        # If user wants to start a NEW topic/plan, we interrupt the current one.
        if intent["route"] == "PLAN":
            topic = intent.get("topic") or "General"
            style = intent.get("style") or "comprehensive"
            
            # Reset Plan
            self.session.current_plan = []
            self.session.current_topic = topic
            self.session.failed_prereqs = []
            
            # Generate New Plan
            plan_str = self.planner.create_plan(topic, style)
            try:
                plan = json.loads(plan_str)
                self.session.current_plan = plan
                self.session.save()
                
                # Start immediately
                return self._execute_plan_step(message, history_str)
            except Exception as e:
                reply = f"I tried to create a plan for {topic}, but failed. Let's just chat about it."
                self._save_bot_reply(reply)
                return {"reply": reply, "action": None}

        # If we are currently in a plan, try to advance it or execute steps
        if self.session.current_plan:
            # 2a. Priority Interruptions (Technical Questions)
            # If the user asks a technical question, we answer it even if a plan is active.
            if intent["route"] == "QUESTION":
                ans = self.researcher.handle(message, history_str)
                reminder = f"\n\n--- MISSION REMINDER ---\nDon't forget: I prepared a specialized lesson on **{self.session.current_topic}** for you in the **Tutor Tab**! Let's continue there when you're ready."
                reply = ans + reminder
                self._save_bot_reply(reply)
                return {"reply": reply, "action": None}

            # 2b. Navigation / Skip intent
            skip_keywords = ["skip", "next", "pass", "move on"]
            if any(k in message.lower() for k in skip_keywords):
                 skipped_step = self.session.current_plan.pop(0)
                 self.session.save()
                 reply = f"Skipping {skipped_step.get('step')}... Moving to next."
                 self._save_bot_reply(reply)
                 return self.process_message("NEXT_STEP_TRIGGER") 

            # 2c. Execute Plan Step
            return self._execute_plan_step(message, history_str)

        # If NO Plan, and NOT Planning -> Handle based on Route
        if intent["route"] == "ACTION":
            # Direct Action (e.g., "Give me a quiz")
            topic = intent.get("topic") or self.session.current_topic or "General"
            
            action_trigger = self.director.handle(message, topic)
            
            # Parse trigger to standard format
            # Support ACTION_TRIGGER:TYPE:DATA or just ACTION_TRIGGER:TYPE
            clean_trigger = action_trigger.replace("ACTION_TRIGGER:", "").strip()
            parts = clean_trigger.split(":", 1)
            action_type = parts[0]
            action_data = parts[1] if len(parts) > 1 else topic
            
            action_payload = router_action_to_payload(action_type, action_data)
            
            reply = "Opening that for you now."
            self._save_bot_reply(reply)
            return {"reply": reply, "action": action_payload}

        elif intent["route"] == "QUESTION":
            reply = self.researcher.handle(message, history_str)
            self._save_bot_reply(reply)
            return {"reply": reply, "action": None}

        else: # CHAT / DEFAULT
            # Just talk
            reply = self.tutor.handle(message, history_str, user_email=self.user.email)
            self._save_bot_reply(reply)
            return {"reply": reply, "action": None}

    def advance_plan(self, context_message):
        """
        Bypasses the Router and forces the execution of the next step in the plan.
        Used by system triggers (e.g. report_success) to ensure we don't accidentally
        trigger a new plan via the Router.
        """
        self._save_bot_reply(f"System: {context_message}")
        history_str = "" 
        return self._execute_plan_step(context_message, history_str)

    def _execute_plan_step(self, message, chat_history):
        """
        Executes the current step in the plan using specialized agents.
        """
        if not self.session.current_plan:
             reply = "Plan completed! What next?"
             self._save_bot_reply(reply)
             return {"reply": reply, "action": None}
             
        current_step = self.session.current_plan[0]
        step_type = current_step.get("step")
        step_topic = current_step.get("topic")
        action = current_step.get("action")
        
        reply = ""
        step_complete = False

        # --- STEP DISPATCHER ---
        
        # 1. PREREQUISITE TEACHING (Main Agent Internal)
        if step_type == "teach_prereqs":
            # Use internal TutorAgent instead of persistent_tutor delegation
            reply = self.tutor.handle(message, chat_history, topic=step_topic, subtopic="Prerequisites", user_email=self.user.email)
            # For simplicity, we assume one interaction for prereqs in Main Agent
            # If we want a full multi-turn here, we could add state, but user requested isolation.
            step_complete = True

        # 2. TEACH CONTENT -> Hand off to Tutor Agent Tab
        elif step_type == "teach_content":
             # We no longer execute teaching inside the Main Agent CenterPanel.
             # Instead, we perform a clean "Handoff" to the dedicated Tutor Tab.
             from chatbot.services.persistent_tutor import start_new_topic
             
             started = current_step.get("started", False)
             if not started:
                 current_step["started"] = True
                 self.session.current_plan[0] = current_step
                 self.session.save()
                 
                 # Initialize the topic in the SQL Database for the other tab
                 is_rev = current_step.get("mode") == "revision"
                 start_res = start_new_topic(self.user, step_topic, is_revision=is_rev)
                 roadmap_reply = start_res.get("reply")
                 
                 reply = f"I've prepared a specialized study roadmap for **{step_topic}**. I'm switching you to the **Tutor Tab** now to begin the lesson!"
                 
                 action = {
                     "type": "SWITCH_TAB", 
                     "view": "tutor", 
                     "data": {
                         "topic": step_topic, 
                         "initialMessage": roadmap_reply 
                     }
                 }
                 step_complete = False
             else:
                 # If the user is somehow still here, just move to the next thing or prompt them
                 reply = f"I'm ready for you in the **Tutor Tab** to master **{step_topic}**! \n\nIf you have a specific question about it, feel free to ask here, otherwise go ahead and switch tabs to continue the theory! 🚀"
                 step_complete = False

        # 4. PRACTICE -> Director
        elif step_type == "practice_code":
             action_payload = router_action_to_payload("SWITCH_TO_CODE", step_topic)
             reply = f"Time to write some code for {step_topic}."
             action = action_payload
             # FIX: Do NOT mark complete. Wait for report_success.
             step_complete = False

        elif step_type == "practice_debug":
             action_payload = router_action_to_payload("SWITCH_TO_DEBUG", step_topic)
             reply = f"Let's fix some bugs related to {step_topic}."
             action = action_payload
             # FIX: Do NOT mark complete. Wait for report_success.
             step_complete = False

        else:
             # Unknown step
             step_complete = True

        # Advance Plan
        if step_complete:
            self.session.last_step_result = {"step": step_type, "status": "delegated"}
            self.session.current_plan.pop(0)
            self.session.save()
            
            # If we just auto-completed a bunch of director actions, we might want to stop?
            # Or chaining?
            # If we chained multiple steps, we'd just dump multiple actions which isn't supported well.
            # So generally we assume one action per turn.
            
            if self.session.current_plan:
                reply += f"\n\n(Moving to next step: {self.session.current_plan[0]['step']})"

        self._save_bot_reply(reply)
        return {"reply": reply, "action": action}

    def _save_bot_reply(self, text):
        self.session.chat_history.append({"sender": "bot", "text": text})
        self.session.save()

def router_action_to_payload(action_type, action_data):
    if action_type == "SWITCH_TO_CODE":
        return {"type": "SWITCH_TAB", "view": "code", "data": {"topic": action_data}}
    elif action_type == "SWITCH_TO_DEBUG":
        return {"type": "SWITCH_TAB", "view": "debugger", "data": {"topic": action_data}}
    elif action_type == "SWITCH_TO_QUIZ":
        return {"type": "SWITCH_TAB", "view": "quiz", "data": {"topic": action_data}}
    return None
