import streamlit as st
import requests
import json
import time
from typing import List, Dict
from datetime import datetime

# ==================== 核心配置（本地/部署双兼容） ====================
# 本地测试：直接填写你的API Key
# 本地测试时取消注释，部署时注释掉
# 部署时启用这行，从 Streamlit Secrets 读取
API_KEY = st.secrets["API_KEY"]
# 部署时：注释上面一行，启用下面一行
# API_KEY = st.secrets["API_KEY"]

API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

# ==================== DeepSeek机器人核心类 ====================
class DeepSeekChatBot:
    def __init__(self, temperature=0.3, max_tokens=150, retry_times=3, retry_interval=3):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_times = retry_times
        self.retry_interval = retry_interval
        self.chat_history: List[Dict[str, str]] = []
        requests.packages.urllib3.disable_warnings()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

    def _call_api_with_retry(self, request_data: Dict) -> Dict:
        for retry_idx in range(1, self.retry_times + 1):
            try:
                response = requests.post(
                    url=API_URL,
                    headers=self._get_headers(),
                    json=request_data,
                    verify=False,
                    timeout=20
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if retry_idx == self.retry_times:
                    raise Exception(f"调用失败（重试{self.retry_times}次）：{str(e)}")
                time.sleep(self.retry_interval)

    def send_message(self, user_input: str, reset_history=False, custom_temp=None, custom_max_tokens=None) -> str:
        if reset_history:
            self.chat_history.clear()
        if not user_input.strip():
            raise ValueError("输入不能为空！")
        
        self.chat_history.append({"role": "user", "content": user_input.strip()})
        request_data = {
            "model": DEFAULT_MODEL,
            "messages": self.chat_history,
            "temperature": custom_temp if custom_temp is not None else self.temperature,
            "max_tokens": custom_max_tokens if custom_max_tokens is not None else self.max_tokens
        }

        api_result = self._call_api_with_retry(request_data)
        ai_raw_reply = api_result["choices"][0]["message"]["content"]
        clean_reply = self._format_reply(ai_raw_reply)
        self.chat_history.append({"role": "assistant", "content": clean_reply})
        return clean_reply

    @staticmethod
    def _format_reply(raw_reply: str) -> str:
        if not raw_reply:
            return "AI暂无有效回复"
        return raw_reply.strip()

# ==================== 预设文案模板 ====================
PROMPT_TEMPLATES = {
    "早安文案（自然风）": "写3句20字以内的早安文案，带阳光/风/晨露等自然元素，风格温暖治愈",
    "晚安文案（星空风）": "写3句20字以内的晚安文案，带星空/月亮/晚风等元素，风格温柔舒缓",
    "节日文案（通用）": "写3句20字以内的通用节日文案，适配中秋/端午/春节，风格喜庆温馨",
    "励志文案（简洁）": "写3句15字以内的励志文案，风格简洁有力，适合朋友圈",
    "朋友圈文案（生活感）": "写3句25字以内的生活感朋友圈文案，风格轻松自然，贴近日常"
}

# ==================== 工具函数（导出） ====================
def export_to_txt(text: str):
    """导出文案为TXT文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"文案生成_{timestamp}.txt"
    st.download_button(
        label="📥 导出为TXT文件",
        data=text,
        file_name=file_name,
        mime="text/plain"
    )

# ==================== Streamlit网页界面（方案2最终版） ====================
def main():
    st.set_page_config(
        page_title="DeepSeek智能文案助手",
        page_icon="✍️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 自定义CSS美化
    st.markdown("""
        <style>
            /* 整体样式 */
            body {font-family: "Microsoft YaHei", sans-serif;}
            h1 {color: #2E86AB !important; text-align: center; margin-bottom: 20px;}
            /* 侧边栏标题 */
            .sidebar-header {color: #A23B72; font-weight: bold; margin: 10px 0 5px 0;}
            /* 聊天气泡 */
            .stChatMessage {border-radius: 12px; padding: 10px 15px; margin-bottom: 8px;}
            /* 按钮样式 */
            .stButton>button {border-radius: 8px; background-color: #F18F01; color: white; border: none;}
            .stButton>button:hover {background-color: #C77800;}
            /* 代码块样式 */
            pre {border-radius: 8px !important;}
        </style>
    """, unsafe_allow_html=True)

    # 页面标题
    st.title("✍️ DeepSeek 智能文案助手")
    st.caption("第六课稳定版 | 自动选中+快捷键复制")

    # 侧边栏功能区
    with st.sidebar:
        st.markdown('<div class="sidebar-header">⚙️ 基础设置</div>', unsafe_allow_html=True)
        temp = st.slider("回复创意度", 0.0, 1.0, 0.3, 0.1, help="0=稳定 | 1=创意")
        max_tokens = st.slider("最大长度", 50, 500, 150, 50, help="控制文案字数")
        reset_btn = st.button("🗑️ 清空历史", type="secondary")

        st.divider()  # 分割线
        st.markdown('<div class="sidebar-header">📋 预设模板</div>', unsafe_allow_html=True)
        selected_template = st.selectbox("选择文案模板", list(PROMPT_TEMPLATES.keys()), index=0)
        use_template_btn = st.button("🚀 使用模板", type="primary")

    # 会话状态初始化
    if "bot" not in st.session_state:
        st.session_state.bot = DeepSeekChatBot(temperature=temp, max_tokens=max_tokens)
    if "chat_history_display" not in st.session_state:
        st.session_state.chat_history_display = []
    if "last_reply" not in st.session_state:
        st.session_state.last_reply = ""

    # 清空历史逻辑
    if reset_btn:
        st.session_state.bot.chat_history.clear()
        st.session_state.chat_history_display = []
        st.session_state.last_reply = ""
        st.success("✅ 已清空所有对话历史！")

    # 使用预设模板逻辑
    if use_template_btn:
        template_prompt = PROMPT_TEMPLATES[selected_template]
        st.session_state.chat_history_display.append({"role": "user", "content": template_prompt})
        with st.spinner("✨ AI正在生成文案..."):
            try:
                ai_reply = st.session_state.bot.send_message(
                    template_prompt,
                    custom_temp=temp,
                    custom_max_tokens=max_tokens
                )
                st.session_state.chat_history_display.append({"role": "assistant", "content": ai_reply})
                st.session_state.last_reply = ai_reply
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")

    # 自定义输入逻辑
    user_input = st.chat_input("💡 输入自定义文案需求（或使用左侧预设模板）")
    if user_input:
        st.session_state.chat_history_display.append({"role": "user", "content": user_input})
        with st.spinner("✨ AI正在思考..."):
            try:
                ai_reply = st.session_state.bot.send_message(
                    user_input,
                    custom_temp=temp,
                    custom_max_tokens=max_tokens
                )
                st.session_state.chat_history_display.append({"role": "assistant", "content": ai_reply})
                st.session_state.last_reply = ai_reply
            except Exception as e:
                st.error(f"❌ 出错了：{str(e)}")

    # 主体布局：聊天区 + 工具区
    col1, col2 = st.columns([8, 2])

    # 聊天记录展示区
    with col1:
        for msg in st.session_state.chat_history_display:
            avatar = "🧑" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # 工具区：方案2（自动选中+快捷键复制）
    with col2:
        st.markdown('<div class="sidebar-header">🔧 文案工具</div>', unsafe_allow_html=True)
        if st.session_state.last_reply:
            # 显示文案代码块（自动选中）
            st.code(st.session_state.last_reply, language="text")
            
            # 自动选中文案的JS脚本
            st.markdown("""
                <script>
                    // 页面加载完成后自动选中最后一个代码块内容
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
            
            # 友好提示
            st.success("✅ 文案已自动选中，按 Ctrl+C（Win）/ Cmd+C（Mac）即可复制！")
            
            # 导出TXT按钮
            export_to_txt(st.session_state.last_reply)
        else:
            st.info("💡 生成文案后可使用复制/导出功能")

if __name__ == "__main__":
    main()