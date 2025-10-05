from typing import List
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.llms.base import LLM
from orchestrator.query_tools import QueryTool
from orchestrator.ingestion_tools import MultiLevelIngestTool
from orchestrator.rag import GeminiClient
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
    description="Query the Level 2 server for highly specific, technical data.",
)
QueryLevel1 = QueryTool(
    name="QueryLevel1",
    level_url=config.LEVEL1_URL,
    description="Query the Level 1 server for summary or aggregated data.",
)
QueryLevel0 = QueryTool(
    name="QueryLevel0",
    level_url=config.LEVEL0_URL,
    description="Query the Level 0 server for general information or metadata.",
)
IngestTool = MultiLevelIngestTool(
    name="MultiLevelIngestTool",
    description="Ingest a new PDF document from a given file path across all levels.",
)


tools: List[Tool] = [
    Tool(
        name=QueryLevel2.name,
        func=QueryLevel2._run,
        description="Use this tool for queries about specific technical details, raw data, or deep analysis. Input should be a precise question.",
    ),
    Tool(
        name=QueryLevel1.name,
        func=QueryLevel1._run,
        description="Use this tool for queries asking for summaries, overviews, or aggregated results. Input should be a general topic.",
    ),
    Tool(
        name=QueryLevel0.name,
        func=QueryLevel0._run,
        description="Use this tool for queries about metadata, available topics, or general system status. Input should be a broad question.",
    ),
    Tool(
        name=IngestTool.name,
        func=IngestTool._run,
        description="Use this tool when the user asks to 'ingest', 'add', or 'upload' a document. The input must be a valid file path to a PDF.",
    ),
]

# -----------------------------
# Initialize Agent
# -----------------------------

agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant. You have access to several tools to query data servers and ingest documents. Choose the best tool for the user's request.",
        ),
        ("human", "{input}"),
        (
            "placeholder",
            "{agent_scratchpad}",
        ),  # `placeholder` is a special variable that the agent uses to pass memory of previous tool calls and observations. It must be named `agent_scratchpad`.
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

    # Handle query by level
    if level is not None:
        logger.info(f"Forcing tool selection for level {level}.")
        if level == 2:
            return QueryLevel2._run(user_input)
        elif level == 1:
            return QueryLevel1._run(user_input)
        elif level == 0:
            return QueryLevel0._run(user_input)
        else:
            return "Error: Invalid level specified. Must be 0, 1, or 2."
    else:
        # Let agent decide
        logger.info("No level specified. Letting the agent decide the best tool.")
        response = agent_executor.invoke({"input": user_input})
        return response["output"]
