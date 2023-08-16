# This file contains utility functions.

import os

from dotenv import dotenv_values
from semantic_kernel.kernel import Kernel
from semantic_kernel.semantic_functions.chat_prompt_template import ChatPromptTemplate
from semantic_kernel.semantic_functions.prompt_template_config import (
    PromptTemplateConfig,
)
from semantic_kernel.semantic_functions.semantic_function_config import (
    SemanticFunctionConfig,
)
from semantic_kernel.utils.validation import validate_skill_name


def import_chat_semantic_plugin_from_directory(
    kernel: Kernel,
    parent_directory: str,
    plugin_directory_name: str,
    function_directory_list: list,
    system_prompt_file: str = None,
    user_prompt_file: str = "user_skprompt.txt",
    config_file: str = "config.json",
):
    """
    Imports a semantic plugin from a directory.
    """
    plugin = {}
    for function_directory_name in function_directory_list:
        result = import_chat_semantic_function_from_directory(
            kernel,
            parent_directory,
            plugin_directory_name,
            function_directory_name,
            system_prompt_file,
            user_prompt_file,
            config_file,
        )
        plugin[function_directory_name] = result
        print(
            f"Loaded semantic function: {plugin_directory_name}.{function_directory_name}"  # noqa
        )
    return plugin


def import_chat_semantic_function_from_directory(
    kernel: Kernel,
    parent_directory: str,
    plugin_directory_name: str,
    function_directory_name: str,
    system_prompt_file: str = None,
    user_prompt_file: str = "user_skprompt.txt",
    config_file: str = "config.json",
):
    """
    Imports a semantic function from a directory.
    """
    CONFIG_FILE = config_file
    SYSTEM_PROMPT_FILE = system_prompt_file
    USER_PROMPT_FILE = user_prompt_file

    validate_skill_name(plugin_directory_name)

    function_directory = os.path.join(
        parent_directory, plugin_directory_name, function_directory_name
    )

    if not os.path.exists(function_directory):
        raise ValueError(f"plugin directory does not exist: {function_directory}")

    # Check if user prompt file exists
    user_prompt_path = os.path.join(function_directory, USER_PROMPT_FILE)
    if not os.path.exists(user_prompt_path):
        raise ValueError(f"User prompt file does not exist: {user_prompt_path}")

    # Check if config file exists
    config_path = os.path.join(function_directory, CONFIG_FILE)
    if not os.path.exists(config_path):
        raise ValueError(f"Config file does not exist: {config_path}")

    # Create prompt config
    config = PromptTemplateConfig()
    with open(config_path, "r") as config_file:
        config = config.from_json(config_file.read())

    # Load user prompt template
    with open(user_prompt_path, "r") as prompt_file:
        template = ChatPromptTemplate(
            prompt_file.read(), kernel.prompt_template_engine, config
        )

    # Add one-off system prompt to the beginning of the message.
    # Check if system prompt file exists if specified
    if SYSTEM_PROMPT_FILE is not None:
        system_prompt_path = os.path.join(function_directory, SYSTEM_PROMPT_FILE)
        if not os.path.exists(system_prompt_path):
            raise ValueError(f"System prompt file does not exist: {system_prompt_path}")
        else:
            with open(system_prompt_path, "r") as prompt_file:
                template.add_system_message(prompt_file.read())

    # Create semantic function config
    function_config = SemanticFunctionConfig(config, template)

    function = kernel.register_semantic_function(
        skill_name=plugin_directory_name,
        function_name=function_directory_name,
        function_config=function_config,
    )

    result = {"function": function, "function_config": function_config}

    return result


def azure_openai_gpt_settings_from_dot_env():
    """
    Returns the Azure OpenAI GPT model settings from the .env file.
    """
    deployment, api_key, endpoint = None, None, None
    config = dotenv_values("../.env")
    deployment = config.get("AZURE_OPENAI_GPT_DEPLOYMENT", None)
    api_key = config.get("AZURE_OPENAI_API_KEY", None)
    endpoint = config.get("AZURE_OPENAI_ENDPOINT", None)

    # Azure requires the deployment name, the API key and the endpoint URL.
    assert deployment is not None, "Azure OpenAI deployment name not found in .env file"
    assert api_key is not None, "Azure OpenAI API key not found in .env file"
    assert endpoint is not None, "Azure OpenAI endpoint not found in .env file"

    return deployment or "", api_key, endpoint


def azure_openai_chatgpt_settings_from_dot_env():
    """
    Returns the Azure OpenAI ChatGPT model settings from the .env file.
    """
    deployment, api_key, endpoint = None, None, None
    config = dotenv_values("../.env")
    deployment = config.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT", None)
    api_key = config.get("AZURE_OPENAI_API_KEY", None)
    endpoint = config.get("AZURE_OPENAI_ENDPOINT", None)

    assert deployment is not None, "Azure OpenAI deployment name not found in .env file"
    assert api_key is not None, "Azure OpenAI API key not found in .env file"
    assert endpoint is not None, "Azure OpenAI endpoint not found in .env file"

    result = {"deployment": deployment, "api_key": api_key, "endpoint": endpoint}
    return result
