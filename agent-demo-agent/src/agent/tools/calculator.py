from langchain_core.tools import tool
import numexpr


@tool
def calculator(expression: str) -> str:
    """计算数学表达式。支持基本运算、三角函数、对数等。例如: "2**10", "sqrt(144)", "sin(pi/2)" """
    try:
        result = numexpr.evaluate(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算失败: {str(e)}"
