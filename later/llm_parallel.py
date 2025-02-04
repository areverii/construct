import streamlit as st
from openai import OpenAI
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up OpenAI client
client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama',  # Required but ignored
)

# Log file setup
LOG_FILE = "manyanswers.log.jsonl"
def log_message(role, content, model):
    timestamp = datetime.now().isoformat()
    log_entry = {"timestamp": timestamp, "role": role, "content": content, "model": model}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        json.dump(log_entry, f)
        f.write("\n")

# Streamlit UI setup
st.set_page_config(page_title="Qwen2.5 Chat (Local Ollama)", layout="wide")
st.title("🤖 Qwen2.5 Chat (Local Ollama)")

# Sidebar for log viewing
with st.sidebar:
    if st.button("View Log"):
        if os.path.exists(LOG_FILE):
            entries = []
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    entries.append(json.loads(line))
            st.session_state["log_view"] = entries
        else:
            st.session_state["log_view"] = []

    if "log_view" in st.session_state:
        st.subheader("Chat Log History")
        log_container = st.container()
        for entry in reversed(st.session_state["log_view"]):
            with log_container:
                st.markdown(f"**{entry['timestamp']} - {entry['model']} ({entry['role']})**: {entry['content']}")
                st.divider()

# Initialize responses list
if "responses" not in st.session_state:
    st.session_state["responses"] = []

# Function to process a single prompt
def process_prompt(prompt, model_choice):
    responses = []
    models_to_call = ["deepseek-r1:7b", "llama3", "qwen2.5-coder"] if model_choice == "all" else [model_choice]

    for model in models_to_call:
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model
            )
            bot_reply = response.choices[0].message.content.strip()
            responses.append({"model": model, "response": bot_reply})

            # Log responses
            log_message("assistant", bot_reply, model)
        except Exception as e:
            st.error(f"Error with model {model}: {str(e)}")

    return prompt, responses

# Load prompts from file
def load_prompts():
    if os.path.exists("prompt_list.txt"):
        with open("prompt_list.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    else:
        st.error("File prompt_list.txt not found.")
        return []

# Main processing logic
def process_prompts(prompt_list, model_choice):
    responses = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_prompt = {executor.submit(process_prompt, prompt, model_choice): prompt for prompt in prompt_list}
        for future in as_completed(future_to_prompt):
            prompt, result = future.result()
            responses.append({"prompt": prompt, "responses": result})
            st.session_state["responses"].append({"prompt": prompt, "responses": result})

    return responses

# User model selection
with st.sidebar:
    st.header("Model Selection")
    model_choice = st.radio(
        "Select Model",
        ["deepseek-r1:7b", "llama3", "qwen2.5-coder", "all"],
        index=3,
    )

# Load prompts on button click
if st.button("Process Prompts"):
    prompt_list = load_prompts()
    process_prompts(prompt_list, model_choice)

# Display chat log history
st.subheader("Chat Log History")
log_container = st.container()
st.write(st.session_state.get('responses', []))

# Add voting functionality
if "upvotes" not in st.session_state:
    st.session_state["upvotes"] = {prompt: 0 for prompt in [resp['prompt'] for resp in st.session_state.get('responses', [])]}

for i, response in enumerate(st.session_state.get('responses', [])):
    with log_container.container():
        st.write(f"**Prompt:** {response['prompt']}")
        for resp in response['responses']:
            st.write(f"**Model:** {resp['model']} -> **Answer:** {resp['response']}")
        if st.button(f"Upvote - Response {i+1}", key=f"upvote_{i}"):
            st.session_state["upvotes"][response["prompt"]] += 1