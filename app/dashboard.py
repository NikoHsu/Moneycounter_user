"""
MoneyCounter 可视化仪表盘
运行：conda activate moneycounter && streamlit run app/dashboard.py
"""

import sys, os, json
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config_loader import get_config
from src.transaction import Transaction
from src.analyzer import Analyzer
from src.manual_loader import load_recurring_expenses, load_housing_fund
from app._filter import filter_detail_table, show_paginated_table, txs_to_dataframe

st.set_page_config(page_title="MoneyCounter 财务仪表盘", layout="wide")

# ---- 隐私辅助函数 ----
def s(val, fmt=",.2f"):
    """隐私保护：隐藏时返回****"""
    if st.session_state.get('show_amounts', True):
        return f"{val:{fmt}}"
    return "****"

def s_pct(val):
    """隐私保护百分比"""
    if st.session_state.get('show_amounts', True):
        return f"{val}%"
    return "****"

# ---- 数据加载（每次刷新重读，不用缓存避免混淆） ----
def load_data():
    config = get_config()
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    all_txs = []

    for fn in ['app_data.json', 'bank_data.json']:
        fp = os.path.join(data_dir, fn)
        if os.path.exists(fp):
            with open(fp, 'r', encoding='utf-8') as f:
                records = json.load(f)
            txs = [Transaction(r, config=config) for r in records]
            all_txs.extend(txs)

    # 加载手动补充数据（房租等）
    manual_records = load_recurring_expenses()
    for r in manual_records:
        all_txs.append(Transaction(dict(r), config=config))

    # 加载公积金月缴数据
    fund_records = load_housing_fund()
    for r in fund_records:
        all_txs.append(Transaction(dict(r), config=config))

    return all_txs, config

transactions, config = load_data()
analyzer = Analyzer(transactions)



# ---- 侧边栏：时间选择 ----
st.sidebar.title("💰 MoneyCounter")

# 获取所有可用的年月
all_months = sorted(set(tx.year_month for tx in transactions if tx._parsed_time))
all_years = sorted(set(str(tx.year) for tx in transactions if tx.year > 0))

st.sidebar.markdown("### 📅 时间范围")

view_mode = st.sidebar.radio("查看模式", ["按月", "按年", "自定义"], horizontal=True)

if view_mode == "按月":
    selected_month = st.sidebar.selectbox("选择月份", all_months if all_months else ["全部"])
    if selected_month:
        txs = [tx for tx in transactions if tx.year_month == selected_month]
    else:
        txs = transactions
    date_label = selected_month

elif view_mode == "按年":
    selected_year = st.sidebar.selectbox("选择年份", all_years if all_years else ["全部"])
    if selected_year and selected_year != "全部":
        txs = [tx for tx in transactions if str(tx.year) == selected_year]
    else:
        txs = transactions
    date_label = selected_year if selected_year != "全部" else "全部"

else:  # 自定义
    dates = [tx._parsed_time for tx in transactions if tx._parsed_time]
    min_date = min(dates).date() if dates else date(2025, 1, 1)
    max_date = max(dates).date() if dates else date(2026, 12, 31)

    start = st.sidebar.date_input("开始日期", min_date, min_value=min_date, max_value=max_date)
    end = st.sidebar.date_input("结束日期", max_date, min_value=min_date, max_value=max_date)

    txs = [tx for tx in transactions if tx._parsed_time and start <= tx._parsed_time.date() <= end]
    date_label = f"{start} ~ {end}"

# 隐私开关移入侧边栏
if 'show_amounts' not in st.session_state:
    st.session_state.show_amounts = True
st.sidebar.markdown("---")
eye_label = '👁 公开' if st.session_state.show_amounts else '👁‍🗨 隐藏'
if st.sidebar.button(eye_label, key='toggle_privacy'):
    st.session_state.show_amounts = not st.session_state.show_amounts
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.caption("运行: streamlit run app/dashboard.py")
st.sidebar.caption("Made by Niko & Q宝 🐾")
st.sidebar.markdown("---")

# ---- 顶部：核心指标卡片 ----
daily_inc = round(sum(tx.amount for tx in txs
                      if tx.is_income() and not tx.is_personal_transfer()
                      and tx.status not in ('退款', '失败')), 2)
daily_exp = round(sum(tx.amount for tx in txs
                      if tx.is_expense() and not tx.is_refund()
                      and tx.status not in ('退款', '失败')), 2)

# 差旅池净收入
tf = analyzer.travel_fund_summary(txs)
travel_net = round(tf['balance'], 2)

# 公积金池净收入
hf = analyzer.housing_fund_summary(txs)
housing_net = round(hf['balance'], 2)

# 总收入 = 日常收入 + 差旅净收入 + 公积金净收入
inc = round(daily_inc + travel_net + housing_net, 2)
exp = daily_exp
net = round(inc - exp, 2)
margin = f"{round(net / inc * 100, 1)}%" if inc > 0 else "0%"



inc_str = f"{inc:,.2f} 元" if st.session_state.show_amounts else '****元'
exp_str = f"{exp:,.2f} 元" if st.session_state.show_amounts else '****元'
net_str = f"{net:,.2f} 元" if st.session_state.show_amounts else '****元'
margin_str = margin

col1, col2, col3, col4 = st.columns(4)
col1.metric("📈 总收入", inc_str)
if st.session_state.show_amounts:
    col1.markdown(f'<p style="color:#00c853;font-size:0.8rem">日常 {daily_inc:,.0f} + 差旅 {travel_net:,.0f} + 公积金 {hf["balance"]:,.0f}</p>', unsafe_allow_html=True)
else:
    col1.markdown('<p style="color:#00c853;font-size:0.8rem">日常 **** + 差旅**** + 公积金****</p>', unsafe_allow_html=True)
col2.metric("📉 总支出", exp_str)
col3.metric("💎 净利润", net_str, delta=margin_str)
col4.metric("📊 交易笔数", f"{len(txs)} 笔")

# 计算时间跨度月数（按实际日期范围算）
parsed_times = [tx._parsed_time for tx in txs if tx._parsed_time]
if parsed_times:
    days_span = (max(parsed_times) - min(parsed_times)).days
    months_span = max(1, round(days_span / 30.44))
else:
    months_span = 1
hourly_rate = net / (months_span * 720)
work_hour_rate = net / (months_span * 192)

col5, col6 = st.columns(2)
hr_str = f"{hourly_rate:.2f} 元/h" if st.session_state.show_amounts else '***元/h'
whr_str = f"{work_hour_rate:.2f} 元/h" if st.session_state.show_amounts else '***元/h'
col5.metric("⏱ 单位时间产值", hr_str, delta=f"{months_span}月×720h")
col6.metric("💼 工作小时产值", whr_str, delta=f"{months_span}月×192h")

st.markdown("---")

# ---- Tab 布局 ----
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 收入结构", "💳 支出结构", "📈 净利润分析",
    "📉 时间曲线", "🧳 差旅池", "🏠 公积金池", "🎯 财务自由进度"
])

# ============================================
# TAB 1: 收入结构分析
# ============================================
with tab1:
    st.subheader(f"收入结构分析 ({date_label})")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**收入来源 TOP10**")
        inc_src = analyzer.income_source_summary(txs)
        if not inc_src.empty:
            # 加入池子收入（仅正数才显示）
            pool_rows = []
            if travel_net > 0:
                pool_rows.append({'source': '差旅余额', 'amount': travel_net})
            if housing_net > 0:
                pool_rows.append({'source': '公积金净贡献', 'amount': housing_net})
            if pool_rows:
                import pandas as pd
                inc_src = pd.concat([inc_src, pd.DataFrame(pool_rows)], ignore_index=True)
                inc_src = inc_src.sort_values('amount', ascending=False).head(10)
            fig = px.pie(inc_src.head(10), values='amount', names='source',
                         title='收入来源占比',
                         color_discrete_sequence=px.colors.sequential.Blues_r)
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**收入类型分布**")
        inc_type = analyzer.income_type_summary(txs)
        if not inc_type.empty:
            fig = px.bar(inc_type.head(10), x='type', y='amount',
                         text='percentage',
                         title='收入类型金额',
                         color='amount',
                         color_continuous_scale='Blues')
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    # 收入逐笔明细
    with st.expander("📋 查看逐笔收入明细"):
        inc_txs = [tx for tx in txs if tx.is_income() and not tx.is_personal_transfer()]
        df = txs_to_dataframe(inc_txs)
        if not df.empty:
            df = filter_detail_table(df, inc_txs, key_prefix='inc')
            show_paginated_table(df, key_prefix='inc')
        else:
            st.info('当前筛选条件下无收入记录')

# ============================================
# TAB 2: 支出结构分析
# ============================================
with tab2:
    st.subheader(f"支出结构分析 ({date_label})")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**支出分类占比**")
        exp_cat = analyzer.expense_category_summary(txs)
        if not exp_cat.empty:
            fig = px.pie(exp_cat, values='amount', names='category',
                         title='支出分类占比',
                         color_discrete_sequence=px.colors.sequential.Reds_r)
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**支出分类金额**")
        if not exp_cat.empty:
            fig = px.bar(exp_cat, x='category', y='amount',
                         text='percentage',
                         title='各分类支出',
                         color='amount',
                         color_continuous_scale='Reds')
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    # 支出逐笔明细
    with st.expander("📋 查看逐笔支出明细"):
        exp_txs = [tx for tx in txs if tx.is_expense() and not tx.is_refund()]
        df = txs_to_dataframe(exp_txs)
        if not df.empty:
            df = filter_detail_table(df, exp_txs, key_prefix='exp')
            show_paginated_table(df, key_prefix='exp')
        else:
            st.info('当前筛选条件下无支出记录')

# ============================================
# TAB 3: 净利润分析
# ============================================
with tab3:
    st.subheader(f"净利润分析 ({date_label})")

    pa = analyzer.profit_analysis(txs)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("总收入", s(pa['total_income']))
    col_b.metric("总支出", s(pa['total_expense']))
    col_c.metric("净利润", s(pa['net_profit']),
                 delta=s_pct(pa['profit_margin']) if st.session_state.get('show_amounts', True) else '****')

    # 月度净利润柱状图
    st.markdown("---")
    st.markdown("**月度净利润趋势**")
    monthly = analyzer.time_series_monthly(txs)
    if not monthly.empty:
        colors = ['#ff4b4b' if v < 0 else '#00c853' for v in monthly['净利润']]
        fig = go.Figure(data=[
            go.Bar(name='净利润', x=monthly['month'], y=monthly['净利润'],
                   marker_color=colors)
        ])
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(title='月度净利润', yaxis_title='元')
        st.plotly_chart(fig, use_container_width=True)

    # 全部交易逐笔明细
    with st.expander("📋 查看当前所有交易明细"):
        df = txs_to_dataframe(txs, max_rows=99999)
        if not df.empty:
            df = filter_detail_table(df, txs, key_prefix='all')
            show_paginated_table(df, key_prefix='all')

    # 收入 vs 支出对比
    st.markdown("**收入 vs 支出月度对比**")
    if not monthly.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name='收入', x=monthly['month'], y=monthly['收入'],
                             marker_color='#2196F3'))
        fig.add_trace(go.Bar(name='支出', x=monthly['month'], y=monthly['支出'],
                             marker_color='#FF5722'))
        fig.update_layout(barmode='group', title='月度收支对比', yaxis_title='元')
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# TAB 4: 时间曲线（3线并排）
# ============================================
with tab4:
    st.subheader(f"收入·支出·净利润 时间曲线 ({date_label})")

    view_toggle = st.radio("时间粒度", ["按月", "按年"], horizontal=True)

    if view_toggle == "按月":
        ts = analyzer.time_series_monthly(txs)
        x_col = 'month'
    else:
        ts = analyzer.time_series_yearly(txs)
        x_col = 'year'

    if not ts.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts[x_col], y=ts['收入'], mode='lines+markers',
            name='收入', line=dict(color='#2196F3', width=3),
            marker=dict(size=8)))
        fig.add_trace(go.Scatter(
            x=ts[x_col], y=ts['支出'], mode='lines+markers',
            name='支出', line=dict(color='#FF5722', width=3),
            marker=dict(size=8)))
        fig.add_trace(go.Scatter(
            x=ts[x_col], y=ts['净利润'], mode='lines+markers',
            name='净利润', line=dict(color='#4CAF50', width=3),
            marker=dict(size=8)))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            title='收入 / 支出 / 净利润 时间序列',
            yaxis_title='金额 (元)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # 逐笔明细
        with st.expander("📋 查看逐笔交易明细"):
            df = txs_to_dataframe(txs, max_rows=99999)
            if not df.empty:
                df = filter_detail_table(df, txs, key_prefix='ts')
                show_paginated_table(df, key_prefix='ts')

        # 汇总数据表
        with st.expander("查看汇总数据"):
            st.dataframe(ts, use_container_width=True, hide_index=True)
    else:
        st.info("所选时间段内无数据")

# ============================================
# TAB 5: 差旅池
# ============================================
with tab5:
    st.subheader(f"🧳 差旅池分析 ({date_label})")

    # 差旅池汇总
    tf = analyzer.travel_fund_summary(txs)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("💰 差旅收入（报销+补贴）", s(tf['biz_income']) + ' 元')
    col_b.metric("🏨 酒店支出", s(tf['biz_expense']) + ' 元')
    delta_color = "normal" if tf['balance'] >= 0 else "inverse"
    col_c.metric("📊 差旅余额", s(tf['balance']) + ' 元',
                 delta=f"{'盈余' if tf['balance']>=0 else '垫付中'}")

    st.markdown("")
    st.info(
        "差旅池 = 报销收入 − 酒店支出。"
        "正数表示补贴结余（有赚），负数表示还有酒店费用待报销（先垫付）。小交通按消费计算。"
        "差旅收支已从日常收支中剥离，不影响净收入计算。"
    )

    # 月度差旅池曲线
    st.markdown("---")
    st.markdown("**差旅池月度趋势**")
    tf_monthly = analyzer.travel_fund_monthly(txs)
    if not tf_monthly.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(name='报销收入', x=tf_monthly['month'], y=tf_monthly['报销收入'],
                             marker_color='#4CAF50'))
        fig.add_trace(go.Bar(name='酒店支出', x=tf_monthly['month'], y=tf_monthly['酒店支出'],
                             marker_color='#FF5722'))
        fig.add_trace(go.Scatter(name='累计余额', x=tf_monthly['month'], y=tf_monthly['累计余额'],
                                 mode='lines+markers', line=dict(color='#2196F3', width=3),
                                 yaxis='y2'))
        fig.update_layout(
            title='差旅池月度明细',
            yaxis=dict(title='金额 (元)'),
            yaxis2=dict(title='累计余额 (元)', overlaying='y', side='right'),
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 查看差旅明细"):
            biz_txs = [tx for tx in txs if tx.business_trip]
            df = txs_to_dataframe(biz_txs, max_rows=99999)
            if not df.empty:
                df = filter_detail_table(df, biz_txs, key_prefix='biz')
                show_paginated_table(df, key_prefix='biz')
    else:
        st.info("所选时间段内无差旅记录")

# ============================================
# TAB 6: 公积金池
# ============================================
with tab6:
    st.subheader(f"🏠 公积金池 ({date_label})")

    hf = analyzer.housing_fund_summary(txs)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("💰 月缴总额", s(hf['fund_income']) + ' 元')
    col_b.metric(f"🏦 提取 {hf['xtract_count']} 笔", s(hf['xtract_total']) + ' 元')
    col_c.metric("📊 公积金净贡献", s(hf['balance']) + ' 元')

    st.markdown("")
    st.info(
        "公积金池只跟踪月缴部分。"
        "每年提取的 15,000 元已计入日常收入（实打实到银行卡），不在此处重复计算。"
    )

    st.markdown("---")
    st.markdown("**公积金月度明细**")
    hf_monthly = analyzer.housing_fund_monthly(txs)
    if not hf_monthly.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(name='月缴', x=hf_monthly['month'], y=hf_monthly['月缴'],
                             marker_color='#9C27B0'))
        fig.add_trace(go.Scatter(name='累计', x=hf_monthly['month'], y=hf_monthly['累计'],
                                 mode='lines+markers', line=dict(color='#4CAF50', width=3)))
        fig.update_layout(
            title='公积金月缴明细',
            yaxis=dict(title='金额 (元)'),
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("所选时间段内无公积金数据")

# ============================================
# TAB 7: 财务自由度
# ============================================
with tab7:
    st.subheader("🎯 财务自由进度")

    # 计算累计净利润（全部历史数据）
    all_inc = sum(tx.amount for tx in transactions
                  if tx.is_income() and not tx.is_personal_transfer())
    all_exp = sum(tx.amount for tx in transactions
                  if tx.is_expense() and not tx.is_refund())
    net_assets = round(all_inc - all_exp, 2)

    target = 3000000  # 300万

    ff = analyzer.financial_freedom(net_assets, target)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("💰 当前净资产", s(ff['net_assets']) + ' 元')
    col_b.metric("🎯 目标本金", f"{ff['target']:,.0f} 元 (300万)")
    col_c.metric("📊 财务自由度", s_pct(ff['ratio']),
                 delta=f"{ff['ratio']-100:.1f}%" if ff['ratio'] >= 25 else "加油!")

    # ---- 进度条 ----
    st.markdown("---")
    st.markdown("### 📊 财务自由进度")

    ratio = min(ff['ratio'], 100)  # 最高显示到100%

    # 用 plotly 做带刻度的进度条
    fig = go.Figure()

    # 主进度条
    fig.add_trace(go.Bar(
        x=[ratio],
        y=['财务自由度'],
        orientation='h',
        marker=dict(
            color=ratio,
            colorscale=[
                [0, '#ff4444'],      # 0% 红
                [0.25, '#ffaa00'],   # 25% 橙
                [0.5, '#ffdd00'],    # 50% 黄
                [1.0, '#00c853'],    # 100% 绿
            ],
            cmin=0, cmax=100,
        ),
        text=f"{ff['ratio']}%",
        textposition='inside',
        insidetextanchor='middle',
        width=0.4,
    ))

    # 里程碑竖线
    milestones = [
        (25, '25% 初步安心', '#ffaa00'),
        (50, '50% 半自由', '#ffdd00'),
        (100, '100% 财务自由 🎉', '#00c853'),
    ]
    for pos, label, color in milestones:
        fig.add_vline(x=pos, line_dash="dash", line_color=color,
                      opacity=0.7, annotation_text=label,
                      annotation_position="top")

    fig.update_layout(
        xaxis=dict(range=[0, 110], title='进度 (%)',
                   tickvals=[0, 10, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]),
        height=200,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        title='当前进度: 当前净资产 ÷ 目标本金(300万) × 100%',
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---- 里程碑卡片 ----
    st.markdown("### 🏆 里程碑")
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)

    milestones_detail = [
        (mcol1, "25% 初步安心", "当财务自由度达到 25%，\n意味着被动收入能覆盖\n日常基本开支的 25%", ff['milestone_25']),
        (mcol2, "50% 半自由", "当财务自由度达到 50%，\n意味着你已经有了一半的\n财务自由保障", ff['milestone_50']),
        (mcol3, "100% 财务自由", "当财务自由度达到 100%，\n你已实现真正的财务自由！", ff['milestone_100']),
    ]

    # 还需多少
    remaining = target - net_assets
    # 用全部历史数据的月均结余来推算
    all_parsed = [tx._parsed_time for tx in transactions if tx._parsed_time]
    if all_parsed:
        all_months = max(1, round((max(all_parsed) - min(all_parsed)).days / 30.44))
    else:
        all_months = 1
    monthly_save = net_assets / all_months if all_months > 0 else 0
    months_to_go = remaining / monthly_save if monthly_save > 0 else 999
    years_to_go = months_to_go / 12

    for col, title, desc, achieved in milestones_detail:
        with col:
            if achieved:
                st.success(f"✅ **{title}**")
                st.caption(f"{desc}\n\n🎉 已达成！")
            else:
                st.info(f"⏳ **{title}**")
                st.caption(f"{desc}")

    mcol4.metric("还需积累", s(remaining, ',.0f') + ' 元')
    if years_to_go < 100:
        mcol4.metric("预计还需", f"{years_to_go:.1f} 年" if years_to_go > 1 else f"{months_to_go:.0f} 个月")
    else:
        mcol4.metric("预计还需", "数据不足")

    # ---- 详细计算 ----
    with st.expander("查看详细计算"):
        st.json({
            "当前净资产（累计收入-支出）": net_assets,
            "目标本金": target,
            "财务自由度": f"{ff['ratio']}%",
            "还需积累金额": remaining,
            "当前期间月均结余": round(monthly_save, 2),
            "预计达到目标（月）": round(months_to_go, 1),
            "预计达到目标（年）": round(years_to_go, 1),
        })


