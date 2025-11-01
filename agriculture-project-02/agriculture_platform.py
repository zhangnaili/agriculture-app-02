import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import hashlib
import json
import random
import os
import io
from typing import Dict, List, Tuple
import pulp
from scipy.optimize import linprog
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="方寸云耕 - 智慧农业决策平台",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 用户数据文件路径
USERS_FILE = "users.json"
CHAT_DB = "chat_history.json"

# 初始化用户系统

def init_chat_db():
    """初始化聊天记录文件"""
    if not os.path.exists(CHAT_DB):
        with open(CHAT_DB, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False)
def load_users():
    """加载用户数据"""
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_users(users):
    """保存用户数据"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)


def hash_password(password):
    """密码哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, user_type="普通用户", farm_info=None):
    """注册新用户"""
    users = load_users()

    if username in users:
        return False, "用户名已存在"

    users[username] = {
        'password': hash_password(password),
        'user_type': user_type,
        'farm_info': farm_info or {},
        'created_at': datetime.now().isoformat(),
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        }
    }

    save_users(users)
    return True, "注册成功"


def verify_user(username, password):
    """验证用户登录"""
    users = load_users()

    if username in users and users[username]['password'] == hash_password(password):
        user_data = users[username]
        if 'user_data' not in user_data:
            user_data['user_data'] = {
                'planting_data': None,
                'benefit_data': None
            }
            save_users(users)
        return True, user_data
    return False, None


# ------------------------------
# 聊天功能核心工具
# ------------------------------


# ------------------------------
# 优化的聊天功能核心工具
# ------------------------------


def load_chat_history(chat_id: str) -> list:
    """加载聊天记录 - 支持公共频道和私聊"""
    init_chat_db()
    try:
        with open(CHAT_DB, "r", encoding="utf-8") as f:
            all_chats = json.load(f)
    except:
        all_chats = {}

    return all_chats.get(chat_id, [])


def save_message(chat_id: str, sender: str, content: str, message_type: str = "text") -> None:
    """保存消息到聊天记录"""
    init_chat_db()
    try:
        with open(CHAT_DB, "r", encoding="utf-8") as f:
            all_chats = json.load(f)
    except:
        all_chats = {}

    message = {
        "sender": sender,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "content": content,
        "type": message_type,
        "read": False  # 新增：消息是否已读
    }

    if chat_id not in all_chats:
        all_chats[chat_id] = []

    all_chats[chat_id].append(message)

    # 限制聊天记录长度，避免文件过大
    if len(all_chats[chat_id]) > 1000:
        all_chats[chat_id] = all_chats[chat_id][-500:]

    with open(CHAT_DB, "w", encoding="utf-8") as f:
        json.dump(all_chats, f, ensure_ascii=False, indent=2)


def mark_messages_as_read(chat_id: str, reader: str):
    """标记消息为已读"""
    init_chat_db()
    try:
        with open(CHAT_DB, "r", encoding="utf-8") as f:
            all_chats = json.load(f)
    except:
        return

    if chat_id in all_chats:
        for message in all_chats[chat_id]:
            if message["sender"] != reader:
                message["read"] = True

        with open(CHAT_DB, "w", encoding="utf-8") as f:
            json.dump(all_chats, f, ensure_ascii=False, indent=2)


def get_unread_count(chat_id: str, username: str) -> int:
    """获取未读消息数量"""
    chat_history = load_chat_history(chat_id)
    unread_count = 0
    for msg in chat_history:
        if msg["sender"] != username and not msg.get("read", False):
            unread_count += 1
    return unread_count


def get_recent_chats(username: str) -> List[Dict]:
    """获取用户最近参与的聊天"""
    init_chat_db()
    try:
        with open(CHAT_DB, "r", encoding="utf-8") as f:
            all_chats = json.load(f)
    except:
        return []

    recent_chats = []
    for chat_id in all_chats.keys():
        if username in chat_id.split("|") or chat_id == "PUBLIC_CHANNEL":
            # 获取最后一条消息
            messages = all_chats[chat_id]
            if messages:
                last_msg = messages[-1]
                # 确定聊天名称
                if chat_id == "PUBLIC_CHANNEL":
                    chat_name = "公共频道"
                    chat_type = "public"
                else:
                    other_user = [u for u in chat_id.split("|") if u != username][0]
                    chat_name = f"与 {other_user} 的私聊"
                    chat_type = "private"

                unread_count = get_unread_count(chat_id, username)

                recent_chats.append({
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "last_message": last_msg["content"],
                    "last_time": last_msg["time"],
                    "unread_count": unread_count,
                    "type": chat_type
                })

    # 按最后消息时间排序
    recent_chats.sort(key=lambda x: x["last_time"], reverse=True)
    return recent_chats[:10]  # 返回最近10个聊天


def chat_page():
    """优化的聊天咨询页面"""
    st.header("💬 农业交流中心")
    current_user = st.session_state.username
    user_type = st.session_state.user_data['user_type']

    # 聊天模式选择
    col_mode, col_info = st.columns([2, 1])
    with col_mode:
        chat_mode = st.radio(
            "选择聊天模式",
            ["公共频道", "私聊"],
            horizontal=True,
            help="公共频道：所有用户可见 | 私聊：一对一交流"
        )

    with col_info:
        if chat_mode == "公共频道":
            st.info("🌐 所有用户可见")
        else:
            st.info("🔒 一对一私密聊天")

    # 根据模式显示不同内容
    if chat_mode == "公共频道":
        public_chat_page(current_user, user_type)
    else:
        private_chat_page(current_user, user_type)


def public_chat_page(current_user: str, user_type: str):
    """公共频道页面"""
    st.subheader("📢 公共频道")

    # 公共频道ID
    public_chat_id = "PUBLIC_CHANNEL"

    # 主聊天区域布局
    col_chat, col_side = st.columns([3, 1])

    with col_chat:
        # 聊天消息容器
        chat_container = st.container(height=500, border=True)

        with chat_container:
            # 加载聊天记录
            chat_history = load_chat_history(public_chat_id)

            if not chat_history:
                st.info("💬 欢迎来到公共频道！这里是所有用户交流种植经验、咨询问题的平台。")

            # 显示消息 - 使用Streamlit原生方式
            for msg in chat_history:
                is_own_message = msg['sender'] == current_user

                if is_own_message:
                    # 自己发送的消息 - 右侧显示
                    with st.chat_message("user", avatar="👤"):
                        st.write(f"**{msg['sender']}**")
                        st.caption(f"{msg['time']}")
                        st.write(msg['content'])
                else:
                    # 他人发送的消息 - 左侧显示
                    with st.chat_message("assistant", avatar="👥"):
                        st.write(f"**{msg['sender']}**")
                        st.caption(f"{msg['time']}")
                        st.write(msg['content'])

        # 消息输入区域
        with st.form(key="public_chat_form", clear_on_submit=True):
            col_input, col_btn = st.columns([4, 1])

            with col_input:
                msg_content = st.text_area(
                    "输入消息...",
                    height=80,
                    placeholder="分享种植经验、咨询问题或交流市场行情...",
                    label_visibility="collapsed"
                )

            with col_btn:
                send_btn = st.form_submit_button(
                    "发送",
                    type="primary",
                    use_container_width=True
                )

        # 快捷操作 - 移到表单外部
        st.caption("快捷操作：")
        quick_actions = st.columns(4)
        quick_questions = [
            "有没有种植玉米的高手？",
            "今年小麦价格怎么样？",
            "大棚湿度控制技巧？",
            "推荐山区经济作物"
        ]

        for i, action in enumerate(quick_actions):
            with action:
                if st.button(quick_questions[i], use_container_width=True):
                    save_message(public_chat_id, current_user, quick_questions[i])
                    st.rerun()

        # 发送消息逻辑
        if send_btn and msg_content.strip():
            save_message(public_chat_id, current_user, msg_content.strip())
            st.success("消息发送成功！")
            st.rerun()

    with col_side:
        st.subheader("📊 频道统计")

        # 在线用户统计
        users = load_users()
        registered_users = [uname for uname in users.keys() if uname != current_user]
        online_users_count = len([u for u in registered_users if random.random() > 0.3]) + 1

        st.metric("在线用户", f"{online_users_count}人")
        st.metric("今日消息",
                  f"{len([m for m in chat_history if m['time'].startswith(datetime.now().strftime('%Y-%m-%d'))])}条")
        st.metric("总消息数", f"{len(chat_history)}条")

        st.divider()

        st.subheader("💡 频道指南")
        st.info("""
        **✅ 可以讨论：**
        - 种植经验和技术
        - 农业问题咨询
        - 市场行情交流
        - 病虫害防治

        **❌ 请勿发布：**
        - 广告和推销内容
        - 不实信息
        - 无关话题
        """)

        # 刷新按钮
        if st.button("🔄 刷新消息", use_container_width=True):
            st.rerun()


def private_chat_page(current_user: str, user_type: str):
    """私聊页面"""
    st.subheader("🔒 私聊")

    # 获取用户列表（排除自己）
    users = load_users()
    other_users = [username for username in users.keys() if username != current_user]

    col_users, col_chat = st.columns([1, 2])

    with col_users:
        st.subheader("👥 用户列表")

        # 最近聊天
        recent_chats = get_recent_chats(current_user)  # 这行需要放在前面
        if recent_chats:
            st.write("**最近聊天**")
            for chat in recent_chats:
                badge = f" 🔔 {chat['unread_count']}" if chat['unread_count'] > 0 else ""
                if st.button(
                        f"{chat['chat_name']}{badge}",
                        key=f"recent_{chat['chat_id']}",
                        use_container_width=True
                ):
                    st.session_state.selected_chat = chat['chat_id']
                    mark_messages_as_read(chat['chat_id'], current_user)
                    st.rerun()

        st.divider()

        # 所有用户列表
        st.write("**所有用户**")
        for username in other_users:
            user_type_icon = "👨‍🌾" if users[username]['user_type'] == "农场主" else "👨‍💼" if users[username][
                                                                                                 'user_type'] == "管理员" else "👤"
            if st.button(
                    f"{user_type_icon} {username}",
                    key=f"user_{username}",
                    use_container_width=True
            ):
                # 生成私聊ID
                chat_id = "|".join(sorted([current_user, username]))
                st.session_state.selected_chat = chat_id
                st.rerun()

    with col_chat:
        # 初始化选中的聊天 - 现在 recent_chats 已经定义
        if 'selected_chat' not in st.session_state and recent_chats:
            st.session_state.selected_chat = recent_chats[0]['chat_id']
        elif 'selected_chat' not in st.session_state:
            st.info("请从左侧选择用户开始私聊")
            return

        # 显示选中的聊天
        selected_chat_id = st.session_state.selected_chat
        other_user = [u for u in selected_chat_id.split("|") if u != current_user][0]

        st.write(f"**与 {other_user} 的私聊**")

        # 聊天消息容器
        chat_container = st.container(height=400, border=True)

        with chat_container:
            chat_history = load_chat_history(selected_chat_id)

            if not chat_history:
                st.info(f"💬 开始与 {other_user} 的对话")

            # 显示消息 - 使用Streamlit原生方式
            for msg in chat_history:
                is_own_message = msg['sender'] == current_user

                if is_own_message:
                    # 自己发送的消息 - 右侧显示
                    with st.chat_message("user", avatar="👤"):
                        st.write(f"**{msg['sender']}**")
                        st.caption(f"{msg['time']}")
                        st.write(msg['content'])
                else:
                    # 他人发送的消息 - 左侧显示
                    with st.chat_message("assistant", avatar="👥"):
                        st.write(f"**{msg['sender']}**")
                        st.caption(f"{msg['time']}")
                        st.write(msg['content'])

        # 消息输入区域
        with st.form(key="private_chat_form", clear_on_submit=True):
            msg_content = st.text_area(
                "输入私聊消息...",
                height=100,
                placeholder=f"发送给 {other_user} 的消息...",
                label_visibility="collapsed"
            )

            send_btn = st.form_submit_button(
                "发送消息",
                type="primary",
                use_container_width=True
            )

        # 发送消息逻辑
        if send_btn and msg_content.strip():
            save_message(selected_chat_id, current_user, msg_content.strip())
            st.success("私聊消息发送成功！")
            st.rerun()

        # 操作按钮
        col_ops1, col_ops2 = st.columns(2)
        with col_ops1:
            if st.button("🔄 刷新聊天", use_container_width=True):
                mark_messages_as_read(selected_chat_id, current_user)
                st.rerun()

        with col_ops2:
            if st.button("📋 清除记录", use_container_width=True):
                # 这里可以实现清除聊天记录的功能
                st.warning("清除聊天记录功能待实现")
# 在main函数中替换原有的chat_page调用
# 将原来的 chat_page() 调用替换为新的优化版本
def update_user_preferences(username, preferences):
    """更新用户偏好设置"""
    users = load_users()
    if username in users:
        users[username]['preferences'] = preferences
        save_users(users)
        return True
    return False


def get_user_preferences(username):
    """获取用户偏好设置"""
    users = load_users()
    if username in users:
        return users[username]['preferences']
    return None


def save_user_data(username, data_type, data):
    """保存用户数据"""
    users = load_users()
    if username in users:
        if 'user_data' not in users[username]:
            users[username]['user_data'] = {
                'planting_data': None,
                'benefit_data': None
            }
        users[username]['user_data'][data_type] = data
        save_users(users)
        return True
    return False

# 预定义的初始账号（包含5个管理员账号）
PREDEFINED_ACCOUNTS = {
    "lsf": {
        'password': hash_password("123456"),
        'user_type': "管理员",
        'farm_info': {},
        'created_at': '2024-01-01T00:00:00',
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        },
        'is_predefined': True,
        'redeemed': True  # 已兑换，可直接使用
    },
    "ch": {
        'password': hash_password("123456"),
        'user_type': "管理员",
        'farm_info': {},
        'created_at': '2024-01-01T00:00:00',
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        },
        'is_predefined': True,
        'redeemed': True
    },
    "zxy": {
        'password': hash_password("123456"),
        'user_type': "管理员",
        'farm_info': {},
        'created_at': '2024-01-01T00:00:00',
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        },
        'is_predefined': True,
        'redeemed': True
    },
    "zhangnaili": {
        'password': hash_password("123456"),
        'user_type': "管理员",
        'farm_info': {},
        'created_at': '2024-01-01T00:00:00',
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        },
        'is_predefined': True,
        'redeemed': True
    },
    "zzq": {
        'password': hash_password("123456"),
        'user_type': "管理员",
        'farm_info': {},
        'created_at': '2024-01-01T00:00:00',
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        },
        'is_predefined': True,
        'redeemed': True
    },
    # 原有的演示账号
    "guest": {
        'password': hash_password("guest123"),
        'user_type': "普通用户",
        'farm_info': {},
        'created_at': '2024-01-01T00:00:00',
        'preferences': {
            'risk_level': '稳健',
            'economic_weight': 0.6,
            'stability_weight': 0.3,
            'sustainability_weight': 0.1
        },
        'user_data': {
            'planting_data': None,
            'benefit_data': None
        },
        'is_predefined': True,
        'redeemed': True
    }
}

# 兑换码系统（现在只包含演示账号的兑换码）
REDEMPTION_CODES = {
    "DEMO001": "guest"
}
def get_user_data(username, data_type):
    """获取用户数据"""
    users = load_users()
    if username in users:
        if 'user_data' not in users[username]:
            users[username]['user_data'] = {
                'planting_data': None,
                'benefit_data': None
            }
            save_users(users)
            return None
        return users[username]['user_data'].get(data_type)
    return None


# 核心算法实现
class AgriculturalOptimizer:
    """农业种植优化算法类"""

    def __init__(self, planting_data, benefit_data, preferences):
        self.planting_data = planting_data
        self.benefit_data = benefit_data
        self.preferences = preferences
        self.risk_levels = {
            "极度保守": 0.1,
            "保守": 0.3,
            "稳健": 0.5,
            "积极": 0.7,
            "极度积极": 0.9
        }

    def calculate_crop_suitability(self) -> Dict[str, float]:
        """计算作物适应性评分"""
        suitability_scores = {}

        for _, crop in self.benefit_data.iterrows():
            score = 0.0

            # 经济效益评分 (40%)
            economic_score = crop['亩效益/元'] / self.benefit_data['亩效益/元'].max()
            score += economic_score * 0.4

            # 稳定性评分 (30%)
            cost_stability = 1 - (crop['种植成本/(元/亩)'] / self.benefit_data['种植成本/(元/亩)'].max())
            yield_stability = crop['亩产量/斤'] / self.benefit_data['亩产量/斤'].max()
            stability_score = (cost_stability + yield_stability) / 2
            score += stability_score * 0.3

            # 可持续性评分 (30%)
            # 豆类作物有轮作优势
            if '豆' in crop['作物名称']:
                sustainability_bonus = 0.3
            else:
                sustainability_bonus = 0.1

            # 低成本作物更可持续
            cost_sustainability = 1 - (crop['种植成本/(元/亩)'] / self.benefit_data['种植成本/(元/亩)'].max())
            sustainability_score = (sustainability_bonus + cost_sustainability) / 2
            score += sustainability_score * 0.3

            suitability_scores[crop['作物名称']] = score

        return suitability_scores

    def optimize_planting_plan(self, total_area: float, years: int = 3) -> Dict:
        """优化种植规划 - 使用线性规划"""
        try:
            # 准备数据
            crops = self.benefit_data['作物名称'].tolist()
            current_planting = self.planting_data.groupby('作物名称')['种植面积/亩'].sum().to_dict()

            # 创建问题实例
            prob = pulp.LpProblem("Agricultural_Optimization", pulp.LpMaximize)

            # 决策变量：各种作物的种植面积
            crop_areas = pulp.LpVariable.dicts("CropArea", crops, lowBound=0)

            # 目标函数：最大化综合效益
            suitability_scores = self.calculate_crop_suitability()
            risk_factor = self.risk_levels.get(self.preferences['risk_level'], 0.5)

            # 计算加权目标函数
            objective = 0
            for crop in crops:
                crop_data = self.benefit_data[self.benefit_data['作物名称'] == crop].iloc[0]

                # 经济效益部分
                economic_value = crop_data['亩效益/元'] * self.preferences['economic_weight']

                # 稳定性部分（考虑风险偏好）
                stability_value = (1 - crop_data['种植成本/(元/亩)'] / 2000) * self.preferences['stability_weight']

                # 可持续性部分
                sustainability_value = suitability_scores[crop] * self.preferences['sustainability_weight']

                # 综合价值
                crop_value = (economic_value + stability_value + sustainability_value) * risk_factor

                objective += crop_value * crop_areas[crop]

            prob += objective

            # 约束条件
            # 总面积约束
            prob += pulp.lpSum([crop_areas[crop] for crop in crops]) <= total_area

            # 轮作约束：豆类作物最小面积（改善土壤）
            bean_crops = [crop for crop in crops if '豆' in crop]
            if bean_crops:
                min_bean_area = total_area * 0.15  # 至少15%的面积种植豆类
                prob += pulp.lpSum([crop_areas[crop] for crop in bean_crops]) >= min_bean_area

            # 多样性约束：单一作物不超过总面积的30%
            for crop in crops:
                prob += crop_areas[crop] <= total_area * 0.3

            # 连续性约束：当前种植的作物面积变化不超过50%
            for crop, current_area in current_planting.items():
                if crop in crop_areas:
                    prob += crop_areas[crop] >= current_area * 0.5
                    prob += crop_areas[crop] <= current_area * 1.5

            # 求解
            prob.solve(pulp.PULP_CBC_CMD(msg=0))

            if pulp.LpStatus[prob.status] == 'Optimal':
                result = {
                    'status': 'optimal',
                    'total_area': total_area,
                    'allocated_area': 0,
                    'crop_allocations': {},
                    'expected_improvement': 0
                }

                current_total_benefit = 0
                new_total_benefit = 0

                for crop in crops:
                    area = crop_areas[crop].varValue
                    if area > 0:
                        crop_data = self.benefit_data[self.benefit_data['作物名称'] == crop].iloc[0]
                        result['crop_allocations'][crop] = {
                            'area': area,
                            'expected_benefit': crop_data['亩效益/元'] * area,
                            'percentage': (area / total_area) * 100
                        }
                        result['allocated_area'] += area
                        new_total_benefit += crop_data['亩效益/元'] * area

                        # 计算当前效益
                        current_area = current_planting.get(crop, 0)
                        current_total_benefit += crop_data['亩效益/元'] * current_area

                if current_total_benefit > 0:
                    result['expected_improvement'] = ((
                                                                  new_total_benefit - current_total_benefit) / current_total_benefit) * 100

                return result
            else:
                return {'status': 'infeasible', 'message': '无法找到可行解'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def risk_analysis(self, crop_allocations: Dict) -> Dict:
        """风险分析"""
        risk_scores = {}
        total_investment = 0
        total_expected_return = 0

        for crop, allocation in crop_allocations.items():
            crop_data = self.benefit_data[self.benefit_data['作物名称'] == crop].iloc[0]

            investment = crop_data['种植成本/(元/亩)'] * allocation['area']
            expected_return = crop_data['亩效益/元'] * allocation['area']

            total_investment += investment
            total_expected_return += expected_return

            # 风险评分基于成本波动性和产量稳定性
            cost_risk = crop_data['种植成本/(元/亩)'] / 1000  # 标准化
            yield_risk = 1 - (crop_data['亩产量/斤'] / self.benefit_data['亩产量/斤'].max())

            risk_score = (cost_risk + yield_risk) / 2
            risk_scores[crop] = {
                'risk_score': risk_score,
                'investment': investment,
                'expected_return': expected_return
            }

        # 总体风险评估
        overall_risk = np.mean([v['risk_score'] for v in risk_scores.values()])
        roi = (total_expected_return / total_investment) * 100 if total_investment > 0 else 0

        return {
            'overall_risk': overall_risk,
            'total_investment': total_investment,
            'total_expected_return': total_expected_return,
            'roi': roi,
            'crop_risks': risk_scores
        }


class PricePredictor:
    """价格预测算法类"""

    def __init__(self, historical_data=None):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def create_synthetic_data(self, benefit_data):
        """创建合成历史数据用于演示"""
        dates = pd.date_range(start='2020-01-01', end='2024-01-01', freq='M')
        synthetic_data = []

        for crop in benefit_data['作物名称'].unique():
            crop_data = benefit_data[benefit_data['作物名称'] == crop].iloc[0]
            base_price = crop_data['销售单价/(元/斤)']

            for date in dates:
                # 添加季节性和随机波动
                seasonal_factor = 1 + 0.2 * np.sin(2 * np.pi * date.month / 12)
                random_factor = 1 + np.random.normal(0, 0.1)
                price = base_price * seasonal_factor * random_factor

                synthetic_data.append({
                    'date': date,
                    'crop': crop,
                    'price': max(price, base_price * 0.5),  # 确保价格不会太低
                    'month': date.month,
                    'year': date.year
                })

        return pd.DataFrame(synthetic_data)

    def train(self, benefit_data):
        """训练预测模型"""
        try:
            historical_data = self.create_synthetic_data(benefit_data)

            # 特征工程
            features = historical_data[['month', 'year']]
            target = historical_data['price']

            # 训练模型
            features_scaled = self.scaler.fit_transform(features)
            self.model.fit(features_scaled, target)
            self.is_trained = True

            return True
        except Exception as e:
            print(f"训练错误: {e}")
            return False

    def predict(self, crop, months=12):
        """预测未来价格"""
        if not self.is_trained:
            return None

        future_dates = pd.date_range(start=datetime.now(), periods=months, freq='M')
        predictions = []

        for date in future_dates:
            features = np.array([[date.month, date.year]])
            features_scaled = self.scaler.transform(features)
            predicted_price = self.model.predict(features_scaled)[0]
            predictions.append({
                'date': date,
                'predicted_price': max(predicted_price, 0.1)  # 确保价格为正
            })

        return pd.DataFrame(predictions)


def redeem_account(redemption_code):
    """兑换账号"""
    if redemption_code in REDEMPTION_CODES:
        username = REDEMPTION_CODES[redemption_code]
        users = load_users()

        if username in users and users[username].get('is_predefined', False):
            if not users[username].get('redeemed', False):
                # 标记为已兑换
                users[username]['redeemed'] = True
                save_users(users)
                return True, username, f"兑换成功！您的账号是：{username}，初始密码请查看使用说明。"
            else:
                return False, None, "该兑换码已被使用"
        else:
            return False, None, "无效的兑换码"
    else:
        return False, None, "兑换码无效"


def init_users():
    """初始化用户数据 - 包含预定义账号"""
    users = load_users()

    # 如果users文件为空或不存在，将预定义账号添加进去
    if not users:
        users = PREDEFINED_ACCOUNTS.copy()
        save_users(users)
    else:
        # 确保所有预定义账号都在users中
        for username, account_info in PREDEFINED_ACCOUNTS.items():
            if username not in users:
                users[username] = account_info
            else:
                # 保留预定义账号的属性，但更新其他可能修改的字段
                users[username]['is_predefined'] = True
                if 'redeemed' not in users[username]:
                    users[username]['redeemed'] = account_info['redeemed']

        save_users(users)

    return users



def login_page():
    """登录页面"""
    st.title("🌾 方寸云耕 - 用户登录")

    # 显示可直接使用的账号信息
    with st.expander("👥 可直接使用的账号", expanded=True):
        st.success("""
        **管理员账号（直接登录）：**
        - 用户名: `lsf` | 密码: `******`
        - 用户名: `ch` | 密码: `******`  
        - 用户名: `zxy` | 密码: `******`
        - 用户名: `zhangnaili` | 密码: `******`
        - 用户名: `zzq` | 密码: `******`

        **演示账号：**
        - 用户名: `guest` | 密码: `******`
        """)

    # 原有的兑换码区域（现在只对演示账号需要）
    with st.expander("🎁 兑换演示账号", expanded=False):
        redemption_code = st.text_input("兑换码", placeholder="输入 DEMO001 获取演示账号")
        if st.button("兑换账号", use_container_width=True):
            if redemption_code:
                success, username, message = redeem_account(redemption_code.upper())
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
            else:
                st.warning("请输入兑换码")

    st.markdown("---")

    # 登录表单
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        login_button = st.form_submit_button("登录", use_container_width=True)

        if login_button:
            if username and password:
                # 修复这里：verify_user只返回2个值，不是3个
                success, user_data = verify_user(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_data = user_data
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
            else:
                st.error("请输入用户名和密码")

    # 临时账号创建（可选）
    with st.expander("创建临时账号（可选）", expanded=False):
        st.warning("⚠️ 临时账号仅在当前浏览器会话中有效")

        with st.form("temp_account_form"):
            temp_username = st.text_input("临时用户名")
            temp_password = st.text_input("临时密码", type="password")
            temp_user_type = st.selectbox("用户类型", ["普通用户", "农场主"])

            farm_info = {}
            if temp_user_type == "农场主":
                farm_info['farm_name'] = st.text_input("农场名称")
                farm_info['total_area'] = st.number_input("总面积（亩）", min_value=0.0)

            create_temp_button = st.form_submit_button("创建临时账号", use_container_width=True)

            if create_temp_button:
                if not temp_username or not temp_password:
                    st.error("请输入用户名和密码")
                else:
                    success, message = register_user(temp_username, temp_password, temp_user_type, farm_info)
                    if success:
                        st.success(message)
                        # 自动登录
                        st.session_state.logged_in = True
                        st.session_state.username = temp_username
                        st.session_state.user_data = load_users()[temp_username]
                        st.rerun()
                    else:
                        st.error(message)
def user_profile_page():
    """用户个人资料页面"""
    st.header("👤 个人中心")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("基本信息")
        st.write(f"**用户名**: {st.session_state.username}")
        st.write(f"**用户类型**: {st.session_state.user_data['user_type']}")
        st.write(f"**注册时间**: {st.session_state.user_data['created_at'][:10]}")

        if st.session_state.user_data['user_type'] == "农场主":
            st.subheader("农场信息")
            farm_info = st.session_state.user_data.get('farm_info', {})
            st.write(f"**农场名称**: {farm_info.get('farm_name', '未填写')}")
            st.write(f"**总面积**: {farm_info.get('total_area', 0)}亩")
            st.write(f"**所在地**: {farm_info.get('location', '未填写')}")
            st.write(f"**主要作物**: {farm_info.get('main_crops', '未填写')}")

    with col2:
        st.subheader("偏好设置")

        with st.form("preferences_form"):
            risk_level = st.select_slider(
                "风险偏好",
                options=["极度保守", "保守", "稳健", "积极", "极度积极"],
                value=st.session_state.user_data['preferences']['risk_level']
            )

            st.write("优化目标权重")
            economic_weight = st.slider("经济效益", 0.0, 1.0,
                                        st.session_state.user_data['preferences']['economic_weight'])
            stability_weight = st.slider("稳定性", 0.0, 1.0,
                                         st.session_state.user_data['preferences']['stability_weight'])
            sustainability_weight = st.slider("可持续性", 0.0, 1.0,
                                              st.session_state.user_data['preferences']['sustainability_weight'])

            # 检查权重总和是否为1
            total_weight = economic_weight + stability_weight + sustainability_weight
            if abs(total_weight - 1.0) > 0.01:
                st.warning(f"权重总和为 {total_weight:.2f}，请调整为1.0")

            if st.form_submit_button("保存偏好"):
                preferences = {
                    'risk_level': risk_level,
                    'economic_weight': economic_weight,
                    'stability_weight': stability_weight,
                    'sustainability_weight': sustainability_weight
                }
                if update_user_preferences(st.session_state.username, preferences):
                    st.session_state.user_data['preferences'] = preferences
                    st.success("偏好设置已保存！")

    # 注销按钮
    st.markdown("---")
    if st.button("🚪 退出登录", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_data = None
        st.rerun()


def admin_page():
    """管理员页面"""
    if st.session_state.user_data['user_type'] != "管理员":
        st.error("无权限访问此页面")
        return

    st.header("⚙️ 系统管理")

    users = load_users()

    st.subheader("用户管理")
    user_data = []
    for username, user_info in users.items():
        user_data.append({
            '用户名': username,
            '用户类型': user_info['user_type'],
            '注册时间': user_info['created_at'][:10],
            '农场名称': user_info.get('farm_info', {}).get('farm_name', '无')
        })

    user_df = pd.DataFrame(user_data)
    st.dataframe(user_df, use_container_width=True)

    # 用户统计
    st.subheader("用户统计")
    user_types = user_df['用户类型'].value_counts()
    fig = px.pie(values=user_types.values, names=user_types.index,
                 title="用户类型分布")
    st.plotly_chart(fig, use_container_width=True)


def data_management_page():
    """数据管理页面"""
    st.header("📁 数据管理")

    tab1, tab2, tab3 = st.tabs(["📊 种植数据", "💰 效益数据", "📥 数据导入"])

    with tab1:
        st.subheader("种植数据管理")

        # 从用户数据加载或使用示例数据
        user_planting_data = get_user_data(st.session_state.username, 'planting_data')

        if user_planting_data is not None:
            planting_df = pd.DataFrame(user_planting_data)
            st.success("已加载您的种植数据")
        else:
            st.info("您尚未上传种植数据，当前使用示例数据")
            planting_df = get_sample_planting_data()

        # 显示数据
        st.dataframe(planting_df, use_container_width=True)

        # 数据编辑
        st.subheader("编辑种植数据")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("添加新记录", use_container_width=True):
                if 'new_planting_rows' not in st.session_state:
                    st.session_state.new_planting_rows = []
                st.session_state.new_planting_rows.append({
                    '种植地块': '', '作物名称': '', '作物类型': '',
                    '种植面积/亩': 0.0, '种植季次': '单季'
                })

        with col2:
            if st.button("保存种植数据", type="primary", use_container_width=True):
                if save_user_data(st.session_state.username, 'planting_data', planting_df.to_dict('records')):
                    st.success("种植数据保存成功！")
                else:
                    st.error("保存失败")

        # 添加新记录的表单
        if 'new_planting_rows' in st.session_state:
            for i, row in enumerate(st.session_state.new_planting_rows):
                with st.expander(f"新记录 {i + 1}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        row['种植地块'] = st.text_input("种植地块", value=row['种植地块'], key=f"plot_{i}")
                        row['作物名称'] = st.text_input("作物名称", value=row['作物名称'], key=f"crop_{i}")
                    with col2:
                        row['作物类型'] = st.selectbox("作物类型",
                                                       ["粮食", "粮食（豆类）", "经济作物", "蔬菜", "水果", "其他"],
                                                       key=f"type_{i}")
                        row['种植面积/亩'] = st.number_input("种植面积/亩",
                                                             min_value=0.0, value=row['种植面积/亩'], key=f"area_{i}")
                    with col3:
                        row['种植季次'] = st.selectbox("种植季次",
                                                       ["单季", "双季", "多季"], key=f"season_{i}")

                    if st.button("确认添加", key=f"confirm_{i}"):
                        new_row = pd.DataFrame([row])
                        planting_df = pd.concat([planting_df, new_row], ignore_index=True)
                        st.session_state.new_planting_rows.pop(i)
                        st.rerun()

    with tab2:
        st.subheader("效益数据管理")

        # 从用户数据加载或使用示例数据
        user_benefit_data = get_user_data(st.session_state.username, 'benefit_data')

        if user_benefit_data is not None:
            benefit_df = pd.DataFrame(user_benefit_data)
            st.success("已加载您的效益数据")
        else:
            st.info("您尚未上传效益数据，当前使用示例数据")
            benefit_df = get_sample_benefit_data()

        # 计算亩效益
        benefit_df['亩效益/元'] = benefit_df['亩产量/斤'] * benefit_df['销售单价/(元/斤)'] - benefit_df[
            '种植成本/(元/亩)']

        # 显示数据
        st.dataframe(benefit_df, use_container_width=True)

        # 数据编辑
        st.subheader("编辑效益数据")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("添加新效益记录", use_container_width=True):
                if 'new_benefit_rows' not in st.session_state:
                    st.session_state.new_benefit_rows = []
                st.session_state.new_benefit_rows.append({
                    '作物名称': '', '亩产量/斤': 0, '种植成本/(元/亩)': 0,
                    '销售单价/(元/斤)': 0.0, '地块类型': '平旱地'
                })

        with col2:
            if st.button("保存效益数据", type="primary", use_container_width=True):
                if save_user_data(st.session_state.username, 'benefit_data', benefit_df.to_dict('records')):
                    st.success("效益数据保存成功！")
                else:
                    st.error("保存失败")

        # 添加新记录的表单
        if 'new_benefit_rows' in st.session_state:
            for i, row in enumerate(st.session_state.new_benefit_rows):
                with st.expander(f"新效益记录 {i + 1}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        row['作物名称'] = st.text_input("作物名称", value=row['作物名称'], key=f"bcrop_{i}")
                        row['亩产量/斤'] = st.number_input("亩产量/斤",
                                                           min_value=0, value=row['亩产量/斤'], key=f"yield_{i}")
                        row['种植成本/(元/亩)'] = st.number_input("种植成本/(元/亩)",
                                                                  min_value=0, value=row['种植成本/(元/亩)'],
                                                                  key=f"cost_{i}")
                    with col2:
                        row['销售单价/(元/斤)'] = st.number_input("销售单价/(元/斤)",
                                                                  min_value=0.0, value=row['销售单价/(元/斤)'],
                                                                  key=f"price_{i}")
                        row['地块类型'] = st.selectbox("地块类型",
                                                       ["平旱地", "水浇地", "大棚", "梯田", "山坡地"],
                                                       key=f"land_{i}")

                    if st.button("确认添加", key=f"bconfirm_{i}"):
                        new_row = pd.DataFrame([row])
                        benefit_df = pd.concat([benefit_df, new_row], ignore_index=True)
                        st.session_state.new_benefit_rows.pop(i)
                        st.rerun()

    with tab3:
        st.subheader("批量数据导入")

        col1, col2 = st.columns(2)

        with col1:
            st.info("种植数据模板")
            sample_planting = get_sample_planting_data()
            csv_planting = sample_planting.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下载种植数据模板",
                data=csv_planting,
                file_name="种植数据模板.csv",
                mime="text/csv",
                use_container_width=True
            )

            uploaded_planting = st.file_uploader("上传种植数据CSV", type=['csv'], key="planting_upload")
            if uploaded_planting is not None:
                try:
                    df_planting = pd.read_csv(uploaded_planting)
                    required_cols = ['种植地块', '作物名称', '作物类型', '种植面积/亩', '种植季次']
                    if all(col in df_planting.columns for col in required_cols):
                        if save_user_data(st.session_state.username, 'planting_data', df_planting.to_dict('records')):
                            st.success("种植数据导入成功！")
                        else:
                            st.error("导入失败")
                    else:
                        st.error(f"CSV文件必须包含以下列: {', '.join(required_cols)}")
                except Exception as e:
                    st.error(f"文件读取错误: {str(e)}")

        with col2:
            st.info("效益数据模板")
            sample_benefit = get_sample_benefit_data()
            csv_benefit = sample_benefit.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下载效益数据模板",
                data=csv_benefit,
                file_name="效益数据模板.csv",
                mime="text/csv",
                use_container_width=True
            )

            uploaded_benefit = st.file_uploader("上传效益数据CSV", type=['csv'], key="benefit_upload")
            if uploaded_benefit is not None:
                try:
                    df_benefit = pd.read_csv(uploaded_benefit)
                    required_cols = ['作物名称', '亩产量/斤', '种植成本/(元/亩)', '销售单价/(元/斤)', '地块类型']
                    if all(col in df_benefit.columns for col in required_cols):
                        if save_user_data(st.session_state.username, 'benefit_data', df_benefit.to_dict('records')):
                            st.success("效益数据导入成功！")
                        else:
                            st.error("导入失败")
                    else:
                        st.error(f"CSV文件必须包含以下列: {', '.join(required_cols)}")
                except Exception as e:
                    st.error(f"文件读取错误: {str(e)}")


def get_sample_planting_data():
    """获取示例种植数据"""
    return pd.DataFrame({
        '种植地块': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1', 'B2', 'B3', 'B4'],
        '作物名称': ['小麦', '玉米', '玉米', '黄豆', '绿豆', '谷子', '小麦', '黑豆', '红豆', '绿豆'],
        '作物类型': ['粮食', '粮食', '粮食', '粮食（豆类）', '粮食（豆类）', '粮食', '粮食', '粮食（豆类）', '粮食（豆类）',
                     '粮食（豆类）'],
        '种植面积/亩': [80.0, 55.0, 35.0, 72.0, 68.0, 55.0, 60.0, 46.0, 40.0, 28.0],
        '种植季次': ['单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季']
    })


def get_sample_benefit_data():
    """获取示例效益数据"""
    return pd.DataFrame({
        '作物名称': ['小麦', '玉米', '黄豆', '绿豆', '黑豆', '红豆', '谷子', '西红柿', '黄瓜', '香菇'],
        '亩产量/斤': [600, 800, 400, 350, 500, 400, 450, 3000, 4000, 2000],
        '种植成本/(元/亩)': [500, 600, 400, 350, 400, 350, 400, 1200, 1500, 8000],
        '销售单价/(元/斤)': [1.5, 1.2, 3.0, 7.0, 7.5, 8.0, 2.0, 2.5, 2.0, 15.0],
        '地块类型': ['平旱地', '平旱地', '平旱地', '平旱地', '平旱地', '平旱地', '平旱地', '水浇地', '大棚', '大棚']
    })


def load_user_or_sample_data():
    """加载用户数据或示例数据"""
    # 尝试加载用户数据
    planting_data = get_user_data(st.session_state.username, 'planting_data')
    benefit_data = get_user_data(st.session_state.username, 'benefit_data')

    # 如果用户数据不存在，使用示例数据
    if planting_data is None:
        planting_data = get_sample_planting_data()
    else:
        planting_data = pd.DataFrame(planting_data)

    if benefit_data is None:
        benefit_data = get_sample_benefit_data()
    else:
        benefit_data = pd.DataFrame(benefit_data)

    # 计算亩效益
    benefit_data['亩效益/元'] = benefit_data['亩产量/斤'] * benefit_data['销售单价/(元/斤)'] - benefit_data[
        '种植成本/(元/亩)']

    return planting_data, benefit_data


def create_dashboard(planting_data, benefit_data):
    """数据驾驶舱"""
    st.header("📊 农业数据驾驶舱")

    # 显示用户个性化欢迎信息
    user_type = st.session_state.user_data['user_type']
    if user_type == "农场主":
        farm_name = st.session_state.user_data.get('farm_info', {}).get('farm_name', '您的农场')
        st.success(f"👋 欢迎回来，{farm_name}的管理者！")
    else:
        st.success(f"👋 欢迎回来，{st.session_state.username}！")

    # 数据来源提示
    user_planting_data = get_user_data(st.session_state.username, 'planting_data')
    user_benefit_data = get_user_data(st.session_state.username, 'benefit_data')

    if user_planting_data is None or user_benefit_data is None:
        st.warning("💡 当前使用示例数据，请前往【数据管理】上传您的真实数据以获得个性化分析")

    # 关键指标
    col1, col2, col3, col4 = st.columns(4)
    total_area = planting_data['种植面积/亩'].sum()
    crop_types = planting_data['作物类型'].nunique()
    crop_varieties = planting_data['作物名称'].nunique()

    with col1:
        st.metric("总种植面积", f"{total_area}亩")
    with col2:
        st.metric("作物种类", f"{crop_varieties}种")
    with col3:
        st.metric("地块数量", f"{len(planting_data)}个")
    with col4:
        avg_benefit = benefit_data['亩效益/元'].mean()
        st.metric("平均亩效益", f"¥{avg_benefit:.0f}")

    # 种植结构分析
    st.subheader("种植结构分析")
    col1, col2 = st.columns(2)

    with col1:
        # 作物类型分布
        type_dist = planting_data.groupby('作物类型')['种植面积/亩'].sum().reset_index()
        fig_pie = px.pie(type_dist, values='种植面积/亩', names='作物类型',
                         title="作物类型面积分布", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # 主要作物面积
        crop_dist = planting_data.groupby('作物名称')['种植面积/亩'].sum().nlargest(10).reset_index()
        fig_bar = px.bar(crop_dist, x='作物名称', y='种植面积/亩',
                         title="主要作物种植面积", color='种植面积/亩')
        st.plotly_chart(fig_bar, use_container_width=True)

    # 效益分析
    st.subheader("经济效益分析")
    col1, col2 = st.columns(2)

    with col1:
        # 亩效益排名
        top_crops = benefit_data.nlargest(10, '亩效益/元')
        fig_benefit = px.bar(top_crops, x='作物名称', y='亩效益/元',
                             title="作物亩效益排名", color='亩效益/元')
        st.plotly_chart(fig_benefit, use_container_width=True)

    with col2:
        # 成本收益分析
        fig_scatter = px.scatter(benefit_data, x='种植成本/(元/亩)', y='亩效益/元',
                                 size='亩产量/斤', color='作物名称',
                                 title="成本-收益分析", hover_data=['销售单价/(元/斤)'])
        st.plotly_chart(fig_scatter, use_container_width=True)


def create_planner(planting_data, benefit_data):
    """智能规划器 - 集成真实算法"""
    st.header("🧮 智能种植规划器")

    # 使用用户偏好设置
    preferences = st.session_state.user_data['preferences']

    # 参数配置
    with st.sidebar:
        st.subheader("优化参数配置")

        years = st.slider("规划年限", 1, 7, 3)
        risk_level = st.select_slider(
            "风险偏好",
            options=["极度保守", "保守", "稳健", "积极", "极度积极"],
            value=preferences['risk_level']
        )

        st.subheader("优化目标权重")
        economic_weight = st.slider("经济效益", 0.0, 1.0, preferences['economic_weight'])
        stability_weight = st.slider("稳定性", 0.0, 1.0, preferences['stability_weight'])
        sustainability_weight = st.slider("可持续性", 0.0, 1.0, preferences['sustainability_weight'])

        st.subheader("约束条件")
        min_bean_rotation = st.checkbox("强制豆类轮作", True)
        avoid_same_crop = st.checkbox("避免重茬种植", True)
        min_plot_size = st.slider("最小地块种植面积", 1.0, 20.0, 5.0)

        # 计算总面积
        total_area = st.number_input("规划总面积（亩）",
                                     min_value=10.0,
                                     max_value=10000.0,
                                     value=float(planting_data['种植面积/亩'].sum()),
                                     step=10.0)

    # 方案生成
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("智能规划")

        if st.button("🚀 生成优化方案", type="primary", use_container_width=True):
            with st.spinner("正在使用优化算法计算最优种植方案..."):
                # 使用真实算法
                preferences = {
                    'risk_level': risk_level,
                    'economic_weight': economic_weight,
                    'stability_weight': stability_weight,
                    'sustainability_weight': sustainability_weight
                }

                optimizer = AgriculturalOptimizer(planting_data, benefit_data, preferences)
                result = optimizer.optimize_planting_plan(total_area, years)

                if result['status'] == 'optimal':
                    # 显示优化结果
                    display_real_optimization_result(result, optimizer)
                else:
                    st.error(f"优化失败: {result.get('message', '未知错误')}")

    with col2:
        st.subheader("快速建议")
        st.info("💡 **基于算法的即时建议**")

        # 使用算法生成建议
        optimizer = AgriculturalOptimizer(planting_data, benefit_data, preferences)
        suitability_scores = optimizer.calculate_crop_suitability()

        # 推荐高适应性作物
        top_crops = sorted(suitability_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        st.write("推荐高适应性作物:")
        for crop, score in top_crops:
            st.write(f"• {crop} (适应性评分: {score:.2f})")

        # 风险提示
        current_risk = np.mean(list(suitability_scores.values()))
        if current_risk < 0.4:
            st.warning("当前种植结构风险较高，建议增加豆类作物比例")


def display_real_optimization_result(result, optimizer):
    """显示真实优化算法结果"""
    st.success(f"✅ 优化方案生成成功！预计整体收益提升 {result['expected_improvement']:.1f}%")

    # 显示分配结果
    st.subheader("📊 优化种植方案")

    allocation_data = []
    for crop, allocation in result['crop_allocations'].items():
        allocation_data.append({
            '作物名称': crop,
            '分配面积/亩': allocation['area'],
            '占比/%': allocation['percentage'],
            '预期收益/元': allocation['expected_benefit']
        })

    allocation_df = pd.DataFrame(allocation_data)
    st.dataframe(allocation_df.style.format({
        '分配面积/亩': '{:.1f}',
        '占比/%': '{:.1f}%',
        '预期收益/元': '¥{:.0f}'
    }), use_container_width=True)

    # 风险分析
    risk_result = optimizer.risk_analysis(result['crop_allocations'])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总体风险评估", f"{risk_result['overall_risk']:.2f}")
    with col2:
        st.metric("预期总投资", f"¥{risk_result['total_investment']:,.0f}")
    with col3:
        st.metric("预期投资回报率", f"{risk_result['roi']:.1f}%")

    # 可视化结果
    col1, col2 = st.columns(2)

    with col1:
        # 面积分配饼图
        fig_area = px.pie(allocation_df, values='分配面积/亩', names='作物名称',
                          title="种植面积分配")
        st.plotly_chart(fig_area, use_container_width=True)

    with col2:
        # 收益贡献条形图
        fig_benefit = px.bar(allocation_df, x='作物名称', y='预期收益/元',
                             title="各作物预期收益贡献",
                             color='预期收益/元')
        st.plotly_chart(fig_benefit, use_container_width=True)

    # 详细分析报告
    st.subheader("📈 详细分析报告")

    with st.expander("查看详细分析", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**优化效果**")
            st.write(f"- 总规划面积: {result['total_area']}亩")
            st.write(f"- 已分配面积: {result['allocated_area']:.1f}亩")
            st.write(f"- 面积利用率: {(result['allocated_area'] / result['total_area']) * 100:.1f}%")
            st.write(f"- 预期收益提升: {result['expected_improvement']:.1f}%")

        with col2:
            st.write("**风险控制**")
            st.write(f"- 总体风险评分: {risk_result['overall_risk']:.2f}")
            st.write(f"- 投资回报率: {risk_result['roi']:.1f}%")
            st.write(f"- 作物多样性: {len(result['crop_allocations'])}种")

            # 风险提示
            if risk_result['overall_risk'] > 0.7:
                st.error("⚠️ 高风险方案，建议调整")
            elif risk_result['overall_risk'] > 0.5:
                st.warning("⚠️ 中等风险方案")
            else:
                st.success("✅ 低风险方案")


def create_risk_simulator(benefit_data):
    """风险模拟器 - 集成价格预测算法"""
    st.header("⚠️ 风险模拟分析")

    tab1, tab2, tab3 = st.tabs(["💰 价格波动预测", "🌦️ 气候影响", "📜 政策变化"])

    with tab1:
        st.subheader("市场价格预测与波动模拟")

        # 价格预测
        col1, col2 = st.columns(2)
        with col1:
            selected_crop = st.selectbox("选择作物", benefit_data['作物名称'].unique())
            prediction_months = st.slider("预测月数", 3, 24, 12)

        with col2:
            if st.button("开始价格预测", type="primary"):
                with st.spinner("训练价格预测模型中..."):
                    predictor = PricePredictor()
                    if predictor.train(benefit_data):
                        predictions = predictor.predict(selected_crop, prediction_months)

                        if predictions is not None:
                            # 显示预测结果
                            fig = px.line(predictions, x='date', y='predicted_price',
                                          title=f"{selected_crop}未来价格预测",
                                          labels={'predicted_price': '预测价格 (元/斤)', 'date': '日期'})
                            st.plotly_chart(fig, use_container_width=True)

                            # 统计信息
                            current_price = \
                            benefit_data[benefit_data['作物名称'] == selected_crop]['销售单价/(元/斤)'].iloc[0]
                            avg_predicted = predictions['predicted_price'].mean()
                            change_percent = ((avg_predicted - current_price) / current_price) * 100

                            col1, col2, col3 = st.columns(3)
                            col1.metric("当前价格", f"¥{current_price:.2f}")
                            col2.metric("预测均价", f"¥{avg_predicted:.2f}")
                            col3.metric("预期变化", f"{change_percent:+.1f}%")
                    else:
                        st.error("价格预测模型训练失败")

        # 敏感性分析
        st.subheader("敏感性分析")
        col1, col2 = st.columns(2)

        with col1:
            price_change = st.slider("价格变化幅度", -50, 50, 0, format="%d%%")
            yield_change = st.slider("产量变化幅度", -30, 30, 0, format="%d%%")

        with col2:
            cost_change = st.slider("成本变化幅度", -20, 20, 0, format="%d%%")
            selected_crop_risk = st.selectbox("分析作物", benefit_data['作物名称'].unique(), key="risk_crop")

        # 模拟影响
        crop_data = benefit_data[benefit_data['作物名称'] == selected_crop_risk].iloc[0]
        original_profit = crop_data['亩效益/元']

        new_price = crop_data['销售单价/(元/斤)'] * (1 + price_change / 100)
        new_yield = crop_data['亩产量/斤'] * (1 + yield_change / 100)
        new_cost = crop_data['种植成本/(元/亩)'] * (1 + cost_change / 100)

        new_profit = new_yield * new_price - new_cost
        profit_change = (new_profit - original_profit) / original_profit * 100

        # 显示结果
        col1, col2 = st.columns(2)
        with col1:
            st.metric("原亩效益", f"¥{original_profit:.0f}")
        with col2:
            st.metric("新亩效益", f"¥{new_profit:.0f}", f"{profit_change:+.1f}%")

    with tab2:
        st.subheader("气候情景模拟")
        scenario = st.selectbox(
            "选择气候情景",
            ["正常年份", "轻度干旱", "严重干旱", "洪涝灾害", "低温冻害", "高温热害"]
        )

        scenarios_data = {
            '情景': ['正常年份', '轻度干旱', '严重干旱', '洪涝灾害', '低温冻害', '高温热害'],
            '产量影响': [0, -15, -40, -25, -20, -10],
            '成本影响': [0, 10, 25, 30, 15, 5],
            '发生概率': [60, 20, 5, 8, 4, 3]
        }

        scenarios_df = pd.DataFrame(scenarios_data)
        selected_scenario = scenarios_df[scenarios_df['情景'] == scenario].iloc[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("产量影响", f"{selected_scenario['产量影响']}%")
        with col2:
            st.metric("成本影响", f"+{selected_scenario['成本影响']}%")
        with col3:
            st.metric("发生概率", f"{selected_scenario['发生概率']}%")

        st.dataframe(scenarios_df, use_container_width=True)

    with tab3:
        st.subheader("政策变化模拟")
        st.info("政策变化对农业种植结构的影响分析")

        policy_options = st.multiselect(
            "选择政策变化",
            ["粮食补贴增加", "生态补偿机制", "农业保险推广", "水资源管理加强", "碳排放要求"],
            default=["粮食补贴增加"]
        )

        if policy_options:
            st.success("已选择政策变化分析")
            # 这里可以添加具体的政策影响分析逻辑

def random_disease_detection():
    """随机生成病变识别结果"""
    # 常见作物病变类型
    diseases = [
        {"name": "白粉病", "confidence": round(random.uniform(0.75, 0.98), 2), "suggestion": "及时喷施三唑类杀菌剂，加强田间通风透光，降低湿度"},
        {"name": "霜霉病", "confidence": round(random.uniform(0.72, 0.95), 2), "suggestion": "选用甲霜灵锰锌、烯酰吗啉等药剂喷雾，避免大水漫灌"},
        {"name": "叶斑病", "confidence": round(random.uniform(0.68, 0.93), 2), "suggestion": "摘除病叶集中烧毁，喷施多菌灵、百菌清等保护性杀菌剂"},
        {"name": "蚜虫侵害", "confidence": round(random.uniform(0.70, 0.96), 2), "suggestion": "使用吡虫啉、啶虫脒等药剂，搭配黄板诱杀，保护瓢虫等天敌"},
        {"name": "无明显病变", "confidence": round(random.uniform(0.80, 0.99), 2), "suggestion": "作物生长状态良好，继续保持现有田间管理，定期巡查即可"},
        {"name": "病毒病", "confidence": round(random.uniform(0.65, 0.88), 2), "suggestion": "及时拔除病株，防治蚜虫、蓟马等传毒媒介，喷施宁南霉素预防"},
        {"name": "炭疽病", "confidence": round(random.uniform(0.73, 0.94), 2), "suggestion": "喷施咪鲜胺、苯醚甲环唑等药剂，避免偏施氮肥，增施磷钾肥"}
    ]
    return random.choice(diseases)


def create_disease_detection():
    """作物病变识别页面"""
    st.header("🔍 作物病变识别")
    st.info("上传作物叶片图片（模拟摄像头拍摄），系统将自动识别病变类型")

    # 图片上传（模拟摄像头功能）
    col1, col2 = st.columns([1, 2])
    with col1:
        uploaded_file = st.file_uploader("选择叶片图片", type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            # 显示上传的图片
            st.image(uploaded_file, caption="上传的叶片图片", use_column_width=True)

            # 识别按钮
            if st.button("开始识别", type="primary", use_container_width=True):
                with st.spinner("正在分析叶片状态..."):
                    # 随机生成识别结果
                    result = random_disease_detection()
                    # 存储结果到会话状态
                    st.session_state.disease_result = result
                    st.rerun()
        else:
            st.session_state.pop("disease_result", None)

    # 显示识别结果
    with col2:
        st.subheader("识别结果")
        if "disease_result" in st.session_state:
            result = st.session_state.disease_result

            # 结果卡片
            st.markdown(f"""
            <div style="background-color:#f0f8fb; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="margin:0; color:#2d3748;">病变类型：{result['name']}</h4>
                <p style="margin:10px 0; color:#4a5568;">置信度：{result['confidence']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

            # 应对建议
            st.subheader("田间管理建议")
            st.markdown(f"""
            <div style="background-color:#f5fafe; padding:15px; border-radius:8px; border-left:4px solid #4299e1;">
                <p style="margin:0; color:#2d3748;">{result['suggestion']}</p>
            </div>
            """, unsafe_allow_html=True)

            # 额外提示
            st.info("💡 提示：本功能为演示版本，实际应用需结合深度学习模型和真实病害数据训练")
        else:
            st.markdown("""
            <div style="background-color:#f8f8f8; padding:40px; border-radius:10px; text-align:center; color:#718096;">
                <p>请上传叶片图片并点击"开始识别"</p>
                <p style="font-size:12px; margin-top:10px;">支持JPG、JPEG、PNG格式</p>
            </div>
            """, unsafe_allow_html=True)
def create_benefit_analysis(benefit_data, planting_data):
    """效益分析"""
    st.header("💵 经济效益深度分析")

    # 总体效益概览
    col1, col2, col3 = st.columns(3)

    total_potential = benefit_data['亩效益/元'].sum()
    avg_efficiency = benefit_data['亩效益/元'].mean()
    max_benefit_crop = benefit_data.loc[benefit_data['亩效益/元'].idxmax(), '作物名称']

    with col1:
        st.metric("总效益潜力", f"¥{total_potential:.0f}")
    with col2:
        st.metric("平均亩效益", f"¥{avg_efficiency:.0f}")
    with col3:
        st.metric("效益最高作物", max_benefit_crop)

    # 效益分布分析
    st.subheader("效益分布分析")
    col1, col2 = st.columns(2)

    with col1:
        # 效益分布直方图
        fig_hist = px.histogram(benefit_data, x='亩效益/元',
                                title="亩效益分布", nbins=20)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        # 地块类型效益对比
        fig_box = px.box(benefit_data, x='地块类型', y='亩效益/元',
                         title="不同地块类型效益对比")
        st.plotly_chart(fig_box, use_container_width=True)

    # 投入产出分析
    st.subheader("投入产出效率分析")

    benefit_data['投入产出比'] = benefit_data['亩效益/元'] / benefit_data['种植成本/(元/亩)']
    efficient_crops = benefit_data.nlargest(10, '投入产出比')

    fig_efficiency = px.bar(efficient_crops, x='作物名称', y='投入产出比',
                            title="作物投入产出比排名", color='投入产出比')
    st.plotly_chart(fig_efficiency, use_container_width=True)

    # 详细数据表
    st.subheader("详细效益数据")
    display_data = benefit_data[['作物名称', '地块类型', '亩产量/斤', '种植成本/(元/亩)',
                                 '销售单价/(元/斤)', '亩效益/元', '投入产出比']].copy()
    display_data = display_data.round({'亩效益/元': 0, '投入产出比': 2})

    st.dataframe(display_data, use_container_width=True)


def create_about_page():
    """关于项目页面"""
    st.header("🌾 关于方寸云耕")

    st.markdown("""
    ### 项目背景

    **方寸云耕**是一个基于数据驱动的智慧农业决策平台，旨在通过先进的数学建模和优化算法，
    为山区农业提供科学的种植决策支持，助力乡村振兴战略实施。

    ### 核心功能

    - 📊 **数据驾驶舱**: 全方位可视化农业数据，洞察种植结构与效益分布
    - 🧮 **智能规划器**: 基于多目标优化的种植方案推荐，平衡经济、风险与可持续性
    - ⚠️ **风险模拟器**: 模拟价格、气候、政策等多重风险，提供应对策略
    - 💵 **效益分析**: 深度分析经济效益，识别优化机会
    - 👤 **用户系统**: 完整的账号管理和个性化设置
    - 📁 **数据管理**: 支持用户上传和管理自己的农场数据

    ### 技术特色

    - 🔐 **安全认证**: 基于哈希密码的用户认证系统
    - 🎯 **个性化配置**: 支持用户偏好设置和个性化推荐
    - 📊 **灵活数据源**: 支持用户上传真实数据和CSV批量导入
    - 🔬 **多目标优化算法**: 综合考虑经济效益、资源利用、风险控制等多重目标
    - 📈 **不确定性建模**: 处理市场价格、气候变化等不确定因素
    - 🌐 **交互式可视化**: 直观展示分析结果和优化方案

    ### 应用价值

    本平台可为农业决策者提供：
    - 科学的数据支撑和决策依据
    - 风险预警和应对方案
    - 经济效益优化建议
    - 长期可持续发展规划

    ### 开发团队

    本项目由李思凡开发，融合了运筹优化、数据分析和农业科学的跨学科专业知识。
    """)

    st.info("💡 提示: 这是一个演示原型，实际应用需要接入真实数据和更复杂的算法模型")


def account_management_page():
    """账号管理页面"""
    st.header("👥 账号管理系统")

    if st.session_state.user_data['user_type'] != "管理员":
        st.error("需要管理员权限")
        return

    users = load_users()

    # 显示所有账号状态
    st.subheader("账号状态总览")

    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    total_users = len(users)
    predefined_users = len([u for u in users.values() if u.get('is_predefined', False)])
    redeemed_users = len([u for u in users.values() if u.get('is_predefined', False) and u.get('redeemed', False)])
    temp_users = len([u for u in users.values() if u.get('is_temporary', False)])

    col1.metric("总用户数", total_users)
    col2.metric("预定义账号", predefined_users)
    col3.metric("已兑换", redeemed_users)
    col4.metric("临时用户", temp_users)

    # 账号列表
    st.subheader("账号列表")

    account_data = []
    for username, user_info in users.items():
        account_type = "预定义" if user_info.get('is_predefined', False) else "临时"
        status = "已兑换" if user_info.get('redeemed', False) else "未兑换" if user_info.get('is_predefined',
                                                                                             False) else "活跃"

        account_data.append({
            '用户名': username,
            '用户类型': user_info['user_type'],
            '账号类型': account_type,
            '状态': status,
            '注册时间': user_info['created_at'][:10]
        })

    account_df = pd.DataFrame(account_data)
    st.dataframe(account_df, use_container_width=True)

    # 兑换码管理
    st.subheader("兑换码管理")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**可用兑换码**")
        for code, username in REDEMPTION_CODES.items():
            user_status = "已兑换" if users[username].get('redeemed', False) else "未使用"
            status_color = "🔴" if users[username].get('redeemed', False) else "🟢"
            st.write(f"{status_color} `{code}` → {username} ({user_status})")

    with col2:
        st.write("**重置账号状态**")
        reset_username = st.selectbox("选择账号", [u for u in PREDEFINED_ACCOUNTS.keys()])

        if st.button("重置为未兑换状态", type="secondary"):
            if reset_username in users:
                users[reset_username]['redeemed'] = False
                save_users(users)
                st.success(f"已重置 {reset_username} 的兑换状态")
                st.rerun()
def main():
    """主应用"""
    # 初始化用户系统 - 确保预定义账号被加载
    init_users()

    # 初始化会话状态
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None

    # 检查登录状态
    if not st.session_state.logged_in:
        login_page()
        return

    # 加载数据
    planting_data, benefit_data = load_user_or_sample_data()

    # 侧边栏导航
    st.sidebar.title(f"🌾 方寸云耕")
    st.sidebar.write(f"欢迎，**{st.session_state.username}**")
    st.sidebar.markdown("---")

    # 根据用户类型显示不同的导航菜单
    user_type = st.session_state.user_data['user_type']

    if user_type == "管理员":
        menu_items = ["数据驾驶舱", "智能规划器", "风险模拟器", "效益分析", "聊天咨询", "作物病变识别", "数据管理",
                      "账号管理", "个人中心", "关于项目"]
    else:
        menu_items = ["数据驾驶舱", "智能规划器", "风险模拟器", "效益分析", "聊天咨询", "作物病变识别", "数据管理",
                      "个人中心", "关于项目"]

    page = st.sidebar.radio("导航菜单", menu_items, index=0)

    # 在侧边栏添加一些实用信息
    st.sidebar.markdown("---")

    # 显示数据状态
    user_planting_data = get_user_data(st.session_state.username, 'planting_data')
    user_benefit_data = get_user_data(st.session_state.username, 'benefit_data')

    if user_planting_data is not None and user_benefit_data is not None:
        st.sidebar.success("✅ 使用用户数据")
    else:
        st.sidebar.warning("📊 使用示例数据")

    st.sidebar.info(f"""
    **平台状态**: 运行中  
    **用户类型**: {user_type}  
    **数据更新**: 2025年11月1日  
    **版本**: v2.1 算法版
    """)

    # 页面路由
    if page == "数据驾驶舱":
        create_dashboard(planting_data, benefit_data)
    elif page == "智能规划器":
        create_planner(planting_data, benefit_data)
    elif page == "风险模拟器":
        create_risk_simulator(benefit_data)
    elif page == "效益分析":
        create_benefit_analysis(benefit_data, planting_data)
    elif page == "数据管理":
        data_management_page()
    elif page == "个人中心":
        user_profile_page()
    elif page == "账号管理":
        account_management_page()
    elif page == "作物病变识别":
        create_disease_detection()
    elif page == "聊天咨询":
        chat_page()
    else:
        create_about_page()
if __name__ == "__main__":
    main()