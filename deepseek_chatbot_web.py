import streamlit as st
import requests
import json
import time

# ==================== 模型密钥（部署时从secrets读） ====================
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "")
QWEN_API_KEY = st.secrets.get("QWEN_API_KEY", "")

MODEL_CONFIGS = {
    "DeepSeek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key": DEEPSEEK_API_KEY,
        "model": "deepseek-chat"
    },
    "千问": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key": QWEN_API_KEY,
        "model": "qwen-turbo"
    }
}

# ==================== Agent 大脑核心 ====================
def agent_think(user_input):
    prompt = f"""
你是一个专业文案智能Agent，请按步骤思考：

用户需求：{user_input}

第一步：分析用户要写什么类型文案（早安/晚安/节日/励志/朋友圈/产品）
第二步：判断是否需要使用知识库
第三步：生成高质量、简短、自然的文案

直接输出最终文案，不要多余解释。
"""
    return prompt

# ==================== AI调用 ====================
def ai_response(model_name, user_input, temperature=0.3):
    cfg = MODEL_CONFIGS[model_name]
    
    # 这里就是 Agent 启动！
    final_prompt = agent_think(user_input)

    headers = {
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": temperature
    }
    try:
        res = requests.post(cfg["url"], headers=headers, json=data, timeout=30)
        return res.json()["choices"][0]["message"]["content"].strip()
    except:
        return "❌ Agent 思考出错，请检查API密钥"

# ==================== 界面 ====================
st.title("🧠 第十课：AI Agent 智能文案机器人")
st.subheader("会自己思考的AI员工")

model_choice = st.selectbox("选择模型", ["DeepSeek", "千问"])
user_msg = st.chat_input("输入你想写的文案需求，比如：写3句高级感早安文案")

if "history" not in st.session_state:
    st.session_state.history = []

if user_msg:
    with st.spinner("🤖 Agent 正在思考中..."):
        reply = ai_response(model_choice, user_msg)
        st.session_state.history.append({"user": user_msg, "ai": reply})

for chat in st.session_state.history:
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["ai"])