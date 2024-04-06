import os
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel
from langchain.chains.openai_functions import create_structured_output_runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Dict, Optional, TypedDict, List 

langchainapikey = 'Is____94293ec3817d4176a0ba4845df938429'
os.environ["LANGCHAIN_TRACING_V2"] = 'false'
os.environ["LANGCHAIN ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = langchainapikey
os.environ["LANGCHAIN_PRO3 ECT"] ="multi-agent"
api_key = "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"#"sk-U5VMyIw3j2Qm04k5IlCCT3BlbkF30PliQZdw4bmlfry94c9s

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=1, api_key=api_key) 

class Code(BaseModel):
    """Plan to follow in future"""

    code: str = Field(
        description="Detailed optmized error-free Python code on the provided requirements"
    )

code_gen_prompt = ChatPromptTemplate.from_template(
'''**Role**: You are a expert software python programmer. You need to develop python code
**Task**: As a programmer, you are required to complete the function. Use a Chain-of-Thought approach to break down the problem, create pseudocode, and then write the code in Python language. Ensure that your code is efficient, readable, and well-commented.
**Instructions**:
1.	**Understand and Clarify**: Make sure you understand the task.
2.	**Algorithm/Method Selection**: Decide on the most efficient way.
**Instructions**:
1.	**Understand and Clarify**: Make sure you understand the task.
2.	**Algorithm/Method Selection**: Decide on the most efficient way.
3.	**Pseudocode Creation**: Write down the steps you will follow in pseudocode.
4.	**Code Generation**: Translate your pseudocode into executable Python code
*REQURIEMENT*: {requirement}''' )

coder = create_structured_output_runnable(
    Code, llm, code_gen_prompt )

#	code_ = coder.invoke({'requirement':'Generate fibbinaco series’})
class Test(BaseModel):
    """Plan to follow in future"""
    Input: List[List] = Field(
        description="Input for Test cases to evaluate the provided code" )
    Output: List[List] = Field(
        description="Expected Output for Test cases to evaluate the provided code" )

test_gen_prompt = ChatPromptTemplate.from_template(
'''**Role**: As a tester, your task is to create Basic and Simple test cases based on provided Requirement and Python Code.
These test cases should encompass Basic, Edge scenarios to ensure the code's robustness, reliability, and Jcalability.
**1. Basic Test Cases**:
-	**Objective**: Basic and Small scale test cases to validate basic functioning
**2. Edge Test Cases**:
-	**Objective**: To evaluate the function's behavior under extreme or unusual conditions.
**Instructions**:
-	Implement a comprehensive set of test cases based on requirements.
-	Pay special attention to edge cases as they often reveal hidden bugs.
-	Only Generate Basics and Edge cases which are small
-	Avoid generating Large scale and Medium scale test case. Focus only small, basic test-cases
*REQURIEMENT*
{requirement}
**Code**
{code}
'''
)
tester_agent = create_structured_output_runnable(
    Test, llm, test_gen_prompt
)
# print(code_.code)
# test_ = testeragent.invoke({’requirement'Generate fibbinaco series','code':code.code})
class ExecutableCode(BaseModel): 
    """Plan to follow in future"""
    code: str = Field(
        description="Detailed optmized error-free Python code with test cases assertion" )

python_execution_gen = ChatPromptTemplate.from_template(
"""You have to add testing layer in the *Python Code* that can help to execute the code. You need to pass only Provided Input as argument and validate if the Given Expected Output is matched. *Instruction*:
-	Make sure to return the error if the assertion fails
-	Generate the code that can be execute
Python Code to excecute:
*	Python Code*:{code}
Input and Output For Code:
*	Input*:{input}
*Expected Output*:{output}"""
)

execution = create_structured_output_runnable(
    ExecutableCode, llm, python_execution_gen)

class RefineCode(BaseModel):
    code: str = Field(
        description="Optimized and Refined Python code to resolve the error" )

python_refine_gen = ChatPromptTemplate.from_template(
"""You are expert in Python Debugging. You have to analysis Given Code and Error and generate code that handles the error
*Instructions*:
-	Make sure to generate error free code
-	Generated code is able to handle the error
*Code*: {code}
*Error*: {error}"""
)

refine_code = create_structured_output_runnable(
    RefineCode, llm, python_refine_gen
)

class AgentCoder(TypedDict):
    requirement: str
    code: str
    tests: Dict[str, any]
    errors: Optional[str]

def programmer(state):
    print(f'Entering in Programmer')
    requirement = state['requirement']
    code_ = coder.invoke({'requirement':requirement}) 
    print("requirements", requirement, "...........",	code_ )
    return {'code':code_.code}

def debugger(state):
    print(f'Entering in Debugger')
    errors = state['errors']
    code = state['code']
    refine_code_ = refine_code.invoke({'code':code,'error':errors}) 
    return {'code':refine_code_.code,'errors':None}

def executer(state):
    print(f'Entering in Executer') 
    tests = state['tests'] 
    input_ = tests['input'] 
    output_ = tests['output'] 
    code = state['code']
    executable_code = execution.invoke({"code":code,"input":input_,'output':output_})
    #print(f"Executable Code - {executable_code.code}") 
    error = None 
    try:
        exec(executable_code.code) 
        print("Code Execution Successful")  
    except Exception as e:
        print('Found Error While Running')
        error = f"Execution Error : {e}"
    return {'code':executable_code.code,'errors':error}

def tester(state):
    print(f'Entering in Tester') 
    requirement = state['requirement'] 
    code = state['code'] 
    tests = tester_agent.invoke({'requirement':requirement,'code':code}) 
    #tester.invoke({’requirement’:'Generate fibbinaco series','code':code_.code}) 
    return {'tests':{'input':tests.Input,'output':tests.Output}}
def decide_to_end(state):
    print(f'Entering in Decide to End') 
    if state['errors']:
        return 'debugger'
    else: return 'end'

from langgraph.graph import END, StateGraph
workflow = StateGraph(AgentCoder)
#	Define the nodes
workflow.add_node("programmer", programmer)
workflow.add_node("debugger", debugger)
workflow.add_node("executer", executer)
workflow.add_node("tester", tester)
#workflow.add_node('dec ide_to_end’,dec ide_to_end)
#	Build graph
workflow.set_entry_point("programmer")
workflow.add_edge("programmer", "tester")
workflow.add_edge("debugger", "executer") 
workflow.add_edge("tester", "executer") 
# workflow.add_edge("executer", "decide_to_end")
workflow.add_conditional_edges(
    "executer", 
    decide_to_end, 
    {
    "end": END,
    "debugger": "debugger",
    },
)
#	Compile
app = workflow.compile()
from langchain_core.messages import HumanMessage
#	requirement = ..Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice.You can return the answer in any order."""
requirement = "create a python agent code that generates langgraph agent"
config = {"recursion_limit": 50}
inputs = {"requirement": requirement}
running_dict = {}

async def process_events():
    async for event in app.astream(inputs, config=config):
        for k, v in event.items(): 
            running_dict[k] = v 
            if k != "__end__":
                print(v)
                print ('---------' *20)
import asyncio
import platform
if platform.system() == 'Windows':
   asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
#    asyncio.get_event_loop().run_until_complete(process_events())
   asyncio.run(process_events())



