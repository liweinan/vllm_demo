"""
FastAPI Chat服务器 - 使用LangChain Agent + vLLM
"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import List, Optional, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# LangChain 导入 - 使用 langchain_classic（根据源代码）
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动和关闭"""
    # 启动时初始化
    try:
        await init_agent()
        logger.info("Chat服务器启动成功")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise
    
    yield  # 应用运行中
    
    # 关闭时清理资源
    logger.info("Chat服务器正在关闭...")

app = FastAPI(title="vLLM + LangChain Chat Server", lifespan=lifespan)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局Agent实例
agent_executor: Optional[Any] = None
tools: List[Any] = []

# vLLM服务器配置
vllm_server_url = os.getenv("VLLM_SERVER_URL", "http://vllm-server:8001/v1")
vllm_model_name = os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

# 请求模型
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    raw_response: str  # 原始完整响应
    tools_available: List[str]

# 定义工具函数
def add_numbers(a: float, b: float) -> float:
    """
    计算两个数字的加法。
    
    重要：仅在用户明确要求进行加法计算时使用此工具。对于问候、闲聊或非数学问题，不要使用此工具。
    
    Args:
        a: 第一个数字
        b: 第二个数字
    
    Returns:
        两个数字的和
    """
    logger.info(f"[Tool] add_numbers(a={a}, b={b})")
    result = a + b
    logger.info(f"[Tool] add_numbers 结果: {result}")
    return result

def multiply_numbers(a: float, b: float) -> float:
    """
    计算两个数字的乘法。
    
    重要：仅在用户明确要求进行乘法计算时使用此工具。对于问候、闲聊或非数学问题，不要使用此工具。
    
    Args:
        a: 第一个数字
        b: 第二个数字
    
    Returns:
        两个数字的乘积
    """
    logger.info(f"[Tool] multiply_numbers(a={a}, b={b})")
    result = a * b
    logger.info(f"[Tool] multiply_numbers 结果: {result}")
    return result

def calculate_expression(expression: str) -> float:
    """
    计算数学表达式。表达式必须只包含数字和基本运算符（+、-、*、/、括号）。
    
    重要：仅在用户明确要求计算数学表达式时使用此工具。expression 参数必须是有效的数学表达式字符串（如 '2+3*4'），不能是问候语、文本或其他非数学内容。对于问候、闲聊或非数学问题，不要使用此工具。
    
    Args:
        expression: 数学表达式字符串，必须只包含数字、运算符和括号，例如 '2+3*4'、'10/2' 等
    
    Returns:
        计算结果的浮点数
    """
    logger.info(f"[Tool] calculate_expression(expression='{expression}')")
    try:
        # 简单的安全计算，只允许数字和基本运算符
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("表达式包含非法字符")
        
        result = eval(expression)
        result_float = float(result)
        logger.info(f"[Tool] calculate_expression 结果: {result_float}")
        return result_float
    except Exception as e:
        logger.error(f"[Tool] calculate_expression 失败: {str(e)}")
        raise ValueError(f"计算错误: {str(e)}")

async def init_agent():
    """初始化LangChain Agent"""
    global agent_executor, tools
    
    # 1. 创建工具列表
    logger.info("正在创建工具...")
    tool_add = StructuredTool.from_function(
        func=add_numbers,
        name="add_numbers",
        description="计算两个数字的加法。仅在用户明确要求进行加法计算时使用。参数：a (float): 第一个数字, b (float): 第二个数字"
    )
    
    tool_multiply = StructuredTool.from_function(
        func=multiply_numbers,
        name="multiply_numbers",
        description="计算两个数字的乘法。仅在用户明确要求进行乘法计算时使用。参数：a (float): 第一个数字, b (float): 第二个数字"
    )
    
    tool_calculate = StructuredTool.from_function(
        func=calculate_expression,
        name="calculate_expression",
        description="计算数学表达式。表达式必须只包含数字和基本运算符（+、-、*、/、括号）。仅在用户明确要求计算数学表达式时使用。参数：expression (str): 数学表达式字符串，例如 '2+3*4'"
    )
    
    tools = [tool_add, tool_multiply, tool_calculate]
    logger.info(f"工具创建完成，共 {len(tools)} 个工具: {[t.name for t in tools]}")
    
    # 2. 连接到vLLM服务
    logger.info(f"正在连接vLLM服务器: {vllm_server_url}")
    logger.info(f"模型名称: {vllm_model_name}")
    
    # 等待vLLM服务器启动（重试逻辑）
    max_retries = 15
    retry_delay = 2  # 秒
    
    llm = None
    for attempt in range(max_retries):
        try:
            # 创建ChatOpenAI客户端连接vLLM服务
            llm = ChatOpenAI(
                base_url=vllm_server_url,
                api_key="not-needed",  # vLLM不需要API key
                model=vllm_model_name,
                temperature=0.1,
                max_tokens=256,
                timeout=30.0,
            )
            
            # 测试连接（通过简单的调用）
            logger.debug("测试vLLM连接...")
            # 注意：这里不实际调用，只是创建客户端
            # 实际连接测试会在第一次调用时进行
            logger.info("vLLM客户端创建成功")
            break  # 成功创建，退出重试循环
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            if attempt < max_retries - 1:
                logger.info(f"等待vLLM服务器启动... (尝试 {attempt + 1}/{max_retries}, 错误: {error_msg})")
                await asyncio.sleep(retry_delay)
                continue
            else:
                logger.warning(f"vLLM服务器连接失败: {error_msg}，将尝试继续启动（可能无法正常工作）")
                import traceback
                logger.error(f"vLLM连接详细错误:\n{traceback.format_exc()}")
                # 即使连接失败也继续，让Agent初始化，但可能无法正常工作
    
    if llm is None:
        raise RuntimeError("无法创建vLLM客户端，请检查vLLM服务器是否运行")
    
    # 3. 创建ReAct Agent
    logger.info("正在创建LangChain ReAct Agent...")
    
    # System prompt 明确指导 Agent 何时使用工具
    system_prompt = """你是一个友善的数学计算助手。

CRITICAL RULES - 必须严格遵守：
1. 如果用户说的是问候语（如"你好"、"hello"、"hi"等），直接友好回复，绝对不要调用任何工具
2. 如果用户的问题不涉及数学计算，直接回答，不要调用工具
3. 只有在用户明确要求进行数学计算时，才使用工具
4. **最重要**：每次请求最多只调用一次工具。调用工具得到结果后，必须立即返回最终答案并结束处理，绝对不要再调用任何工具或进行任何迭代

工作流程（严格遵守）：
- 步骤1：分析用户请求，决定是否需要计算
- 步骤2：如果需要计算，调用一次工具（add_numbers、multiply_numbers 或 calculate_expression）
- 步骤3：得到工具结果后，立即生成最终回复并结束，格式为："答案是 [结果]" 或 "计算结果为 [结果]"
- **绝对不要进入步骤4**：不要再次调用工具，不要继续迭代

可用工具（仅在需要数学计算时使用，且每种计算只能调用一次）：
- add_numbers(a, b): 两数相加
- multiply_numbers(a, b): 两数相乘  
- calculate_expression(expression): 计算数学表达式（仅支持数字和基本运算符，如 +-*/）

正确示例（这些只是说明，不要执行）：
- 如果用户说问候语 → 直接友好回复，不使用工具
- 如果用户说"计算 X + Y" → 调用一次 add_numbers(X, Y)，得到结果后立即回复并结束
- 如果用户说"X * Y" → 调用一次 multiply_numbers(X, Y)，得到结果后立即回复并结束
- 如果用户给出数学表达式字符串 → 调用一次 calculate_expression(表达式)，得到结果后立即回复并结束

**绝对禁止**：
- 调用工具后再次调用任何工具
- 在得到工具结果后继续迭代
- 对同一个计算问题调用多个工具"""
    
    # 使用内置的 ReAct prompt（不依赖 langchain-hub）
    # 注意：{tools}, {tool_names}, {agent_scratchpad}, {input} 由 create_react_agent 自动处理
    # 我们只需要部分填充 system_prompt
    prompt_template = """你是一个友善的数学计算助手。

{system_prompt}

你有访问以下工具：

{tools}

使用以下格式：

Question: 需要回答的输入问题
Thought: 你应该思考要做什么
Action: 要采取的行动，应该是 [{tool_names}] 中的一个
Action Input: 行动的输入
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始输入问题的最终答案

开始！

Question: {input}
Thought: {agent_scratchpad}"""
    
    prompt = PromptTemplate.from_template(prompt_template)
    # 部分填充 system_prompt，其他变量由 create_react_agent 处理
    prompt = prompt.partial(system_prompt=system_prompt)
    
    # 创建ReAct Agent（使用 langchain_classic，根据源代码）
    # 根据源代码：create_react_agent 返回一个 Runnable，需要配合 AgentExecutor 使用
    agent = create_react_agent(llm, tools, prompt)
    
    # 创建AgentExecutor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=3,  # 最大迭代次数，避免响应时间过长
        handle_parsing_errors=True,  # 处理解析错误
    )
    
    logger.info("Agent初始化完成，工具调用将由LangChain自动处理")

async def get_tool_names() -> List[str]:
    """获取可用工具名称列表"""
    return [tool.name for tool in tools]

@app.get("/health")
async def health():
    """健康检查"""
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
    """聊天接口"""
    if agent_executor is None:
        raise HTTPException(status_code=500, detail="Agent未初始化")
    
    try:
        logger.info(f"收到消息: {request.message}")
        
        # 输入验证：检查消息是否为空或过短
        message = request.message.strip()
        if not message or len(message) < 2:
            tool_names = await get_tool_names()
            raw_response = "输入消息过短或为空"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        
        # 使用白名单：包含"加减乘除计算"的才调用大模型
        user_message_lower = message.lower()
        math_keywords = ['计算', '算', '加', '减', '乘', '除', '等于', '等于多少', '+', '-', '*', '/', 'calculate', 'compute', 'add', 'multiply', 'divide']
        has_math_content = any(keyword in user_message_lower for keyword in math_keywords) or \
                          any(char.isdigit() for char in user_message_lower)
        
        # 如果不包含数学内容，直接友好回复，不调用 Agent
        if not has_math_content:
            logger.info("未检测到数学计算内容，直接回复，不调用 Agent")
            tool_names = await get_tool_names()
            raw_response = "你好！我是一个数学计算助手，可以帮助你进行数学计算。请告诉我你需要计算什么？"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        
        # 使用LangChain Agent处理请求（自动处理工具调用）
        # AgentExecutor 是同步的，需要在异步环境中运行
        try:
            # 在异步环境中运行同步的AgentExecutor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent_executor.invoke({"input": message})
            )
            
            # 获取响应文本
            if isinstance(result, dict) and "output" in result:
                raw_response = result["output"]
            else:
                raw_response = str(result)
            
        except asyncio.TimeoutError:
            logger.warning("Agent 处理超时")
            tool_names = await get_tool_names()
            raw_response = "超时错误: Agent 处理超时"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        except Exception as e:
            logger.error(f"Agent执行错误: {e}", exc_info=True)
            tool_names = await get_tool_names()
            raw_response = f"错误: {str(e)}"
            return ChatResponse(
                raw_response=raw_response,
                tools_available=tool_names
            )
        
        # 获取可用工具列表
        tool_names = await get_tool_names()
        
        return ChatResponse(
            raw_response=raw_response,
            tools_available=tool_names
        )
    except Exception as e:
        logger.error(f"处理请求时出错: {e}", exc_info=True)
        tool_names = await get_tool_names()
        raw_response = f"错误详情: {str(e)}"
        return ChatResponse(
            raw_response=raw_response,
            tools_available=tool_names
        )

@app.get("/tools")
async def list_tools():
    """列出可用工具"""
    tools_list = []
    for tool in tools:
        tools_list.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": {}  # StructuredTool 的参数信息在函数签名中
        })
    return {"tools": tools_list}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

