from django.http import JsonResponse
import re
# import google.generativeai as genai (REMOVED)
from chatbot.services.groq_service import GroqService
groq_service = GroqService()
# model = genai.GenerativeModel("gemini-2.5-flash") (REMOVED)
from django.http import JsonResponse
from .models import  UserQuestion
from users.models import User
import requests
from django.views.decorators.csrf import csrf_exempt
import json
from rest_framework.permissions import IsAuthenticated
from users.authentication import JWTAuthentication
from .services.ai_utility import generate_question_with_testcases
from .services.json_utils import clean_json_blocks

from rest_framework.decorators import api_view, authentication_classes, permission_classes

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def generate_question(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)
    print(request.body)
    data = json.loads(request.body)
    topic = data.get("topic")   
    user_id = request.user.id  # or get from session/auth
    print(topic,user_id)
    if not topic or not user_id:
        return JsonResponse({"error": "Topic and user_id are required"}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    # --- Call Agent Service (Groq) ---
    from .services.agent_service import process_user_query
    
    # Construct a query to trigger intent detection or directly use tools
    # Since we want a question for a topic, we can simulate a query
    query = f"Generate a coding question about {topic}"
    
    try:
        user = User.objects.get(id=user_id)
        # process_user_query saves the question to DB (QuestionB/Plan)
        # We need to adapt the return to what frontend expects
        # process_user_query returns {"type": "single", "question": qdata} or plan
        
        result_data = process_user_query(query, user)
        
        if result_data.get("type") == "single":
            qdata = result_data.get("question", {})
            question_text = qdata.get("description", "") # or title + description
            # Frontend expects "question_text"
            if qdata.get("title"):
                question_text = f"**{qdata.get('title')}**\n\n{question_text}"
                
            test_cases = qdata.get("testcases", [])
            
        elif result_data.get("type") == "plan":
             # If it generated a plan, just take the first question?
             # Or inform frontend?
             # For now, let's just take the first question from the plan if available
             questions = result_data.get("questions", [])
             if questions:
                 qdata = questions[0]
                 question_text = f"**{qdata.get('title')}**\n\n{qdata.get('description')}"
                 test_cases = qdata.get("testcases", [])
             else:
                 question_text = "No question generated."
                 test_cases = []
        else:
            question_text = "Unexpected agent response."
            test_cases = []

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": f"Agent request failed: {str(e)}"}, status=500)
    
    # Note: process_user_query already saves QuestionB / Plan models.
    # The frontend seems to rely on the response JSON directly or maybe refetching.
    # The original view saved UserQuestion (mongoengine).
    # agent_service saves QuestionB (mongoengine).
    # We might want to save UserQuestion too if frontend relies on it specifically?
    # Original view saved: UserQuestion(user=user, topic=topic, question_text=question_text, test_cases=test_cases).save()
    
    # Let's save UserQuestion to maintain backward compatibility for now, 
    # even though agent_service saves QuestionB.
    # UserQuestion matches the simple schema frontend might expect if it lists them.
    try:
        UserQuestion(user=user, topic=topic, question_text=question_text, test_cases=test_cases).save()
    except Exception as e:
        print(f"Error saving legacy UserQuestion: {e}")

    # --- Return response to frontend ---
    return JsonResponse({
        "topic": topic,
        "question_text": question_text,
        "test_cases": test_cases
    })


# Provide hints
def get_hint(request):
    question = request.GET.get("question", "reverse a string")
    prompt = f"Give a step-by-step hint for solving: {question}, \
               but do not provide the full solution."

    # response = model.generate_content(prompt)
    # return JsonResponse({"hint": response.text})
    text = groq_service.generate_content(prompt)
    return JsonResponse({"hint": text})

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import requests
# API_KEY = os.environ.get("GEMINI_API_KEY", "") (REMOVED)

@api_view(["POST"])
@permission_classes([AllowAny])
def generate_visualization(request):
    prompt = request.data.get("prompt", "")
    if not prompt:
        return Response({"error": "Prompt is required"}, status=400)

    system_prompt = """
    You are a specialized Visualization Code Generator.

Your task is to generate a complete, self-contained **single-page HTML document** (one file) that visually and interactively demonstrates the requested algorithm or data structure.

RULES:
1. Respond ONLY with the plain HTML document as a single string (start with <!DOCTYPE html> and include <html> ...). Do NOT wrap the output in JSON, Markdown, comments, or any additional text.
2. The document MUST include Tailwind CSS loaded via CDN (https://cdn.tailwindcss.com) and use Tailwind utility classes for styling. Do NOT include external CSS files other than the Tailwind CDN.
3. Use only plain, vanilla JavaScript for interactivity. Do NOT use React, Vue, or any other frameworks/libraries. You may include inline <script> tags inside the HTML file.
4. The page MUST include at least two visible controls labeled "Next Step" and "Reset" to control the visualization, and display the current step index.
5. The HTML should be self-contained and runnable inside an iframe (no module imports, no ESM import/export statements, no external network calls other than the Tailwind CDN).
6. Ensure all DOM element IDs and classes are unique and descriptive to avoid collisions when embedded in an iframe.
7. The visual output should be responsive and usable on common desktop/mobile widths.
8. Include a small legend explaining colors/states used in the visualization (e.g., comparing, swapping, sorted).
9. Keep the code robust: sanitize inputs if accepting user input, avoid using `eval`, and do not depend on server-side resources.
10. The HTML must be ready to render as-is; the user should be able to paste it into an iframe or file and see the fully working visualization without modifications.
11.The input should be from the user 
12.The visualization should also say what is happening at each step
13.Every step should be understandable visually
14.Add animation how they connect or change in real time
15.Visualize the problem first before visualizing the algorithm and then change the visualization to show how the algorithm works
16.provide how the datastructureschange if It needed in the problem 
17.Make sure the illustrattion of how a real code algorithm would work
18.do the swapping or changing of datastructures in real time.
Do not add any additional commentary — output only the HTML document.

Steps:
1. Get the problem or algorithm from the user
2. identify the problem or algorithm
3. Find the best method or implementation of the solution for the problem
4. Identify the Datastructures needed for the problem
5. now plan the blocks to get input
6 now plan all possible interaction in the HTML
7. now plan all the code, data structure and explaination of each step in the HTML
8. now plan the final code
9. provide code snippet 
10. now generate html with clean code and provide best animaation for with tailwind css
    """

    # Use Groq logic instead of direct Gemini REST call
    # Construct a full prompt with system instruction
    full_prompt = f"{system_prompt}\n\nUser Prompt: {prompt}"
    
    try:
        reply = groq_service.generate_content(full_prompt)
        print(f"DEBUG: Raw LLM Reply: {reply[:500]}...") # Log first 500 chars
        
        # CLEANUP: Remove <think>...</think> blocks from reasoning models
        cleaned_reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL | re.IGNORECASE).strip()
        
        # --- ROBUST EXTRACTION ---
        # 1. Try to find <!DOCTYPE html>...</html>
        match_doctype = re.search(r'(<!DOCTYPE html>.*</html>)', cleaned_reply, re.DOTALL | re.IGNORECASE)
        # 2. Try to find <html>...</html>
        match_html = re.search(r'(<html.*</html>)', cleaned_reply, re.DOTALL | re.IGNORECASE)
        
        if match_doctype:
            cleaned_reply = match_doctype.group(1)
        elif match_html:
            cleaned_reply = match_html.group(1)
        else:
            # 3. Fallback: If it's wrapped in markdown code blocks, strip them
            if "```html" in cleaned_reply:
                cleaned_reply = cleaned_reply.split("```html")[1].split("```")[0].strip()
            elif "```" in cleaned_reply:
                cleaned_reply = cleaned_reply.split("```")[1].split("```")[0].strip()
            
        # Final safety: If extraction failed but we have a reply, just send the cleaned reply
        if not cleaned_reply.strip() and reply.strip():
            cleaned_reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL | re.IGNORECASE).strip()

        print(f"Visualization Generated (Length: {len(cleaned_reply)})")
        return Response({"visualization": cleaned_reply})
    except Exception as e:
        print(f"Error generating visualization: {e}")
        return Response({"error": str(e)}, status=500)
    
# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from mongoengine import connect
from django.conf import settings
from .services.agent_service import process_user_query

class CodeAgentView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        user_query = request.data.get("query", "")
        if not user_query:
            return Response({"error": "Missing query"}, status=400)
        try:
            user=request.user.id
            result = process_user_query(user_query,user)
            print("Agent result:", result)
            return Response(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def generate_agent_code_challenge(request):
    """
    Dedicated endpoint for the AgentCode feature.
    Bypasses intent routing and directly calls the 3-question structured batch generator.
    """
    topic = request.data.get("topic")
    if not topic:
        return Response({"error": "Missing topic"}, status=400)
        
    try:
        from .services.agent_service import generate_structured_batch_tool
        from .models import QuestionB, TestCase, CodingStep
        
        user = request.user
        print(f"Generating dedicated AgentCode challenge for topic: {topic}")
        questions_data = generate_structured_batch_tool(topic)
        
        saved_questions = []
        for qdata in questions_data:
            testcases_data = qdata.get("testcases", [])
            if isinstance(testcases_data, str):
                try:
                   testcases_data = json.loads(testcases_data)
                except:
                   testcases_data = []

            testcases = []
            for tc in testcases_data:
                 inp = tc.get("input_data") or tc.get("input") or ""
                 out = tc.get("expected_output") or tc.get("expected") or ""
                 testcases.append(TestCase(input_data=str(inp), expected_output=str(out)))
            
            # --- GUIDED STEPS ---
            steps_data = qdata.get("steps", [])
            steps = []
            for sd in steps_data:
                steps.append(CodingStep(
                    title=sd.get("title", "Progression"),
                    instruction=sd.get("instruction", ""),
                    hint=sd.get("hint", ""),
                    target_logic=sd.get("target_logic", "")
                ))

            qdoc = QuestionB(
                user=user,
                topic=topic,
                title=qdata.get("title", "Practice Question"),
                description=qdata.get("description", "No description"),
                difficulty=qdata.get("difficulty", "medium"),
                testcases=testcases,
                steps=steps
            )
            qdoc.save()
            
            # Ensure qdata sent back contains the steps for frontend state
            qdata["steps"] = steps_data
            saved_questions.append(qdata)
            
        print(f"Successfully generated {len(saved_questions)} questions.")
        print("Generated Questions:", saved_questions)
        return Response({
            "type": "plan", 
            "questions": saved_questions, 
            "topic": topic
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_next_plan_step(request):
    """
    Generates the next step in an existing plan IF it hasn't been generated yet.
    """
    plan_id = request.data.get("plan_id")
    if not plan_id:
        return Response({"error": "Plan ID required"}, status=400)
    
    try:
        from .models import Plan, QuestionB, TestCase
        from .services.agent_service import generate_question_for_step
        
        plan = Plan.objects.get(id=plan_id, user=request.user)
        
        # Determine next index
        current_count = len(plan.questions)
        total_steps = len(plan.plan_content)
        
        if current_count >= total_steps:
             return Response({"message": "Plan completed!", "completed": True}, status=200)
             
        next_step_index = current_count
        first_next_step = plan.plan_content[next_step_index]
        
        # Identify the phase
        target_phase = first_next_step.get("title", "").split(":")[0].strip()
        print(f"Loading next phase batch: {target_phase}")
        
        # Collect all steps belonging to this phase that haven't been generated yet
        steps_to_generate = []
        for i in range(next_step_index, total_steps):
            step = plan.plan_content[i]
            phase = step.get("title", "").split(":")[0].strip()
            if phase == target_phase:
                steps_to_generate.append(step)
            else:
                break # Stop when phase changes
                
        results = []
        for step in steps_to_generate:
            try:
                print(f"Generating Step: {step['title']}")
                qdata = generate_question_for_step(plan.topic, step)
                
                # Save Question
                testcases = []
                for tc in qdata.get("testcases", []):
                        testcases.append(TestCase(input_data=tc.get("input_data"), expected_output=tc.get("expected_output")))
    
                qdoc = QuestionB(
                    user=request.user,
                    topic=plan.topic,
                    title=qdata["title"],
                    description=qdata["description"],
                    difficulty=qdata.get("difficulty", "medium").lower(),
                    testcases=testcases
                )
                qdoc.save()
                
                # Update Plan
                plan.questions.append(str(qdoc.id))
                results.append(qdata)
            except Exception as e:
                print(f"Error generating step {step['title']}: {e}")
        
        plan.save()
        
        # Return list of questions
        return Response({"questions": results, "completed": False, "index": next_step_index}, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user_plans(request):
    """
    Returns a list of saved plans for the user.
    """
    try:
        from .models import Plan
        # Fetch plans sorted by newest first
        plans = Plan.objects.filter(user=request.user).order_by('-created_at')
        
        result = []
        for p in plans:
            # Calculate progress
            total = len(p.plan_content)
            completed = len(p.questions)
            
            result.append({
                "id": str(p.id),
                "topic": p.topic,
                "intent": p.intent,
                "created_at": str(p.created_at),
                "progress": f"{completed}/{total}",
                "completed_count": completed,
                "total_count": total,
                "is_completed": completed >= total and total > 0
            })
            
        return Response(result, status=200)
    except Exception as e:
         return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_assist(request):
    """
    AI Assistant for Coding Page.
    Expects: { "prompt": "...", "code": "...", "model": "..." }
    """
    prompt = request.data.get("prompt", "")
    code_context = request.data.get("code", "")
    history = request.data.get("history", [])
    mode = request.data.get("mode", "chat") # "chat" or "review"
    current_step = request.data.get("current_step") # {title, instruction, target_logic}
    
    if not prompt and mode == "chat":
        return Response({"error": "Prompt is required"}, status=400)
        
    if mode == "review":
        system_prompt = f"""
        You are a strict Python Coding Coach. 
        Your task is to REVIEW the user's current code against the MISSION STEP logic.
        
        MISSION STEP:
        Title: {current_step.get('title')}
        Instruction: {current_step.get('instruction')}
        Target Logic (What must be present): {current_step.get('target_logic')}
        
        CURRENT CODE:
        ```python
        {code_context}
        ```
        
        OUTPUT FORMAT:
        Return JSON ONLY:
        {{
            "passed": boolean,
            "feedback": "If passed: Praise and explain why it's good. If failed: Explain what is missing without giving full code.",
            "next_instruction": "The instruction for the NEXT step if passed, else repeat current."
        }}
        """
    else:
        system_prompt = f"""
        You are an expert Python Coding Tutor.
        The user is working on a coding problem.
        
        Current Code:
        ```python
        {code_context}
        ```
        
        GUIDELINE:
        - If the user asks for a hint, provide a "Hidden Hint" using the tag [REVEAL]...[/REVEAL].
          Example: "Try using the range() function. [REVEAL]for i in range(len(arr)):[/REVEAL]"
        - Predict the next step he has to perform with his code.
        - Be concise. Don't output more than 300 words.
        """
    
    try:
        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
                
        if prompt:
            messages.append({"role": "user", "content": prompt})
        elif mode == "review":
            messages.append({"role": "user", "content": "Review my progress for this step."})

        reply = groq_service.chat(messages)
        
        if reply:
            reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL | re.IGNORECASE).strip()
            
        if mode == "review":
            review_data = clean_json_blocks(reply)
            
            if review_data:
                # Normalize keys to lowercase for consistent frontend handling
                normalized = {str(k).lower(): v for k, v in review_data.items()}
                passed = normalized.get("passed", False)
                feedback = normalized.get("feedback", normalized.get("comment", "Review completed."))
                
                # RECORD MISTAKE IF FAILED
                if not passed:
                    from chatbot.services.mistake_service import mistake_service
                    topic_label = current_step.get('title') if current_step else "Coding Challenge"
                    mistake_service.record_mistake(request.user.email, topic_label, feedback, "code")

                return Response({
                    "passed": passed,
                    "feedback": feedback,
                    "next_instruction": normalized.get("next_instruction", normalized.get("instruction", "Proceed to next step."))
                })
            else:
                # Fallback if AI didn't return valid JSON
                return Response({
                    "passed": False, 
                    "feedback": reply,
                    "next_instruction": "Please fix the current step and try again."
                })

        return Response({"reply": reply})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user_mistakes(request):
    """
    Returns the qualitative mistake log for the dashboard.
    """
    try:
        from chatbot.services.mistake_service import mistake_service
        mistakes = mistake_service.get_recent_mistakes(request.user.email, limit=10)
        data = []
        for m in mistakes:
            data.append({
                "topic": m.topic,
                "mistake": m.mistake_description,
                "source": m.source,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "Unknown"
            })
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
