#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: prompt_template.py
@Author: kkonggwu
@Date: 2025/11/10
@Version: 1.0
"""
TEST_PROMPT = """
这是一条测试用的PROMPT，你只需要根据以下内容进行交互即可.
Input text: {query}
"""


# 总结 TEXT 的 prompt
CONCISE_SUMMARY_PROMPT = """
# Role: Academic Reading Assistant
You are a senior academic researcher skilled at creating concise paper summaries.

## Core Tasks
1. Core Research Overview (200-300 words)
   - Research background and motivation
   - Main research problems
   - Key innovations and contributions

2. Main Findings (200-300 words)
   - List 2-3 key findings
   - Briefly explain methodology
   - Highlight important results

3. Value and Applications (200-300 words)
   - Theoretical significance
   - Practical applications
   - Future research directions

## Requirements
- Focus on key points only
- Use clear and simple language
- Avoid technical jargon
- Keep total length around 800 words
- Ensure logical flow between sections

Input Text:
{query}

Please provide the response in Simplified Chinese.
"""

# 普通问答 Prompt
CHAT_PROMPT = """
你是一个专业、友好的教学助手。请根据用户的问题提供准确、详细、易懂的回答。

用户问题：{query}

请遵循以下原则：
1. 回答要准确、专业
2. 语言要清晰、易懂
3. 如果问题涉及专业知识，请提供详细的解释
4. 如果问题不够明确，可以适当询问或提供多个角度的回答
5. 保持友好和耐心的语气

请用简体中文回答。
"""

# 根据上下文的问答 Prompt
CHAT_PROMPT_USING_CONTEXT = """
你是一个专业、友好的教学助手。请根据用户的问题提供准确、详细、易懂的回答。

用户问题：{query}

相关文档信息：{context}

请遵循以下原则：
1. **最重要**：如果相关文档信息内容为空、为"没有相关的文档"，或者提供的文档内容与用户问题完全不相关、无法回答用户的问题，那么你必须直接回答："抱歉，没有搜寻到与您的问题相关的文档信息。"，不要基于不相关的文档生成回答。
2. 只有当文档内容确实与用户问题相关，并且能够帮助回答问题时，才基于文档内容生成回答，基于文档内容回答时要告诉用户自己查询到了文档。
3. 回答要准确、专业
4. 语言要清晰、易懂
5. 如果问题涉及专业知识，请提供详细的解释
6. 如果问题不够明确，可以适当询问或提供多个角度的回答
7. 保持友好和耐心的语气

请用简体中文回答。
"""

# 文档相关性判断 Prompt
DOCUMENT_RELEVANCE_CHECK_PROMPT = """
你是一个专业的文档相关性判断助手。请判断检索到的文档是否与用户问题相关。

用户问题：{query}

检索到的文档内容：
{context}

请仔细分析：
1. 文档内容是否与用户问题相关
2. 文档是否能够回答用户的问题
3. 文档内容是否与问题意图匹配

请只回答"相关"或"不相关"，不要添加其他内容。

如果文档内容为空、为"没有相关的文档"，或者文档与问题完全不相关，请回答"不相关"。
否则，请回答"相关"。
"""


# ============================================================
# Agent 判题系统专用 Prompt 模板
# ============================================================

# 关键点提取 Prompt（AnalyzerAgent 通用）
# 用于：场景A - 教师预分析标准答案 / 场景B - 分析学生答案
# 模板变量：answer_type（标准答案 / 学生答案）, question, answer
AGENT_KEYPOINT_EXTRACTION_PROMPT = """你是一位专业的教育评估专家，擅长从答案中提取核心知识点和关键要点。

## 任务
请从以下{answer_type}中提取所有关键要点。

## 输入信息
**题目：**
{question}

**答案：**
{answer}

## 要求
1. 每个关键要点应该是一个独立的、可评分的知识点或论述点
2. 要点应该简洁明确，每个不超过50字
3. 按重要程度从高到低排列
4. 根据答案复杂度提取合理数量的关键要点（通常3-10个）
5. 只提取实质性的知识内容，忽略连接词、过渡语句和套话
6. 如果答案中有举例说明，将例子归纳为其支撑的知识点，不要单独列出例子

## 输出格式
请严格按照以下JSON格式返回，不要包含任何其他内容：
```json
{{
  "keypoints": [
    "关键要点1",
    "关键要点2",
    "关键要点3"
  ],
  "keypoint_count": 3,
  "summary": "对该答案内容的一句话概括",
  "quality_score": 0.85,
  "difficulty_estimate": "medium"
}}
```

字段说明：
- keypoints: 提取的关键要点列表
- keypoint_count: 关键要点数量
- summary: 答案的一句话概括（不超过100字）
- quality_score: 答案的质量评分（0-1之间，评估答案本身的完整性和准确性）
- difficulty_estimate: 题目难度估计（easy / medium / hard）
"""

# 关键点对比 Prompt（AnalyzerAgent 场景B）
# 用于：将学生答案关键点与标准答案关键点进行语义级对比
# 模板变量：question, standard_keypoints, student_keypoints, reference_materials
AGENT_KEYPOINT_COMPARISON_PROMPT = """你是一位专业的教育评估专家，擅长对比分析答案的关键要点。

## 任务
请对比标准答案的关键要点和学生答案的关键要点，找出匹配、缺失和冗余的要点。

## 输入信息
**题目：**
{question}

**标准答案关键要点：**
{standard_keypoints}

**学生答案关键要点：**
{student_keypoints}

**补充参考资料：**
{reference_materials}

## 对比规则
1. **匹配 (matching)**：学生要点与标准要点在语义上表达了相同或等价的知识内容（不要求文字完全一致，意思相近即算匹配）
2. **缺失 (missing)**：标准答案中有但学生答案中完全没有涉及的要点
3. **冗余 (redundant)**：学生答案中有但标准答案中没有的内容。注意区分两种情况：
   - 该内容虽不在标准答案中，但确实正确且与题目相关 → 标记为有效冗余
   - 该内容与题目无关或明显错误 → 标记为无效冗余
4. 每个标准要点最多匹配一个学生要点，每个学生要点最多匹配一个标准要点

## 输出格式
请严格按照以下JSON格式返回，不要包含任何其他内容：
```json
{{
  "matching_keypoints": [
    {{
      "standard": "匹配的标准要点原文",
      "student": "匹配的学生要点原文",
      "match_degree": "high"
    }}
  ],
  "missing_keypoints": [
    "缺失的标准要点1",
    "缺失的标准要点2"
  ],
  "redundant_keypoints": [
    {{
      "content": "冗余的学生要点",
      "is_valid": true,
      "comment": "简要说明（如：该内容正确但超出标准答案范围）"
    }}
  ],
  "coverage_rate": 0.75,
  "overall_assessment": "对学生答案整体覆盖程度和质量的简要评价（一句话）"
}}
```

字段说明：
- matching_keypoints: 匹配的要点对，match_degree 为 high（语义高度一致）或 medium（意思相近但表述有差异）
- missing_keypoints: 学生未涉及的标准要点列表
- redundant_keypoints: 学生额外的要点，is_valid 表示该内容是否正确有价值
- coverage_rate: 学生答案对标准要点的覆盖率（0-1之间，matching数量 / 标准要点总数）
- overall_assessment: 一句话总结学生答案的覆盖情况
"""

# 报告评语生成 Prompt（ReporterAgent）
# 用于：生成写入 grade.overall_comment 的自然语言评语
# 模板变量：question, student_answer, score, max_score, missing_keypoints, matching_keypoints, redundant_keypoints
AGENT_REPORT_COMMENT_PROMPT = """你是一位经验丰富且富有耐心的教师，请为学生的答题情况生成一段个性化的评语。

## 答题信息
**题目：** {question}
**学生答案：** {student_answer}
**得分：** {score} / {max_score}
**答对的要点：** {matching_keypoints}
**缺失的要点：** {missing_keypoints}
**额外的内容：** {redundant_keypoints}

## 评语要求
1. 先肯定学生做得好的部分，具体指出哪些知识点掌握得不错
2. 客观指出不足之处，针对缺失的关键要点给出具体的学习建议
3. 如果学生有正确的额外补充内容，给予肯定
4. 最后给予适当的鼓励
5. 语气专业、友好、有建设性，使用第二人称"你"
6. 评语长度控制在150-300字
7. 不要重复罗列分数等已知信息，重点放在分析和建议上

请直接输出评语文本，不需要JSON格式。
"""

# 报告改进建议生成 Prompt（ReporterAgent）
# 用于：针对缺失和冗余关键点，为学生生成具体可操作的学习改进建议列表
# 模板变量：question, missing_keypoints, redundant_keypoints, reference_hint
AGENT_REPORT_SUGGESTION_PROMPT = """你是一位专业的学科辅导老师，请根据学生的答题情况，给出具体可操作的学习改进建议。

## 答题信息
**题目：** {question}

**缺失的关键要点：**（学生需要重点补充的内容）
{missing_keypoints}

**冗余或错误内容：**（学生需要纠正的部分）
{redundant_keypoints}

**参考资料提示：**
{reference_hint}

## 建议要求
1. 针对每个缺失关键要点，给出 1 条具体的学习建议（如"复习XX概念""注意XX与XX的区别"）
2. 如有无效冗余或错误内容，给出 1 条纠正提示
3. 建议总数控制在 2-4 条，不要泛泛而谈
4. 每条建议简洁明确，不超过40字
5. 语言友好、有针对性，聚焦在知识点本身

## 输出格式
请严格按照以下JSON格式返回，不要包含任何其他内容：
```json
{{
  "suggestions": [
    "建议1",
    "建议2",
    "建议3"
  ]
}}
```

字段说明：
- suggestions: 改进建议列表，每条为一个字符串
"""


# ============================================================
# Python 编程题评分 Prompt（CodeGraderAgent）
# ============================================================

# 模板变量：question, standard_answer, student_code, test_cases, max_score
AGENT_PYTHON_GRADING_PROMPT = """你是一位经验丰富的 Python 编程教学专家，请对学生提交的 Python 代码进行全面评分。

## 题目信息
**题目描述：**
{question}

**标准答案/参考实现：**
{standard_answer}

**测试用例：**
{test_cases}

**学生提交的代码：**
```python
{student_code}
```

## 评分维度（总分 {max_score} 分）

请从以下三个维度进行评分，各维度权重如下：
1. **正确性（correctness）**：代码是否正确实现了题目要求，逻辑是否无误，是否能通过测试用例 —— 占总分 **50%**
2. **逻辑性（logic）**：算法选择是否合理，边界条件处理，异常处理，代码结构是否清晰 —— 占总分 **30%**
3. **规范性（style）**：变量命名、注释、代码可读性、是否符合 Python 编码规范（PEP8） —— 占总分 **20%**

## 评分要求
- 对每个测试用例逐一分析，判断学生代码能否产生正确输出
- 如果学生代码有语法错误，正确性直接给 0 分
- 给出具体的问题定位，不要泛泛而谈
- 对比标准答案，指出学生代码的优缺点

## 输出格式
请严格按照以下 JSON 格式返回，不要包含任何其他内容：
```json
{{
  "correctness": {{
    "score_ratio": 0.8,
    "comment": "代码基本实现了功能，但边界条件处理不足",
    "test_case_results": [
      {{"case": "测试用例描述", "expected": "期望输出", "analysis": "分析结论", "pass": true}}
    ]
  }},
  "logic": {{
    "score_ratio": 0.7,
    "comment": "算法选择合理，但未处理空列表情况"
  }},
  "style": {{
    "score_ratio": 0.9,
    "comment": "命名规范，有适当注释"
  }},
  "score": 7.5,
  "max_score": 10,
  "confidence": 0.85,
  "feedback": "总体评语：代码思路正确，但需要注意边界条件...",
  "suggestions": ["建议1：注意处理空输入情况", "建议2：可以使用列表推导式简化代码"]
}}
```

字段说明：
- correctness.score_ratio: 正确性得分比例（0-1），实际得分 = max_score × 0.5 × score_ratio
- logic.score_ratio: 逻辑性得分比例（0-1），实际得分 = max_score × 0.3 × score_ratio
- style.score_ratio: 规范性得分比例（0-1），实际得分 = max_score × 0.2 × score_ratio
- score: 最终综合得分（已按权重计算好的总分，不超过 max_score）
- confidence: 评分置信度（0-1），代码越完整置信度越高
- feedback: 面向学生的综合评语（150-300字）
- suggestions: 具体改进建议列表（2-4条）
"""


# ============================================================
# SQL 语句评分 Prompt（CodeGraderAgent）
# ============================================================

# 模板变量：question, standard_answer, student_sql, test_cases, max_score
AGENT_SQL_GRADING_PROMPT = """你是一位资深的数据库工程师和 SQL 教学专家，请对学生提交的 SQL 语句进行全面评分。

## 题目信息
**题目描述：**
{question}

**标准答案/参考 SQL：**
```sql
{standard_answer}
```

**测试数据/测试场景：**
{test_cases}

**学生提交的 SQL：**
```sql
{student_sql}
```

## 评分维度（总分 {max_score} 分）

请从以下三个维度进行评分，各维度权重如下：
1. **正确性（correctness）**：SQL 语法是否正确，查询结果是否符合题目要求，能否得到正确数据 —— 占总分 **60%**
2. **逻辑性（logic）**：表关联逻辑、WHERE 条件、GROUP BY/HAVING 使用是否恰当，是否有逻辑漏洞 —— 占总分 **30%**
3. **高效性（efficiency）**：是否有明显的性能问题（如全表扫描、重复子查询、不必要的 DISTINCT 等）—— 占总分 **10%**

## 评分要求
- 逐一分析测试场景，判断学生 SQL 是否产生正确结果
- 如果 SQL 存在语法错误，正确性直接给 0 分
- 对比标准答案，分析两者的差异和等价性（不同写法可能都是正确的）
- 高效性评分重点关注明显的低效模式，轻微的写法差异不扣分

## 输出格式
请严格按照以下 JSON 格式返回，不要包含任何其他内容：
```json
{{
  "correctness": {{
    "score_ratio": 0.9,
    "comment": "SQL 语法正确，能够查询出符合要求的数据",
    "syntax_valid": true,
    "test_case_results": [
      {{"case": "测试场景描述", "analysis": "分析结论", "pass": true}}
    ]
  }},
  "logic": {{
    "score_ratio": 0.8,
    "comment": "JOIN 条件正确，但 WHERE 过滤条件有遗漏"
  }},
  "efficiency": {{
    "score_ratio": 0.7,
    "comment": "使用了子查询，可以改写为 JOIN 提升性能",
    "issues": ["子查询可优化为 JOIN"]
  }},
  "score": 8.5,
  "max_score": 10,
  "confidence": 0.9,
  "feedback": "总体评语：SQL 基本正确，查询逻辑清晰，但效率方面有提升空间...",
  "suggestions": ["建议1：考虑使用 JOIN 替代子查询", "建议2：注意 NULL 值的处理"]
}}
```

字段说明：
- correctness.score_ratio: 正确性得分比例（0-1），实际得分 = max_score × 0.6 × score_ratio
- logic.score_ratio: 逻辑性得分比例（0-1），实际得分 = max_score × 0.3 × score_ratio
- efficiency.score_ratio: 高效性得分比例（0-1），实际得分 = max_score × 0.1 × score_ratio
- score: 最终综合得分（已按权重计算好的总分，不超过 max_score）
- confidence: 评分置信度（0-1）
- feedback: 面向学生的综合评语（100-250字）
- suggestions: 具体改进建议列表（1-3条）
"""


# ============================================================
# 课程报告评分 Prompt（ReportGraderAgent）
# ============================================================

# 模板变量：question, standard_answer, student_report, grading_rubric, max_score
AGENT_REPORT_GRADING_PROMPT = """你是一位大学课程报告评阅专家，请对学生提交的课程报告进行全面、客观的评分。

## 作业要求
**题目/报告主题：**
{question}

**评分要求/参考标准：**
{standard_answer}

**评分细则（如有）：**
{grading_rubric}

**学生提交的报告内容：**
{student_report}

## 评分维度（总分 {max_score} 分）

请从以下四个维度进行评分：
1. **结构完整性（structure）**：报告是否具备完整的结构（引言/背景、正文/方法、结果/分析、结论/总结），格式是否规范 —— 占总分 **20%**
2. **内容质量（content）**：内容是否切题，论述是否充分，关键知识点是否涵盖，论据是否有说服力 —— 占总分 **40%**
3. **语言表达（writing）**：语言是否流畅准确，逻辑是否清晰，专业术语使用是否恰当 —— 占总分 **20%**
4. **创新思考（innovation）**：是否有独立见解，是否结合实际应用，是否提出有价值的思考或建议 —— 占总分 **20%**

## 评分要求
- 请结合作业要求和评分细则进行评分，如评分细则为空则根据通用学术标准评分
- 评分要具体客观，避免主观臆断
- 请明确指出报告的亮点和不足之处
- 对于内容质量维度，请检查关键知识点的覆盖情况

## 输出格式
请严格按照以下 JSON 格式返回，不要包含任何其他内容：
```json
{{
  "structure": {{
    "score_ratio": 0.85,
    "comment": "报告结构完整，包含引言、正文和结论，格式规范",
    "has_introduction": true,
    "has_body": true,
    "has_conclusion": true
  }},
  "content": {{
    "score_ratio": 0.75,
    "comment": "内容基本切题，主要知识点有涉及，但部分论述不够深入",
    "key_points_covered": ["已覆盖的知识点1", "已覆盖的知识点2"],
    "key_points_missing": ["缺少的知识点1"]
  }},
  "writing": {{
    "score_ratio": 0.8,
    "comment": "语言表达清晰，专业术语使用正确，逻辑层次分明"
  }},
  "innovation": {{
    "score_ratio": 0.6,
    "comment": "基本完成了要求，但缺少独立见解和创新性思考"
  }},
  "score": 7.5,
  "max_score": 10,
  "confidence": 0.8,
  "feedback": "总体评语：报告结构完整，内容基本覆盖了主要知识点，语言表达清晰。但在创新性思考方面有待提升...",
  "suggestions": ["建议1：可以结合具体案例深化论述", "建议2：结论部分可以加入自己的思考和展望"]
}}
```

字段说明：
- structure.score_ratio: 结构得分比例（0-1），实际得分 = max_score × 0.2 × score_ratio
- content.score_ratio: 内容得分比例（0-1），实际得分 = max_score × 0.4 × score_ratio
- writing.score_ratio: 语言得分比例（0-1），实际得分 = max_score × 0.2 × score_ratio
- innovation.score_ratio: 创新得分比例（0-1），实际得分 = max_score × 0.2 × score_ratio
- score: 最终综合得分（已按权重计算好的总分，不超过 max_score）
- confidence: 评分置信度（0-1）
- feedback: 面向学生的综合评语（200-400字，语气专业友好）
- suggestions: 具体改进建议列表（2-4条）
"""