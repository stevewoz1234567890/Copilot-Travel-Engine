from operator import itemgetter
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from typing import Dict, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
import os
from uuid import uuid4

from get_langgraph_doc import load_docs

langchainapikey = 'Is____94293ec3817d4176a0ba4845df938429'
os.environ["LANGCHAIN_TRACING_V2"] = 'false'
os.environ["LANGCHAIN ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = langchainapikey
os.environ["LANGCHAIN_PRO3 ECT"] ="multi-agent"
api_key = "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"

from bs4 import BeautifulSoup as Soup
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader

# LCEL docs
url = "https://python.langchain.com/docs/langgraph/"
loader = RecursiveUrlLoader(url=url,
                           max_depth=20,
                           extractor=lambda x: Soup(x, "html.parser").text
                           )
docs = loader.load()

# Sort the list based on the URLs in 'metadata' -> 'source'
d_sorted = sorted(docs,
                 key=lambda x: x.metadata["source"])
d_reversed = list(reversed(d_sorted))

# Concatenate the 'page_content' of each sorted dictionary
concatenated_content = "\n\n\n --- \n\n\n".join(
    [doc.page_content for doc in d_reversed]
)
docs = concatenated_content

## state

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        keys: A dictionary where each key is a string.
    """

    keys: Dict[str, any]


def generate(state):
    """
    Generate a node solution based on LangGraph docs and the input question
    with optional feedback from code execution tests

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """

    ## state
    state_dict = state["keys"]
    question = state_dict["question"]
    iter = state_dict["iterations"]

    ## Data model
    class agent(BaseModel):
        """agent output"""
        prefix: str = Field(description="Description of the purpose")
        imports: str = Field(description="agent block import statement")
        code: str = Field(description="agent block not including import statements")

    ## LLM
    # model = ChatOpenAI(
    #     temperature=0,
    #     model="gpt-4-0125-preview",
    #     # openai_api_key=OPEN_API_KEY,
    #     streaming=True
    #     )
    model = ChatOpenAI(
        model_name="gpt-3.5-turbo", 
        temperature=0, 
        api_key=api_key
        ) 
    
    # Tool
    agent_tool_oai = convert_to_openai_tool(agent)

    # LLM with tool and enforce invocation
    llm_with_tool = model.bind(
        tools=[agent_tool_oai],
        tool_choice={"type": "function", "function": {"name": "agent"}}
    )

    # Parser
    parser_tool = PydanticToolsParser(tools=[agent])

    ## Prompt
    template = """You are an agent generation with expertise in LangGraph.\n
        Here is a full set of LangGraph documentation:
        \n ------- \n
        {context}
        \n ------- \n
        Answer the user question based on the above provided documentation. \n
        Your responsibility encompasses the complete workflow, incorporating elements such as agents, tools, nodes, state objects, edges, agent executor, and the graph itself, to build a comprehensive LangGraph system.  \n
        The code should be error-free, ready for immediate execution, and should not miss any component necessary for the LangGraph's functionality. \n
        Please ensure the code includes: \n
        Proper import statements for all required libraries and modules.
        A thorough implementation covering agents, tools, nodes, state objects, edges, and the agent executor to represent the entire LangGraph workflow. \n
        Detailed comments throughout the code to explain the logic and flow, ensuring clarity and maintainability. \n
        A clean, organized structure that facilitates understanding and further development. \n
        Here is the user question:
        \n --- --- --- \n
        {question}
    """

    # Prompt
    prompt = PromptTemplate(
        template=template,
        input_variables={"context", "question"},
    )

    # Chain
    chain = (
        {
            "context": lambda x: docs,
            "question": itemgetter("question")
        }
        | prompt
        | llm_with_tool
        | parser_tool
    )

    ## Generation
    if "error" in state_dict:
        print("---RE~GENERATE SOLUTION w/ ERROR FEEOBACK---")
        
        error = state_dict["error"]
        code_solution = state_dict["generation"]

        # Udpate prompt
        addendum = """ \n --- --- --- \n You previously tried to solve this problem. \n Here is your solution:
                    \n -—- --- --- \n {generation} \n --- --- --- \n Here is the resulting error from code
                    execution: \n --- --- ——- \n {error} \n --- --- -— \n Please re-try to answer this.
                    Structure your answer with a description of the code solution. \n Then list the imports.
                    And finally list the functioning code block. Structure your answeg with a description of
                    the code solution. \n Then list the imports. And finally list the functioning code block.
                    \n Here is the user question: \n --- --- --- \n {question}"""
        template = template + addendum

        # Prompt
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question", "generation", "error"],
        )

        # Chain
        chain = (
            {
            "context": lambda x: docs,
            "question": itemgetter("question"),
            "generation": itemgetter("generation"),
            "error": itemgetter("error"),
            }
            | prompt
            | llm_with_tool
            | parser_tool
        )

        code_solution = chain.invoke({"question": question,
                                      "generation": str(code_solution[0]),
                                      "error":error})
    else:
        print("---GENERATE SOLUTION---")

        # Prompt
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        # Chain
        chain = (
            {
                "context": lambda x: docs,
                "question": itemgetter("question"),
            }
            | prompt
            | llm_with_tool
            | parser_tool
        )

        code_solution = chain.invoke({"question": question})
        print(code_solution[0].imports)
        print(code_solution[0].code)
        iter = iter+1
        return {"keys": {"generation": code_solution, "question": question, "iterations": iter}}

def check_code_imports(state):
    """
    Check imports

    Args:
        state (dict): The current graph state
    Returns:
        state (dict): New key added to state, error
    """

    ## State
    print("-—-CHECKING CODE IMPORTS-—-")
    state_dict = state["keys"]
    question = state_dict["question"]
    code_solution = state_dict["generation"]
    imports = code_solution[0].imports
    iter = state_dict["iterations"]

    try:
        # Attempt to execute the imports
        exec(imports)
    except Exception as e:
        print("---COQOE IMPORT CHECK: FAILED---")
        # Catch any error during execution (e.g., ImportError, SyntaxError)
        error = f"Execution error: {e}"
        if "error" in state_dict:
            error_prev_runs = state_dict["error"]
            error = error_prev_runs + "\n --- Most recent run error --- \n" + error
    else:
        print("---COOE IMPORT CHECK: SUCCESS~-~")
        # No errors occurred
        error = "None"
        
    return {"keys": {"generation": code_solution, "question": question, "error": error, "iterations": iter}}

def check_code_execution(state):
    """
    Check code block execution

    Args:
        state (dict): The current graph state
    Returns:
        state (dict): New key added to state, error
    """
    
    ## State
    print("---CHECKING CODE EXECUTION---")
    state_dict = state["keys"]
    question = state_dict["question"]
    code_solution = state_dict["generation"]
    prefix = code_solution[0].prefix
    imports = code_solution[0].imports
    code = code_solution[0].code
    code_block = imports +"\n"+ code
    iter = state_dict["iterations"]

    try:
        # Attempt to execute the code block
        exec(code_block)
    except Exception as e:
        print("---CODE BLOCK CHECK: FAILED---")
        # Catch any error during execution (e.g., ImportError, SyntaxError})
        error = f"Execution error: {e}"
        if "error" in state_dict:
            error_prev_runs = state_dict["error"]
            error = error_prev_runs + "\n --- Most recent run error --- \n" + error
    else:
        print("---CODE BLOCK CHECK: SUCCESS---")
        # No errors occurred
        error = "None"
    
    return {"keys": {"generation": code_solution,
                     "question": question,
                     "error": error,
                     "prefix": prefix,
                     "imports": imports,
                     "iterations":iter,
                     "code": code}}

### Edges

def decide_to_check_code_exec(state):
    """
    Determines whether to test code execution, or re-try answer generation.

    Args:
        state (dict): The current graph state
    Returns;
        str: Next node to call
    """
    print("---DECIDE TO TEST CODE EXECUTION---")
    state_dict = state["keys"]
    question = state_dict["question"]
    code_solution = state_dict["generation"]
    error = state_dict["error"]
    if error == "None":
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        print("---DECISION: TEST CODE EXECUTION---")
        return "check_code_execution"
    else:
        # We have relevant documents, so generate answer
        print("---DECISION: RE-TRY SOLUTION---")
        return "generate"

def decide_to_finish(state):
    """
    Determines whether to finish (re-try code 3 times.

    Args:
        state (dict): The current graph state
    Returns:
        str: Next node to call
    """

    print("---DECIDE TO TEST CODE EXECUTION---")
    state_dict = state["keys"]
    question = state_dict["question"]
    code_solution = state_dict["generation"]
    error = state_dict["error"]
    iter = state_dict["iterations"]
    
    if error == "None" or iter == 3:
        # ALl documents have been filtered check_relevance
        # We will re-generate a new query
        print("---DECISION: TEST CODE EXECUTION---")
        return "end"
    else:
    # We have relevant documents, so generate answer
        print("---DECISION: RE-TRY SOLUTION---")
        return "generate"

workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("generate", generate)  # generate solution
workflow.add_node("check_code_imports", check_code_imports)  # check imports
workflow.add_node("check_code_execution", check_code_execution)  # check execution

# Build graph
workflow.set_entry_point("generate")
workflow.add_edge("generate", "check_code_imports")
workflow.add_conditional_edges(
    "check_code_imports",
    decide_to_check_code_exec,
    {
        "check_code_execution": "check_code_execution",
        "generate": "generate",
    },
)
workflow.add_conditional_edges(
    "check_code_execution",
    decide_to_finish,
    {
        "end": END,
        "generate": "generate",
    },
)

# Compile
app = workflow.compile()

# Test
def test(question="Create a langchain langgraph that comments on GitHub PRs", limit=100):
    config = {"recursion_limit": limit}
    answer = app.invoke({"keys": {"question":question, "iterations":0}}, config=config)
    return answer

test()