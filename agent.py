# agent.py
import asyncio
import os
import re
from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from tools.file_parser import parse_uploaded_files
from tools.data_extractor import extract_company_data
from tools.classifier import classify_naf
from tools.eligibility import check_electricity_eligibility, check_gas_eligibility
from tools.calculator import calculate_refund
from tools.document_generator import generate_all_documents
#from google.adk.models.lite_llm import LiteLlm





#ollama_model = LiteLlm(model="ollama_chat/qwen2.5-coder:7b")


# --- Tool definitions (unchanged) ---
def parse_files_tool(file_paths_text: str) -> dict:
    """
    Parse uploaded files given as a text containing file paths separated by commas.
    Example: "C:/path/to/file1.pdf, C:/path/to/file2.pdf"
    Returns a dict {filename: extracted_text}.
    """
    paths = [p.strip() for p in file_paths_text.split(',') if p.strip()]
    paths = list(set(paths))
    return parse_uploaded_files(paths)

def extract_data_tool(texts: dict) -> dict:
    return extract_company_data(texts)

def classify_naf_tool(naf_code: str) -> str:
    return classify_naf(naf_code)

def check_eligibility_tool(profile: str, data: dict) -> dict:
    result = {}
    if profile in ["industrie", "artisan"]:
        result["electricity"] = check_electricity_eligibility(data)
    if data.get("gas_consumption_mwh"):
        result["gas"] = check_gas_eligibility(data)
    return result

def calculate_refund_tool(profile: str, data: dict, eligibility: dict) -> dict:
    return calculate_refund(profile, data, eligibility)

def generate_docs_tool(data: dict, refund: dict) -> dict:
    return generate_all_documents(data, refund)


# --- Tool definitions ---
def parse_files_tool(file_paths_text: str) -> dict:
    paths = [p.strip() for p in file_paths_text.split(',') if p.strip()]
    paths = list(set(paths))
    return parse_uploaded_files(paths)

def extract_data_tool(texts: dict) -> dict:
    return extract_company_data(texts)

def classify_naf_tool(naf_code: str) -> str:
    return classify_naf(naf_code)

def check_eligibility_tool(profile: str, data: dict) -> dict:
    result = {}
    if profile in ["industrie", "artisan"]:
        result["electricity"] = check_electricity_eligibility(data)
    if data.get("gas_consumption_mwh"):
        result["gas"] = check_gas_eligibility(data)
    return result

def calculate_refund_tool(profile: str, data: dict, eligibility: dict) -> dict:
    return calculate_refund(profile, data, eligibility)

def generate_docs_tool(data: dict, refund: dict) -> dict:
    return generate_all_documents(data, refund)





# Wrap tools with FunctionTool
parse_files_tool = FunctionTool(func=parse_files_tool)
extract_data_tool = FunctionTool(func=extract_data_tool)
classify_naf_tool = FunctionTool(func=classify_naf_tool)
check_eligibility_tool = FunctionTool(func=check_eligibility_tool)
calculate_refund_tool = FunctionTool(func=calculate_refund_tool)
generate_docs_tool = FunctionTool(func=generate_docs_tool)

tools = [
    parse_files_tool,
    extract_data_tool,
    classify_naf_tool,
    check_eligibility_tool,
    calculate_refund_tool,
    generate_docs_tool,
]

# --- Agent creation (without function_calling_behavior) ---
agent = LlmAgent(
    name="ExciseAuditAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="""
You are an expert in French energy tax law. You have access to tools that can parse files, extract data, check eligibility, calculate refunds, and generate documents.

Follow this workflow strictly using function calls:

1. Ask the user to provide the full file paths of all required documents (Kbis, electricity invoices, tax returns, technical descriptions, etc.), separated by commas.
2. Once the user provides the paths, call `parse_files_tool` with the paths string.
3. After receiving the parsed texts (a dict), call `extract_data_tool` with that dict.
4. From the extracted data, get the NAF code and call `classify_naf_tool` with it.
5. Then call `check_eligibility_tool` with the profile and data.
6. If eligible, call `calculate_refund_tool` with the profile, data, and eligibility.
7. Finally, call `generate_docs_tool` with the data and refund, and then present the results to the user.

Always use function calls for these steps. Do not output JSON in text. After all tools are called, provide a clear summary to the user.
    """,
    tools=tools,
    
)
# --- Main loop with enhanced event handling ---
async def main():
    runner = InMemoryRunner(agent=agent, app_name="excise_audit")
    session_id = "session_1"
    user_id = "user1"

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    print("Excise Audit Agent ready. Type your messages (or 'exit' or 'quit' to quit).")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        content = Content(role="user", parts=[Part(text=user_input)])

        # Process all events from this turn
        async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content
            ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent (text): {part.text}")
                    elif part.function_call:
                        print(f"[Calling tool: {part.function_call.name} with args {part.function_call.args}]")
                    elif part.function_response:
                        print(f"[Tool response from: {part.function_response.name}]")
                        # Optionally print the response summary
                        response_data = part.function_response.response
                        if isinstance(response_data, dict):
                            print(f"  Response keys: {list(response_data.keys())}")
                        else:
                            print(f"  Response: {str(response_data)[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())