import os
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel
from langchain.chains.openai_functions import create_structured_output_runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Dict,  TypedDict, List 
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
import asyncio
import platform

langchainapikey = 'Is____94293ec3817d4176a0ba4845df938429'
os.environ["LANGCHAIN_TRACING_V2"] = 'false'
os.environ["LANGCHAIN ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = langchainapikey
os.environ["LANGCHAIN_PRO3 ECT"] ="multi-agent"
api_key = "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"#"sk-U5VMyIw3j2Qm04k5IlCCT3BlbkF30PliQZdw4bmlfry94c9s

from bs4 import BeautifulSoup as Soup
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader

# LangGraph docs
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

## state
class AgentState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        keys: A dictionary where each key is a string.
    """
    keys: Dict[str, any]

## Data model
class Agent(BaseModel):
    """Agent output"""
    prefix: str = Field(description="Description of the problem and approach")
    code: str = Field(description="Code block")

## LLM
model = ChatOpenAI(
    model_name="gpt-3.5-turbo", 
    temperature=0, 
    api_key=api_key
    ) 

prompt = ChatPromptTemplate.from_template(
    '''
    **Role**: 
         You are a expert software python programmer. You need to develop python code.
    **Task**: 
        As a programmer, you are required to complete the function. Use a Chain-of-Thought approach to break down the problem, create pseudocode, and then write the code in Python language. Ensure that your code is efficient, readable, and well-commented.
    **Instructions**:
        1.	**Understand and Clarify**: Make sure you understand the task.
        2.	**Algorithm/Method Selection**: Decide on the most efficient way.
        3.	**Pseudocode Creation**: Write down the steps you will follow in pseudocode.
        4.	**Code Generation**: Translate your pseudocode into executable Python code
    **REQUREMENT**:
        {requirement}
    '''
)

llm = create_structured_output_runnable(
    Agent, 
    model, 
    prompt
    )

class Test(BaseModel):
    """Plan to follow in future"""
    Input: List[List] = Field(
        description="Input for Test cases to evaluate the provided code" )
    Output: List[List] = Field(
        description="Expected Output for Test cases to evaluate the provided code" )

test_prompt = ChatPromptTemplate.from_template(
    '''
    **Role**: 
        As a tester, your task is to create Basic and Simple test cases based on requirement and Python Code.
        These test cases should encompass Basic, Edge scenarios to ensure the code's robustness, reliability, and Scalability.
    **Basic Test Cases**:
        **Objective**: 
            Basic and Small scale test cases to validate basic functioning
    **Edge Test Cases**:
        **Objective**: 
            To evaluate the function's behavior under extreme or unusual conditions.
    **Instructions**:
    -	Implement a comprehensive set of test cases based on requirements.
    -	Pay special attention to edge cases as they often reveal hidden bugs.
    -	Only Generate Basics and Edge cases which are small
    -	Avoid generating Large scale and Medium scale test case. Focus only small, basic test-cases
    **REQUREMENT**
        {requirement}
    **Code**
        {code}
    '''
)

tester_llm = create_structured_output_runnable(
    Test, 
    model, 
    test_prompt,
    enforce_function_usage=True,
    return_single=True)

class Execute(BaseModel): 
    """Plan to follow in future"""
    code: str = Field(description="Detailed optmized error-free Python code with test cases assertion" )

execute_prompt = ChatPromptTemplate.from_template(
    """
    You have to add testing layer in the *Python Code* that can help to execute the code. You need to pass only Provided Input as argument and validate if the Given Expected Output is matched. 
    **Instruction**:
    -	Make sure to return the error if the assertion fails
    -	Generate the code that can be execute
    **Code**:
        Code to excecute:
        {code}
    **Input**:
        {input}
    **Expected Output**:
        {output}
    """
)

execute_llm = create_structured_output_runnable(
    Execute, 
    model, 
    execute_prompt,
    enforce_function_usage=True,
    return_single=True)

class Finetune(BaseModel):
    code: str = Field(description="Finetuned Python code to resolve the error" )

finetune_prompt = ChatPromptTemplate.from_template(
    """
    You are expert in Python Debugging. 
    You have to analysis Given Code and Error and generate code that handles the error.
    **Instructions**:
    -	Make sure to generate error free code
    -	Generated code is able to handle the error
    **Code**: 
        {code}
    **Error**: 
        {error}
    """
)

finetune_llm = create_structured_output_runnable(
    Finetune, 
    model,
    finetune_prompt,
    enforce_function_usage=True,
    return_single=True)

def generate(state):
    """
    Generate a node solution based on LangGraph docs and the input requirement
    with optional feedback from code execution tests

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """

    ## state
    state_dict = state["keys"]
    requirement = state_dict["requirement"]

    ## Generation
    if "error" in state_dict:
        print("---RE~GENERATE SOLUTION w/ ERROR FEEOBACK---")
        
        error = state_dict["error"]
        code_solution = state_dict["generation"]
        print(code_solution.code)
        finetuned = finetune_llm.invoke({'code':code_solution.code,
                                         'error':error}) 
        return {"keys": {"generation": finetuned, 
                         "requirement": requirement, 
                         "error": None}}

    else:
        print("---GENERATE SOLUTION---")
        generated = llm.invoke({'requirement':requirement,
                                'context': lambda x: docs}) 
        print(generated.code)
        return {"keys": {"generation": generated, 
                         "requirement": requirement}}

def check_code_execution(state):
    """
    Check code block execution

    Args:
        state (dict): The current graph state
    Returns:
        state (dict): New key added to state, error
    """

    print("---CHECKING CODE EXECUTION---")
    
    ## State
    print("---TESTING---")
    state_dict = state["keys"]
    requirement = state_dict['requirement'] 
    code = state_dict['generation'].code
    tested = tester_llm.invoke({'requirement':requirement,
                                'code':code}) 

    print("---EXECUTING---")
    executed = execute_llm.invoke({"code":code,
                                   "input":tested.Input,
                                   'output':tested.Output})

    error = None 
    try:
        exec(executed.code) 
        print("Code Execution Successful")  
    except Exception as e:
        print('Execution Error')
        error = f"Execution Error : {e}"
        print('sunggwang omil chungil')
    return {"keys": {"generation": executed, 
                     "requirement": requirement,
                     "error": error}}

### Edges

def decide_to_finish(state):
    """
    Determines whether to finish (re-try code 3 times).

    Args:
        state (dict): The current graph state
    Returns:
        str: Next node to call
    """

    print("---DECIDE TO TEST CODE EXECUTION---")
    state_dict = state["keys"]
    error = state_dict["error"]
    
    if error == "None":
        # ALl documents have been filtered check_relevance
        # We will re-generate a new query
        print("---DECISION: TEST CODE EXECUTION---")
        return "end"
    else:
    # We have relevant documents, so generate answer
        print("---DECISION: RE-TRY SOLUTION---")
        return "generate"

# Define a new graph    
workflow = StateGraph(AgentState)

#	Define the nodes
workflow.add_node("generate", generate)  # generate solution
workflow.add_node("check_code_execution", check_code_execution)  # check execution

#	Build graph

# Set the entrypoint
workflow.set_entry_point("generate")

# Add a conditional edge
workflow.add_conditional_edges(
    "check_code_execution",
    decide_to_finish,
    {
        "end": END,
        "generate": "generate",
    },
)

# Add a normal edge
workflow.add_edge("generate", "check_code_execution")

#	Compile
app = workflow.compile()

requirement = "Create a langchain langgraph that comments on GitHub PRs"
# inputs = {"requirement": [HumanMessage(content=requirement)]}
config = {"recursion_limit": 50}

answer = app.invoke({"keys": {"requirement":HumanMessage(content=requirement)}}, 
                    config=config)
print(answer)