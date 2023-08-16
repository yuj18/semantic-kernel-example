# This plugin is used to orchestrate the execution of a plan.

import ast
import re

from semantic_kernel import Kernel
from semantic_kernel.orchestration.context_variables import ContextVariables
from semantic_kernel.orchestration.sk_context import SKContext
from semantic_kernel.semantic_functions.semantic_function_config import (
    SemanticFunctionConfig,
)
from semantic_kernel.skill_definition import sk_function


class Orchestrator:
    def __init__(
        self,
        kernel: Kernel,
        chat_function_config: SemanticFunctionConfig = None,
    ):
        self._kernel = kernel
        self._chat_function_config = chat_function_config
        self._functions = self._create_available_functions_string(kernel)
        print("Loaded Orchestrator Plugin.")

    def _create_available_functions_string(self, kernel: Kernel):
        """
        Given an instance of the Kernel, find all available functions.
        """
        # Get a dictionary of skill names to all native and semantic functions
        all_functions = kernel.skills.get_functions_view().native_functions
        semantic_functions = kernel.skills.get_functions_view().semantic_functions
        all_functions.update(semantic_functions)
        function_list = [
            skill_name + "." + func.name
            for skill_name in all_functions
            for func in all_functions[skill_name]
        ]

        return function_list

    @sk_function(
        description="Process the request based on an execution plan.",
        name="process_request",
    )
    async def process_request(self, context: SKContext) -> str:
        # Save the original request, to be used to form a plan
        request = context["input"]

        # Generate a step-by-step execution plan based on the request
        planner_func = self._kernel.skills.get_function("planning", "planner")
        planner_func(context=context)

        # Convert the output of the planner into a list
        list_pattern = r"\[.*\]"

        if re.match(list_pattern, context["input"]):
            tasks = ast.literal_eval(context["input"])
        else:
            print(f"No plan found: {context['input']}")
            tasks = []

        plan = {"input": request, "tasks": tasks}
        print("-" * 50)
        print(f"\n  |Backend: Plan|: {tasks}\n")

        # Check if the task list contain unknown functions
        for task in tasks:
            if task not in self._functions:
                return "I am sorry. I could not find an answer to your question."

        # Execute the plan
        result = await self.execute_plan_async(plan, self._kernel)
        print("-" * 50)

        return result

    async def execute_plan_async(self, plan: dict, kernel: Kernel) -> str:
        """
        Given a plan, execute each of the functions within the plan
        from start to finish and output the result.
        """

        # Create a context for the plan
        context = ContextVariables()
        # Add the original request to the context
        context["input"] = plan["input"]
        # Also capture the original request in the user_input variable
        context["user_input"] = plan["input"]

        # Default result
        result = "I am sorry. I could not find an answer to your question."
        # Execute each function in the plan
        for subtask in plan["tasks"]:
            plugin_name, function_name = subtask.split(".")
            sk_function = kernel.skills.get_function(plugin_name, function_name)
            if subtask == "knowledge_base_search.create_answer":
                # If create_answer is used, add a chat history maintenance step
                output = await sk_function.invoke_async(variables=context)
                await self.maintain_chat_history(
                    context["user_input"], 2, output.result
                )
            elif subtask == "knowledge_base_search.safety_share":
                # context["user_input"] = "please share a safety tip"
                output = await sk_function.invoke_async(variables=context)

            else:
                output = await sk_function.invoke_async(variables=context)

            if subtask == "knowledge_base_search.create_search_query":
                print(f"  |Backend: Query KB|: {output.result}\n")

            # Return the output of the last function
            result = output.result

        return result

    async def maintain_chat_history(
        self,
        last_user_input: str,
        num_messages_to_pop: int,
        last_assistant_message: str = "",
    ) -> str:
        """
        Maintain a chat history. This is used to remove the search results
        from user messages.
        """
        if self._chat_function_config is not None:
            for i in range(num_messages_to_pop):
                # Remove the last n messages
                self._chat_function_config.prompt_template._messages.pop()

            # Add the last user message without the search results
            self._chat_function_config.prompt_template.add_user_message(last_user_input)
            # Add the last assistant message
            self._chat_function_config.prompt_template.add_assistant_message(
                last_assistant_message
            )
