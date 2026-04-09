import os
import json
import time
from openai import OpenAI
from server.cust_env_environment import DocSweeperEnvironment
from models import DocAction

IMAGE_NAME = os.getenv("IMAGE_NAME") 
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

# Swapped back to OpenAI defaults
API_BASE_URL = os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-4o-mini"
BENCHMARK_NAME = "doc_sweeper"

def run_inference(task_name: str):
    api_base_url = os.environ.get("API_BASE_URL") or API_BASE_URL
    model_name = os.environ.get("MODEL_NAME") or MODEL_NAME
    hf_token = os.environ.get("HF_TOKEN") or API_KEY

    if not api_base_url:
        raise ValueError("Missing API base url")
    if not model_name:
        raise ValueError("Missing model name")
    if not hf_token:
        raise ValueError("Missing hf_token")

    # Replaced Groq with OpenAI, keeping the timeout fixes!
    client = OpenAI(
        api_key=hf_token,
        base_url=api_base_url,
        timeout=15.0,     # Max 15 seconds per request
        max_retries=1     # Do not get stuck in infinite backoff loops
    )
    
    env = DocSweeperEnvironment(task=task_name)
    obs = env.reset()
    
    done = False
    total_reward = 0.0
    step_count = 0
    rewards_history = []
    MAX_STEPS = 20 # Hard step limit failsafe

    print(f"[START] task={task_name} env={BENCHMARK_NAME} model={model_name}", flush=True)

    system_prompt = f"""
    You are an elite, systematic documentation engineer. You interact with a virtual file system via JSON tool calls.
    
    YOUR CURRENT TASK: '{task_name}'
    - If 'version_bump': Systematically OPEN EVERY SINGLE FILE in the directory tree. Check for 'v1.0.0' or 'v1.00'. If found, use 'edit' to update to 'v2.0.0'.
    - If 'config_migration': Open docker-compose files. Update version to '3.8' and migrate 'links:' to 'networks:'.
    - If 'broken_links': Find broken relative links containing '../old-docs/' and edit them to point strictly to './new-docs/'.
    
    WORKFLOW RULES:
    1. PLAN IN THOUGHT: Use the 'thought' field to reason. NEVER use a tool called "plan". Valid tools are strictly: 'open', 'edit', 'grep', 'done'.
    2. OPEN THEN EDIT: You MUST 'open' a file before you can 'edit' it.
    3. EDIT SAFELY: When editing, use 'old_str' (exact text to replace) and 'new_str'. Do NOT use 'path'.
    4. FINISH: Call 'done' ONLY when you have opened and verified EVERY file in the directory tree.
    
    OUTPUT SCHEMA:
    You MUST output ONLY a single raw JSON object EXACTLY matching this structure:
    {{
        "thought": "<Mandatory step-by-step reasoning>",
        "tool_name": "<MUST be one of: 'open', 'edit', 'grep', 'done'>",
        "path": "<Optional. File path for 'open'>",
        "old_str": "<Optional. Exact match string for 'edit'>",
        "new_str": "<Optional. Replacement string for 'edit'>",
        "search_query": "<Optional. Text to search for 'grep'>"
    }}
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    start_time = time.time()

    while not done and step_count < MAX_STEPS:
        step_count += 1
        current_state_prompt = f"""
        [ENVIRONMENT OBSERVATION]
        Active File: {obs.active_file or 'None'}
        Terminal Feedback: {obs.terminal_feedback}
        Directory Tree: {json.dumps(obs.directory_tree)}
        File Content: {obs.file_content}
        Linter Issues: {obs.issues_detected}
        """
        messages.append({"role": "user", "content": current_state_prompt})
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            raw_reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": raw_reply})
            
            action_json = json.loads(raw_reply)
            if isinstance(action_json, list):
                action_json = action_json[0] if len(action_json) > 0 else {"tool_name": "done"}
                
            thought = action_json.pop("thought", "None")
            
            valid_fields = DocAction.model_fields.keys() 
            safe_kwargs = {k: v for k, v in action_json.items() if k in valid_fields}
            
            action = DocAction(**safe_kwargs)
            obs = env.step(action)
            
            total_reward += obs.reward
            rewards_history.append(obs.reward)
            done = obs.done

            action_str = f"{action.tool_name}" 
            done_str = str(done).lower()
            print(f"[STEP] step={step_count} action={action_str} reward={obs.reward:.2f} done={done_str} error=null", flush=True)
            
        except Exception as e:
            error_msg = str(e).replace('\n', ' ')
            obs.terminal_feedback = f"SYSTEM ERROR: {error_msg}. Review the schema rules."
            rewards_history.append(0.0) 
            
            if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                 done = True 
                 
            done_str = str(done).lower()
            print(f"[STEP] step={step_count} action=error reward=0.00 done={done_str} error=\"{error_msg}\"", flush=True)

    final_score = max(0.0, min(1.0, total_reward))
    success = final_score > 0.0 
    success_str = str(success).lower()
    rewards_str = ",".join(f"{r:.2f}" for r in rewards_history)

    print(f"[END] success={success_str} steps={step_count} score={final_score:.2f} rewards={rewards_str}", flush=True)


if __name__ == "__main__":
    tasks = ["version_bump", "config_migration", "broken_links"]
    for task in tasks:
        run_inference(task)