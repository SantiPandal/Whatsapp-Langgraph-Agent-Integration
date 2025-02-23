import os
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from typing_extensions import TypedDict

from app.config.config import setup_model
from app.config.logging import logger
from app.src.wppconnect.api import send_message
from app.utils.graph_utils import generate_thread_id, process_chunks, print_graph
from system_prompt import prompt

# Initialize dotenv to load environment variables
load_dotenv()


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State):
        while True:
            result = self.runnable.invoke(state)
            if (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", prompt),
        ("placeholder", "{messages}"),
    ]
)

llm_config = {
    "provider": "groq",
    "model": "llama-3.3-70b-specdec",
    "temperature": 0.6,
}

llm_model = setup_model(llm_config)


assistant_runnable = primary_assistant_prompt | llm_model


builder = StateGraph(State)


# Define nodes: these do the work
builder.add_node("assistant", Assistant(assistant_runnable))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)


## TO PRINT THE GRAPH
# from langgraph.checkpoint.memory import MemorySaver

# checkpoint = MemorySaver()
# graph = builder.compile(checkpointer=checkpoint)

# print_graph(graph)


async def main(phone_number, message):
    try:
        async with AsyncConnectionPool(
            conninfo=os.getenv("PSQL_CONNECTION_STRING"),
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        ) as pool, pool.connection() as conn:
            checkpointer = AsyncPostgresSaver(conn)

            # await checkpointer.setup() # FIRST EXECUTION ONLY

            graph = builder.compile(checkpointer=checkpointer)


            thread_id = generate_thread_id(phone_number)

            config = {
                "configurable": {},
            }

            config["configurable"]["thread_id"] = thread_id
            config["configurable"]["phone_number"] = phone_number

            logger.info(f"Thread ID: {thread_id}")

            input_data = {"messages": [{"role": "user", "content": message}]}

            async for chunk in graph.astream(
                input=input_data, config=config, stream_mode="updates"
            ):
                process_chunks(chunk, phone_number)
    except:
        custom_message = """Unfortunately, an internal error has occurred in our system. 😕 Please try again later."""
        send_message(custom_message, phone_number)