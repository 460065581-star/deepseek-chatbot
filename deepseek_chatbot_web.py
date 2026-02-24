import streamlit as st
import requests
import json
import time
import os
from typing import List, Dict
from datetime import datetime

# ==================== 多模型配置（部署版） ====================
# 部署时：从Streamlit Secrets读取
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "")
QWEN_API_KEY = st.secrets.get("QWEN_API_KEY", "")

# 模型配置表
MODEL_CONFIGS = {
    "DeepSeek（正式风）": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model_name": "deepseek-chat",
        "api_key": DEEPSEEK_API_KEY
    },
    "千问（口语风）": {
        "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model_name": "qwen-turbo",
        "api_key": QWEN_API_KEY
    }
}

# ==================== 持久化存储核心函数 ====================
HISTORY_FILE = "chat_history.json"

def load_history() -> Dict:
    """从文件加载聊天历史"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            # 防止文件损坏
            return {"display": [], "core": [], "last_reply": ""}
    return {"display": [], "core": [], "last_reply": ""}

def save_history(display_history: List, core_history: List, last_reply: str):
    """保存聊天历史到文件"""
    data = {
        "display": display_history,
        "core": core_history,
        "last_reply": last_reply
    }
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clear_history():
    """清空聊天历史（删除文件）"""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

# ==================== 多模型核心类 ====================
class MultiModelChatBot:
    def __init__(self, model_name="DeepSeek（正式风）", temperature=0.3, max_tokens=150, retry_times=3, retry_interval=3):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_times = retry_times
        self.retry_interval = retry_interval
        self.chat_history: List[Dict[str, str]] = []
        requests.packages.urllib3.disable_warnings()

    def _get_config(self):
        if self.model_name not in MODEL_CONFIGS:
            raise ValueError(f"不支持的模型：{self.model_name}")
        config = MODEL_CONFIGS[self.model_name]
        if not config["api_key"]:
            raise ValueError(f"{self.model_name} 的API Key未配置！")
        return config

    def _get_headers(self) -> Dict[str, str]:
        config = self._get_config()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }

    def _call_api_with_retry(self, request_data: Dict) -> Dict:
        config = self._get_config()
        for retry_idx in range(1, self.retry_times + 1):
            try:
                response = requests.post(
                    url=config["api_url"],
                    headers=self._get_headers(),
                    json=request_data,
                    verify=False,
                    timeout=20
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if retry_idx == self.retry_times:
                    raise Exception(f"{self.model_name}调用失败：{str(e)}")
                time.sleep(self.retry_interval)

    def send_message(self, user_input: str, reset_history=False, custom_temp=None, custom_max_tokens=None) -> str:
        if reset_history:
            self.chat_history.clear()
        if not user_input.strip():
            raise ValueError("输入不能为空！")
        
        self.chat_history.append({"role": "user", "content": user_input.strip()})
        config = self._get_config()
        request_data = {
            "model": config["model_name"],
            "messages": self.chat_history,
            "temperature": custom_temp if custom_temp is not None else self.temperature,
            "max_tokens": custom_max_tokens if custom_max_tokens is not None else self.max_tokens
        }

        api_result = self._call_api_with_retry(request_data)
        ai_raw_reply = api_result["choices"][0]["message"]["content"]
        clean_reply = ai_raw_reply.strip()
        self.chat_history.append({"role": "assistant", "content": clean_reply})
        return clean_reply

# ==================== 预设文案模板 ====================
PROMPT_TEMPLATES = {
    "早安文案（自然风）": "写3句20字以内的早安文案，带阳光/风/晨露等自然元素，风格温暖治愈",
    "晚安文案（星空风）": "写3句20字以内的晚安文案，带星空/月亮/晚风等元素，风格温柔舒缓",
    "节日文案（通用）": "写3句20字以内的通用节日文案，适配中秋/端午/春节，风格喜庆温馨",
    "励志文案（简洁）": "写3句15字以内的励志文案，风格简洁有力，适合朋友圈",
    "朋友圈文案（生活感）": "写3句25字以内的生活感朋友圈文案，风格轻松自然，贴近日常"
}

# ==================== 工具函数 ====================
def export_to_txt(text: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"文案生成_{timestamp}.txt"
    st.download_button(
        label="📥 导出为TXT文件",
        data=text,
        file_name=file_name,
        mime="text/plain"
    )

# ==================== 主程序入口 ====================
def main():
    st.set_page_config(
        page_title="多模型智能文案助手（带记忆）",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 自定义CSS
    st.markdown("""
        <style>
            body {font-family: "Microsoft YaHei", sans-serif;}
            h1 {color: #2E86AB !important; text-align: center; margin-bottom: 20px;}
            .sidebar-header {color: #A23B72; font-weight: bold; margin: 10px 0 5px 0;}
            .stChatMessage {border-radius: 12px; padding: 10px 15px; margin-bottom: 8px;}
            .stButton>button {border-radius: 8px; background-color: #F18F01; color: white; border: none;}
            .stButton>button:hover {background-color: #C77800;}
            pre {border-radius: 8px !important;}
        </style>
    """, unsafe_allow_html=True)

    st.title("🧠 多模型智能文案助手（持久化版）")
    st.caption("第八课 | 关闭网页，历史记录不丢失")

    # 侧边栏
    with st.sidebar:
        st.markdown('<div class="sidebar-header">🔄 模型选择</div>', unsafe_allow_html=True)
        selected_model = st.selectbox("选择文案生成模型", list(MODEL_CONFIGS.keys()), index=0)

        st.divider()
        st.markdown('<div class="sidebar-header">⚙️ 基础设置</div>', unsafe_allow_html=True)
        temp = st.slider("回复创意度", 0.0, 1.0, 0.3, 0.1)
        max_tokens = st.slider("最大长度", 50, 500, 150, 50)
        
        # 清空按钮（现在会删除文件）
        if st.button("🗑️ 清空历史（永久删除）", type="secondary"):
            clear_history()
            st.session_state.chat_history_display = []
            st.session_state.bot.chat_history = []
            st.session_state.last_reply = ""
            st.success("✅ 已永久清空所有历史记录！")
            st.rerun() # 强制刷新页面

        st.divider()
        st.markdown('<div class="sidebar-header">📋 预设模板</div>', unsafe_allow_html=True)
        selected_template = st.selectbox("选择文案模板", list(PROMPT_TEMPLATES.keys()), index=0)
        use_template_btn = st.button("🚀 使用模板", type="primary")

    # ========== 核心：初始化并加载历史 ==========
    # 1. 首次运行或模型切换时，初始化Bot
    if "bot" not in st.session_state or st.session_state.bot.model_name != selected_model:
        st.session_state.bot = MultiModelChatBot(
            model_name=selected_model,
            temperature=temp,
            max_tokens=max_tokens
        )
    
    # 2. 加载历史记录（仅在页面首次加载时）
    if "chat_history_display" not in st.session_state:
        loaded_data = load_history()
        st.session_state.chat_history_display = loaded_data["display"]
        st.session_state.bot.chat_history = loaded_data["core"]
        st.session_state.last_reply = loaded_data["last_reply"]

    # ========== 模板生成逻辑 ==========
    if use_template_btn:
        template_prompt = PROMPT_TEMPLATES[selected_template]
        st.session_state.chat_history_display.append({"role": "user", "content": template_prompt})
        
        with st.spinner(f"✨ {selected_model}正在生成文案..."):
            try:
                ai_reply = st.session_state.bot.send_message(
                    template_prompt,
                    custom_temp=temp,
                    custom_max_tokens=max_tokens
                )
                st.session_state.chat_history_display.append({"role": "assistant", "content": ai_reply})
                st.session_state.last_reply = ai_reply
                
                # ========== 核心：保存历史 ==========
                save_history(
                    st.session_state.chat_history_display,
                    st.session_state.bot.chat_history,
                    ai_reply
                )

            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")

    # ========== 自定义输入逻辑 ==========
    user_input = st.chat_input(f"💡 输入自定义文案需求（当前模型：{selected_model}）")
    if user_input:
        st.session_state.chat_history_display.append({"role": "user", "content": user_input})
        
        with st.spinner(f"✨ {selected_model}正在思考..."):
            try:
                ai_reply = st.session_state.bot.send_message(
                    user_input,
                    custom_temp=temp,
                    custom_max_tokens=max_tokens
                )
                st.session_state.chat_history_display.append({"role": "assistant", "content": ai_reply})
                st.session_state.last_reply = ai_reply
                
                # ========== 核心：保存历史 ==========
                save_history(
                    st.session_state.chat_history_display,
                    st.session_state.bot.chat_history,
                    ai_reply
                )

            except Exception as e:
                st.error(f"❌ 出错了：{str(e)}")

    # ========== 界面展示 ==========
    col1, col2 = st.columns([8, 2])

    with col1:
        for msg in st.session_state.chat_history_display:
            avatar = "🧑" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    with col2:
        st.markdown('<div class="sidebar-header">🔧 文案工具</div>', unsafe_allow_html=True)
        if st.session_state.last_reply:
            st.code(st.session_state.last_reply, language="text")
            
            st.markdown("""
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const codeBlocks = document.querySelectorAll('pre code');
                        if (codeBlocks.length > 0) {
                            const lastCodeBlock = codeBlocks[codeBlocks.length - 1];
                            const range = document.createRange();
                            range.selectNodeContents(lastCodeBlock);
                            const selection = window.getSelection();
                            selection.removeAllRanges();
                            selection.addRange(range);
                        }
                    });
                </script>
            """, unsafe_allow_html=True)
            
            st.success("✅ 文案已自动选中，按 Ctrl/Cmd+C 复制！")
            export_to_txt(st.session_state.last_reply)
        else:
            st.info("💡 生成文案后可使用复制/导出功能")

if __name__ == "__main__":
    main()