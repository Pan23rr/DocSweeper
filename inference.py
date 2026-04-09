import os
import json
import time
from openai import OpenAI
from server.cust_env_environment import DocSweeperEnvironment
from models import DocAction


IMAGE_NAME = os.getenv("IMAGE_NAME") 
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-4o-mini"

def run_inference(task_name: str):

    api_base_url = os.environ.get("API_BASE_URL") or API_BASE_URL
    model_name = os.environ.get("MODEL_NAME") or MODEL_NAME
    hf_token = os.environ.get("HF_TOKEN") or API_KEY

    if not api_base_url:
        raise ValueError("Missinh api base url")
    if not model_name:
        raise ValueError("Missing model name")
    if not hf_token:
        raise ValueError("Missing hf_token")

    client = OpenAI(
        api_key=hf_token,
        base_url=api_base_url
    )
    
    env = DocSweeperEnvironment(task=task_name)
    obs = env.reset()
    done = False
    total_reward = 0.0
    step_count = 0
    

    print(f"[START] task={task_name} model={model_name}")

    system_prompt = f"""
    You are an elite, systematic documentation engineer. You interact with a virtual file system via JSON tool calls.
    
    YOUR CURRENT TASK: '{task_name}'
    - If 'version_bump': Systematically OPEN EVERY SINGLE FILE in the directory tree. Check for 'v1.0.0' or 'v1.00'. If found, use 'edit' to update to 'v2.0.0'.
    - If 'config_migration': Open docker-compose files. Update version to 3.8 and migrate 'links' to 'networks'.
    - If 'broken_links': Find broken relative links and edit them to point to correct paths.
    
    WORKFLOW RULES:
    1. PLAN FIRST: Use the 'thought' field to track which files you have checked and which remain.
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

    while not done:
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
            done = obs.done


            print(f"[STEP] step={step_count} action={action.tool_name} reward={obs.reward:.2f} done={done} thought=\"{thought[:100]}...\"")
            
        except Exception as e:
            obs.terminal_feedback = f"SYSTEM ERROR: {str(e)}. Review the schema rules."
            print(f"[STEP] step={step_count} action=error reward=0.0 done={done} error=\"{str(e)}\"")

    runtime = time.time() - start_time


    final_score = max(0.0, min(1.0, total_reward))
    
    print(f"[END] task={task_name} score={final_score:.2f} total_steps={step_count} runtime_seconds={runtime:.1f}")


if __name__ == "__main__":
    tasks = ["version_bump", "config_migration", "broken_links"]
    for task in tasks:
        run_inference(task)