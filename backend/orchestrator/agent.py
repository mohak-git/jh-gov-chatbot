import json
from typing import List
from langchain.agents import Tool
from orchestrator.query_tools import QueryTool
from orchestrator.ingestion_tools import MultiLevelIngestTool
import orchestrator.config as config
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI


logger = logging.getLogger(__name__)


# -----------------------------
# Instantiate Gemini LLM
# -----------------------------
try:
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        convert_system_message_to_human=True,  # Helps with some prompt compatibility
    )
    logger.info(
        f"Successfully initialized Gemini LLM with model: {config.GEMINI_MODEL}"
    )
except Exception as e:
    logger.error(
        f"Failed to initialize Gemini LLM. Ensure GOOGLE_API_KEY is set. Error: {e}"
    )
    llm = None  # Set to None to prevent further errors

# -----------------------------
# Instantiate Tools
# -----------------------------
QueryLevel2 = QueryTool(
    name="QueryLevel2",
    level_url=config.LEVEL2_URL,
    description="Use for specific, detailed questions about Jharkhand government policies. Best for finding exact figures, clauses, eligibility criteria, or technical specifics from policy documents. This tool queries the most detailed information source.",
)
QueryLevel1 = QueryTool(
    name="QueryLevel1",
    level_url=config.LEVEL1_URL,
    description="Use for broader questions asking for summaries or overviews of a policy. Good for understanding the main points, objectives, or key takeaways of a scheme. This tool queries a summarized version of the documents.",
)
QueryLevel0 = QueryTool(
    name="QueryLevel0",
    level_url=config.LEVEL0_URL,
    description="Use for high-level, general questions. Best for discovering what policies are available on a topic (e.g., 'What policies exist for agriculture?'), or asking about document metadata. This tool queries the highest-level summary.",
)
IngestTool = MultiLevelIngestTool(
    name="MultiLevelIngestTool",
    description="Ingest a new PDF document from a given file path across all levels.",
)


tools: List[Tool] = [
    Tool(
        name=QueryLevel2.name,
        func=QueryLevel2._run,
        description=QueryLevel2.description,
    ),
    Tool(
        name=QueryLevel1.name,
        func=QueryLevel1._run,
        description=QueryLevel1.description,
    ),
    Tool(
        name=QueryLevel0.name,
        func=QueryLevel0._run,
        description=QueryLevel0.description,
    ),
]

# -----------------------------
# Initialize Agent
# -----------------------------

agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                You are an expert assistant for a multi-level Retrieval-Augmented Generation (RAG) system for Jharkhand government policies. Your primary role is to select the correct tool to answer the user's query.

                You have access to three levels of information:
                - Level 2 (QueryLevel2): The most detailed, containing raw text from policy PDFs. Use this for specific, granular questions, if question is topic specifig go for it.
                - Level 1 (QueryLevel1): Contains summaries of the documents. Use this for overview or sub topic related questions.
                - Level 0 (QueryLevel0): Contains very high-level summaries and metadata. Use this to find out what documents are available or for very broad topic queries, when question about overall topic.

                Analyze the user's query and choose the tool that best matches the required level of detail.
                - For "What is the exact subsidy for..." -> Use QueryLevel2.
                - For "Give me a summary of the startup policy..." -> Use QueryLevel1.
                - For "What policies do you have about education?" -> Use QueryLevel0.
                
                Output ONLY one of the following strings (case-sensitive):

                0  
                1  
                2

                NOTHING ELSE.
            """,
        ),
        ("human", "{question}"),
        (
            "placeholder",
            "{agent_scratchpad}",
        ),  # placeholder is a special variable that the agent uses to pass memory of previous tool calls and observations. It must be named agent_scratchpad.
    ]
)


if llm:
    agent = create_tool_calling_agent(llm, tools, agent_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
    )
    logger.info("Agent and Executor initialized successfully.")
else:
    agent_executor = None
    logger.error(
        "Agent Executor could not be created because LLM initialization failed."
    )


def decide_tool(question: str) -> int:
    """Ask the agent which tool to use."""
    if not llm:
        logger.warning("LLM not initialized. Defaulting to QueryLevel1.")
        return 1

    decision = llm.invoke(agent_prompt.format_messages(question=question))
    tool_name = int(decision.content.strip())

    valid_tools = [0, 1, 2]
    if tool_name not in valid_tools:
        logger.warning(
            f"Invalid tool decision '{tool_name}', defaulting to QueryLevel1."
        )
        tool_name = 1

    logger.info(f"Tool selected by LLM: QueryLevel{tool_name}")
    return tool_name


def run_query(user_input: str, level: int = None, action: str = "query"):
    """
    Runs a query or ingestion based on `action`.

    Args:
        user_input: The user's query or file path(s) for ingestion.
        level: Optional integer (0, 1, 2) to force a specific query tool.
        action: 'query' (default) or 'ingest'.
    """
    if not agent_executor and action == "query":
        return (
            "Error: Agent Executor is not available. Please check LLM initialization."
        )

    # Handle ingestion=
    if action == "ingest":
        try:
            return IngestTool._run(user_input)
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return f"Ingestion failed: {e}"

    tool_map = {0: QueryLevel0, 1: QueryLevel1, 2: QueryLevel2}

    # Handle query by level
    if level is not None:
        logger.info(f"Forcing tool selection for level {level}.")
        tool = tool_map.get(level)
        if not tool:
            return "Error: Invalid level specified. Must be 0, 1, or 2."
    else:
        # Let agent decide
        logger.info("No level specified. Letting the agent decide the best tool.")
        tool_name = decide_tool(user_input)
        tool = tool_map.get(tool_name)

    if tool:
        return tool._run(user_input)

    return {"answer": "Error: Tool selection failed", "citations": [], "prompt": None}
