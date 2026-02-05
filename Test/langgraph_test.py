import os
import json
import re
from typing import TypedDict, Dict, Any
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# --- 1. 环境初始化 ---
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "false"


# --- 2. 状态结构定义 ---
class AgentState(TypedDict):
    student_answer: str
    reference_answer: str
    score: int
    feedback: str
    critic_opinion: str
    is_approved: bool
    # 新增 debug 记录，用于存储路径
    history: list


# --- 3. 调试辅助函数 ---
def debug_log(node_name: str, raw_content: str, parsed_data: dict):
    """专门用于格式化输出 Debug 信息"""
    print(f"\n{'=' * 30} 节点: {node_name} {'=' * 30}")
    print(f"【AI 原始返回】:\n{raw_content.strip()}")
    print(f"【解析后的数据】: {json.dumps(parsed_data, ensure_ascii=False, indent=2)}")
    print(f"{'=' * 70}")


def safe_extract_json(text: str) -> Dict[str, Any]:
    try:
        clean_text = text.strip().replace('```json', '').replace('```', '')
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(clean_text)
    except Exception as e:
        return {}


# --- 4. 智能体节点定义 ---
llm = ChatTongyi(model_name="qwen-max")


def grader_node(state: AgentState):
    prompt = f"针对答案【{state['student_answer']}】评分，参考【{state['reference_answer']}】。返回JSON: {{\"score\": 整数, \"feedback\": \"理由\"}}"

    response = llm.invoke([HumanMessage(content=prompt)])
    data = safe_extract_json(response.content)

    # 打印 Debug 信息
    debug_log("GRADER", response.content, data)

    return {
        "score": data.get("score", 0),
        "feedback": data.get("feedback", "N/A"),
        "history": ["grader"]
    }


def critic_node(state: AgentState):
    prompt = f"复核分数 {state['score']} 是否公正。返回JSON: {{\"is_approved\": bool, \"opinion\": \"理由\"}}"

    response = llm.invoke([HumanMessage(content=prompt)])
    data = safe_extract_json(response.content)

    # 打印 Debug 信息
    debug_log("CRITIC", response.content, data)

    return {
        "is_approved": data.get("is_approved", True),
        "critic_opinion": data.get("opinion", "OK"),
        "history": state.get("history", []) + ["critic"]
    }


def refiner_node(state: AgentState):
    prompt = f"根据建议【{state['critic_opinion']}】修正原分 {state['score']}。返回JSON: {{\"score\": 整数, \"feedback\": \"修正理由\"}}"

    response = llm.invoke([HumanMessage(content=prompt)])
    data = safe_extract_json(response.content)

    # 打印 Debug 信息
    debug_log("REFINER", response.content, data)

    return {
        "score": data.get("score", state['score']),
        "feedback": data.get("feedback", state['feedback']),
        "history": state.get("history", []) + ["refiner"]
    }


# --- 5. 构造工作流图 ---
builder = StateGraph(AgentState)
builder.add_node("grader", grader_node)
builder.add_node("critic", critic_node)
builder.add_node("refiner", refiner_node)

builder.set_entry_point("grader")
builder.add_edge("grader", "critic")


def routing_logic(state: AgentState):
    decision = "end" if state["is_approved"] else "refine"
    print(f"决定路径: {decision.upper()}")
    return decision


builder.add_conditional_edges("critic", routing_logic, {"refine": "refiner", "end": END})
builder.add_edge("refiner", END)

app = builder.compile()

# --- 6. 执行测试 ---
if __name__ == "__main__":
    test_input = {
        "student_answer": "我认为只要写好 Python 就可以了，不用管什么算法复杂度。",
        "reference_answer": "优秀的程序员必须掌握算法复杂度（时间与空间复杂度），以编写高效的代码。"
    }

    print("\n[开始任务执行...]")
    final_output = app.invoke(test_input)

    print("\n" + "#" * 20 + " 任务结束汇总 " + "#" * 20)
    print(f"执行路径: {' -> '.join(final_output['history'])}")
    print(f"最终得分: {final_output['score']}")
    print(f"最终评语: {final_output['feedback']}")