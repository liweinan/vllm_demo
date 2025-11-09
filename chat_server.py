"""
FastAPI Chat Server - Using LangChain Agent + vLLM
"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import List, Optional, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# LangChain imports - using langchain_classic (based on source code)
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management: startup and shutdown"""
    # Initialize on startup
    try:
        await init_agent()
        logger.info("Chat server started successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield  # Application running
    
    # Cleanup resources on shutdown
    logger.info("Chat server is shutting down...")

app = FastAPI(title="vLLM + LangChain Chat Server", lifespan=lifespan)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Agent instance
agent_executor: Optional[Any] = None
tools: List[Any] = []

# vLLM server configuration
vllm_server_url = os.getenv("VLLM_SERVER_URL", "http://vllm-server:8001/v1")
vllm_model_name = os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

# Request models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    raw_response: str  # Raw complete response
    tools_available: List[str]

# Define tool functions
def add_numbers(a: float, b: float) -> float:
    """
    Calculate the sum of two numbers.
    
    Important: Only use this tool when the user explicitly requests addition calculation. Do not use this tool for greetings, casual chat, or non-mathematical questions.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Sum of the two numbers
    """
    logger.info(f"[Tool] add_numbers(a={a}, b={b})")
    result = a + b
    logger.info(f"[Tool] add_numbers result: {result}")
    return result

def multiply_numbers(a: float, b: float) -> float:
    """
    Calculate the product of two numbers.
    
    Important: Only use this tool when the user explicitly requests multiplication calculation. Do not use this tool for greetings, casual chat, or non-mathematical questions.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Product of the two numbers
    """
    logger.info(f"[Tool] multiply_numbers(a={a}, b={b})")
    result = a * b
    logger.info(f"[Tool] multiply_numbers result: {result}")
    return result

def calculate_expression(expression: str) -> float:
    """
    Calculate a mathematical expression. The expression must only contain numbers and basic operators (+, -, *, /, parentheses).
    
    Important: Only use this tool when the user explicitly requests calculation of a mathematical expression. The expression parameter must be a valid mathematical expression string (e.g., '2+3*4'), not a greeting, text, or other non-mathematical content. Do not use this tool for greetings, casual chat, or non-mathematical questions.
    
    Args:
        expression: Mathematical expression string, must only contain numbers, operators, and parentheses, e.g., '2+3*4', '10/2', etc.
    
    Returns:
        Calculation result as float
    """
    logger.info(f"[Tool] calculate_expression(expression='{expression}')")
    try:
        # Simple safe calculation, only allow numbers and basic operators
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Expression contains invalid characters")
        
        result = eval(expression)
        result_float = float(result)
        logger.info(f"[Tool] calculate_expression result: {result_float}")
        return result_float
    except Exception as e:
        logger.error(f"[Tool] calculate_expression failed: {str(e)}")
        raise ValueError(f"Calculation error: {str(e)}")

async def init_agent():
    """Initialize LangChain Agent"""
    global agent_executor, tools
    
    # 1. Create tool list
    logger.info("Creating tools...")
    tool_add = StructuredTool.from_function(
        func=add_numbers,
        name="add_numbers",
        description="""Calculate the sum of two numbers.

IMPORTANT: Only use this tool when the user explicitly requests addition calculation. For greetings, casual chat, or non-mathematical questions, DO NOT use this tool.

Args:
    a: First number
    b: Second number

Returns:
    Sum of the two numbers"""
    )
    
    tool_multiply = StructuredTool.from_function(
        func=multiply_numbers,
        name="multiply_numbers",
        description="""Calculate the product of two numbers.

IMPORTANT: Only use this tool when the user explicitly requests multiplication calculation. For greetings, casual chat, or non-mathematical questions, DO NOT use this tool.

Args:
    a: First number
    b: Second number

Returns:
    Product of the two numbers"""
    )
    
    tool_calculate = StructuredTool.from_function(
        func=calculate_expression,
        name="calculate_expression",
        description="""Calculate a mathematical expression. The expression must only contain numbers and basic operators (+, -, *, /, parentheses).

IMPORTANT: Only use this tool when the user explicitly requests calculation of a mathematical expression. The expression parameter must be a valid mathematical expression string (e.g., '2+3*4'), not a greeting, text, or other non-mathematical content. For greetings, casual chat, or non-mathematical questions, DO NOT use this tool.

Args:
    expression: Mathematical expression string, must only contain numbers, operators, and parentheses, e.g., '2+3*4', '10/2', etc.

Returns:
    Calculation result as float"""
    )
    
    tools = [tool_add, tool_multiply, tool_calculate]
    logger.info(f"Tools created, total {len(tools)} tools: {[t.name for t in tools]}")
    
    # 2. Connect to vLLM service
    logger.info(f"Connecting to vLLM server: {vllm_server_url}")
    logger.info(f"Model name: {vllm_model_name}")
    
    # Wait for vLLM server to start (retry logic)
    max_retries = 15
    retry_delay = 2  # seconds
    
    llm = None
    for attempt in range(max_retries):
        try:
            # Create ChatOpenAI client to connect to vLLM service
            llm = ChatOpenAI(
                base_url=vllm_server_url,
                api_key="not-needed",  # vLLM doesn't need API key
                model=vllm_model_name,
                temperature=0.1,
                max_tokens=256,
                timeout=30.0,
            )
            
            # Test connection (via simple call)
            logger.debug("Testing vLLM connection...")
            # Note: Not actually calling here, just creating client
            # Actual connection test will happen on first call
            logger.info("vLLM client created successfully")
            break  # Successfully created, exit retry loop
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            if attempt < max_retries - 1:
                logger.info(f"Waiting for vLLM server to start... (attempt {attempt + 1}/{max_retries}, error: {error_msg})")
                await asyncio.sleep(retry_delay)
                continue
            else:
                logger.warning(f"vLLM server connection failed: {error_msg}, will try to continue startup (may not work properly)")
                import traceback
                logger.error(f"vLLM connection detailed error:\n{traceback.format_exc()}")
                # Continue even if connection fails, let Agent initialize, but may not work properly
    
    if llm is None:
        raise RuntimeError("Cannot create vLLM client, please check if vLLM server is running")
    
    # 3. Create ReAct Agent
    logger.info("Creating LangChain ReAct Agent...")
    
    # System prompt clearly guides Agent when to use tools
    # Reference: mcp_server.py tool descriptions to avoid infinite tool calls
    system_prompt = """You are a friendly math calculation assistant.

CRITICAL RULES - Must strictly follow (these rules prevent infinite tool calls):

1. **DO NOT USE TOOLS FOR GREETINGS OR CASUAL CHAT**:
   - If the user says greetings (like "hello", "hi", "你好", etc.), directly reply friendly, absolutely do not call any tools
   - If the user's question doesn't involve math calculation, directly answer, do not call tools
   - Examples of non-math questions: greetings, asking "how are you", asking about the weather, asking what you can do, etc.

2. **ONLY USE TOOLS FOR EXPLICIT MATH CALCULATION REQUESTS**:
   - Only use tools when the user explicitly requests math calculation
   - The user must clearly ask for calculation (e.g., "calculate", "compute", "what is X + Y", "计算", etc.)
   - If the user's intent is unclear, ask for clarification instead of calling tools

3. **CALL EXACTLY ONE TOOL PER REQUEST - THEN STOP**:
   - **Most important**: Call at most ONE tool per request
   - After calling a tool and getting the result, immediately return the final answer and END processing
   - Format: "The answer is [result]" or "Calculation result is [result]" or "答案是 [result]"
   - **DO NOT** call any tools again after getting a result
   - **DO NOT** continue iterating after getting a result

Workflow (strictly follow - this prevents infinite loops):
- Step 1: Analyze user request
  - If it's a greeting or non-math question → directly reply friendly, END (do not use tools)
  - If it's a math calculation request → proceed to Step 2
- Step 2: If calculation is needed, call ONE tool (add_numbers, multiply_numbers, or calculate_expression)
- Step 3: After getting tool result, immediately generate final reply and END
  - Format: "The answer is [result]" or "答案是 [result]"
  - **STOP HERE** - do not proceed further
- **NEVER proceed to Step 4**: Do not call tools again, do not continue iterating

Available tools (only use when math calculation is explicitly requested):
- add_numbers(a, b): Add two numbers. IMPORTANT: Only use when user explicitly requests addition.
- multiply_numbers(a, b): Multiply two numbers. IMPORTANT: Only use when user explicitly requests multiplication.
- calculate_expression(expression): Calculate mathematical expression (only supports numbers and basic operators, like +-*/). IMPORTANT: Only use when user explicitly requests expression calculation.

Correct examples (these are just explanations, do not execute):
- User says "你好" or "hello" → directly reply "你好！我是数学计算助手..." (do not use tools)
- User says "Calculate 5 + 3" → call add_numbers(5, 3) once, get result 8, reply "The answer is 8", END
- User says "4 * 7" → call multiply_numbers(4, 7) once, get result 28, reply "The answer is 28", END
- User says "计算 2+3*4" → call calculate_expression("2+3*4") once, get result 14, reply "答案是 14", END

**ABSOLUTELY FORBIDDEN** (these cause infinite loops):
- Calling any tools for greetings or non-math questions
- Calling any tools again after calling a tool and getting a result
- Continuing iteration after getting tool result
- Calling multiple tools for the same calculation problem
- Calling tools when user intent is unclear (ask for clarification instead)"""
    
    # Use built-in ReAct prompt (doesn't depend on langchain-hub)
    # Note: {tools}, {tool_names}, {agent_scratchpad}, {input} are automatically handled by create_react_agent
    # We only need to partially fill system_prompt
    prompt_template = """You are a friendly math calculation assistant.

{system_prompt}

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you need to answer
Thought: you should think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
    
    prompt = PromptTemplate.from_template(prompt_template)
    # Partially fill system_prompt, other variables are handled by create_react_agent
    prompt = prompt.partial(system_prompt=system_prompt)
    
    # Create ReAct Agent (using langchain_classic, based on source code)
    # According to source code: create_react_agent returns a Runnable, needs to be used with AgentExecutor
    agent = create_react_agent(llm, tools, prompt)
    
    # Create AgentExecutor
    # For small models (1.5B), we need more iterations to handle format errors
    # - Iteration 1: Thought + Action (may have format errors)
    # - Iteration 2: Retry or Observation + Thought
    # - Iteration 3: Final Answer
    # max_iterations=3 allows for one retry if format parsing fails
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=3,  # Allow 3 iterations for small models that may have format issues
        handle_parsing_errors=True,  # Handle parsing errors
        return_intermediate_steps=False,  # Don't return intermediate steps to avoid confusion
        max_execution_time=30,  # Max execution time in seconds
    )
    
    logger.info("Agent initialization complete, tool calls will be automatically handled by LangChain")

async def get_tool_names() -> List[str]:
    """Get list of available tool names"""
    return [tool.name for tool in tools]

@app.get("/health")
async def health():
    """Health check"""
    tool_names = await get_tool_names()
    vllm_available = agent_executor is not None
    
    return {
        "status": "healthy",
        "agent_loaded": agent_executor is not None,
        "vllm_available": vllm_available,
        "tools_count": len(tool_names)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat interface"""
    if agent_executor is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        logger.info(f"Received message: {request.message}")
        
        # Input validation: check if message is empty or too short
        message = request.message.strip()
        if not message or len(message) < 2:
            tool_names = await get_tool_names()
            raw_response = "Input message is too short or empty"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        
        # Use whitelist: only call LLM if contains math calculation keywords
        user_message_lower = message.lower()
        math_keywords = ['计算', '算', '加', '减', '乘', '除', '等于', '等于多少', '+', '-', '*', '/', 'calculate', 'compute', 'add', 'multiply', 'divide']
        has_math_content = any(keyword in user_message_lower for keyword in math_keywords) or \
                          any(char.isdigit() for char in user_message_lower)
        
        # If doesn't contain math content, directly reply friendly, don't call Agent
        if not has_math_content:
            logger.info("No math calculation content detected, directly replying, not calling Agent")
            tool_names = await get_tool_names()
            raw_response = "Hello! I am a math calculation assistant, I can help you with math calculations. Please tell me what you need to calculate?"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        
        # Use LangChain Agent to process request (automatically handles tool calls)
        # AgentExecutor is synchronous, needs to run in async environment
        try:
            # Run synchronous AgentExecutor in async environment
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent_executor.invoke({"input": message})
            )
            
            # Get response text
            if isinstance(result, dict) and "output" in result:
                raw_response = result["output"]
            else:
                raw_response = str(result)
            
        except asyncio.TimeoutError:
            logger.warning("Agent processing timeout")
            tool_names = await get_tool_names()
            raw_response = "Timeout error: Agent processing timeout"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            tool_names = await get_tool_names()
            raw_response = f"Error: {str(e)}"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        
        # Get available tools list
        tool_names = await get_tool_names()
        
        return ChatResponse(
            raw_response=raw_response,
            tools_available=tool_names
        )
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        tool_names = await get_tool_names()
        raw_response = f"Error details: {str(e)}"
        return ChatResponse(
            raw_response=raw_response,
            tools_available=tool_names
        )

@app.get("/tools")
async def list_tools():
    """List available tools"""
    tools_list = []
    for tool in tools:
        tools_list.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": {}  # StructuredTool parameter info is in function signature
        })
    return {"tools": tools_list}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

