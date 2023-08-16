# This is a lightweight console app that uses the semantic kernel to chat with a user.
# Before running the app, create a .env file based on .env.example in the root
# directory. To run the app, simply run: python chat.py

import asyncio

import semantic_kernel as sk
import semantic_kernel.connectors.ai.open_ai as sk_oai

import utils
from plugins.orchestrator import Orchestrator
from plugins.cognitive_search import AzureCognitiveSearch

# Create a semantic kernel
kernel = sk.Kernel()

# Add a chat service
oai_service = utils.azure_openai_chatgpt_settings_from_dot_env()
kernel.add_chat_service(
    "chatgpt",
    sk_oai.AzureChatCompletion(
        oai_service["deployment"], oai_service["endpoint"], oai_service["api_key"]
    ),
)

# Register semantic functions from plugins
plugin_parent_directory = "plugins"
semantic_functions = {}

# Load knowledge base search semantic functions
plugin_dir = "knowledge_base_search"
semantic_function_list = ["create_search_query", "create_answer", "safety_share"]
functions = utils.import_chat_semantic_plugin_from_directory(
    kernel,
    plugin_parent_directory,
    plugin_dir,
    semantic_function_list,
    "system_skprompt.txt",
    "user_skprompt.txt",
    "config.json",
)
semantic_functions.update(functions)

# Load planning semantic functions
plugin_dir = "planning"
semantic_function_list = ["planner"]
functions = utils.import_chat_semantic_plugin_from_directory(
    kernel,
    plugin_parent_directory,
    plugin_dir,
    semantic_function_list,
    "system_skprompt.txt",
    "user_skprompt.txt",
    "config.json",
)
semantic_functions.update(functions)


# Register Azure Cognitive Search plugin
acs_plugin = kernel.import_skill(
    AzureCognitiveSearch(),
    "acs_plugin",
)

# Register Orchestrator plugin
orchestrator_plugin = kernel.import_skill(
    Orchestrator(kernel, semantic_functions["create_answer"]["function_config"]),
    "orchestrator_plugin",
)


async def chat() -> bool:
    try:
        # Get user input
        user_input = input("[User]:>")
    except KeyboardInterrupt:
        print("\n\nExiting chat...")
        return False
    except EOFError:
        print("\n\nExiting chat...")
        return False

    if user_input == "exit":
        print("\n\nExiting chat...")
        return False

    # Pass user input to the orchestrator to process
    result = await orchestrator_plugin["process_request"].invoke_async(user_input)

    # Present the response to the user
    print(f"[Copilot]:> {result}\n")

    return True


async def main() -> None:
    chatting = True
    while chatting:
        chatting = await chat()


if __name__ == "__main__":
    asyncio.run(main())
