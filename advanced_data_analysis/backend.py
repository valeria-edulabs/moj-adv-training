import os
import io
import contextlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Monkeypatch Plotly Figure.show to prevent opening browser windows/tabs
go.Figure.show = lambda self, *args, **kwargs: None
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command

load_dotenv()

# Preload dataset
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products_stock_data.csv")
df_global = pd.read_csv(CSV_PATH)

@tool(response_format="content_and_artifact")
def python_interpreter(code: str) -> tuple[str, any]:
    """Execute Python code using pandas and plotly to analyze data.

    Available libraries:
    - `pd` (pandas)
    - `px` (plotly.express)
    - `go` (plotly.graph_objects)
    
    If your code calculates text statistics or general summaries, print them using `print()`.
    If your code creates a plot, you MUST assign the plotly figure object to a variable named `fig`.
    If your code filters, aggregates, or transforms the data and you want to display the resulting table/dataframe, you MUST assign it to a variable named `result`.
    
    Args:
        code: The Python code to run.
    """
    # Create a local environment with the preloaded df
    local_vars = {
        'df': df_global.copy(),
        'pd': pd,
        'px': px,
        'go': go
    }
    
    stdout = io.StringIO()
    try:
        # Execute the python code and capture standard output
        with contextlib.redirect_stdout(stdout):
            exec(code, globals(), local_vars)
        
        output_text = stdout.getvalue().strip()
        
        # Check for plotly figure in fig or result DataFrame/Series
        fig = local_vars.get('fig')
        result = local_vars.get('result')
        
        artifact = None
        if fig is not None:
            if hasattr(fig, "to_dict"):
                artifact = {
                    "type": "plotly",
                    "data": fig.to_dict()
                }
            else:
                artifact = {
                    "type": "plotly",
                    "data": dict(fig)
                }
        elif result is not None:
            if isinstance(result, pd.Series):
                result = result.to_frame()
            if isinstance(result, pd.DataFrame):
                artifact = {
                    "type": "dataframe",
                    "data": result.to_dict(orient="records")
                }
            
        # Ensure we return a description/content for the model
        if not output_text:
            if result is not None:
                output_text = f"Successfully computed dataframe result with columns: {list(result.columns) if hasattr(result, 'columns') else 'none'}."
            elif fig is not None:
                output_text = "Successfully generated Plotly plot and saved it to 'fig'."
            else:
                output_text = "Code executed successfully with no output."
                
        return output_text, artifact
        
    except Exception as e:
        return f"Error executing code: {str(e)}", None

SYSTEM_PROMPT = """
You are an expert Data Analyst Agent. You have access to a Python interpreter tool (`python_interpreter`) that can execute code on a preloaded pandas DataFrame `df` containing products stock data.


Your task is to analyze the data to answer user questions. You must use the `python_interpreter` tool to perform all calculations, groupings, data filtering, and plotting.

### Guidelines:
1. When asked for calculations or text answers, write python code to compute them. Print the final answer clearly using `print()`.
2. When asked to display a plot or chart, write python code to generate the plot using Plotly Express (`px`) or Plotly Graph Objects (`go`), and assign the figure object to the variable `fig`. Do NOT call `fig.show()` as the Streamlit app will render the figure automatically.
3. When asked to display data in a table or list, write python code to filter/aggregate the DataFrame, and assign the resulting DataFrame or Series to the variable `result`.
4. Remember that you do not see the plot or the DataFrame yourself—you only see the text printed or returned by the tool. However, the user will see the rendered plot or table. Always explain what the plot or table represents and confirm that it has been displayed.
5. If the user rejects the execution of your Python code, do NOT attempt to retry the tool call or generate code again. Instead, politely inform the user that you cannot fulfill their request without approval to run the code.
"""

llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")
memory = MemorySaver()

hitl_middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        "python_interpreter": True
    }
)

data_agent = create_agent(
    model=llm,
    tools=[python_interpreter],
    checkpointer=memory,
    system_prompt=SYSTEM_PROMPT,
    # middleware=[hitl_middleware]
)

def stream(text: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    for chunk in data_agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        stream_mode="updates"
    ):
        yield chunk

def resume_stream(decision: dict, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    for chunk in data_agent.stream(
        Command(resume=decision),
        config=config,
        stream_mode="updates"
    ):
        yield chunk


def save_graph_png():
    data_agent.get_graph().draw_mermaid_png(output_file_path="graph.png")

if __name__ == '__main__':
    save_graph_png()