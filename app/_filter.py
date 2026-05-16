"""
给明细表加上列筛选控件 + 分页
"""
import streamlit as st
import pandas as pd

PAGE_SIZE = 500


def txs_to_dataframe(tx_list, max_rows=99999):
    """将Transaction列表转为DataFrame"""
    rows = []
    for tx in tx_list[:max_rows]:
        rows.append({
            '时间': tx.transaction_time,
            '类型': tx.transaction_type,
            '对方': tx.counterparty,
            '商品说明': (tx.product_desc[:40] + '..') if len(tx.product_desc) > 40 else tx.product_desc,
            '收支': tx.income_expense_type,
            '金额': tx.amount,
            '支付方式': tx.payment_method,
            '状态': tx.status,
            '来源': tx.source,
            '出差': '是' if tx.business_trip else '',
        })
    return pd.DataFrame(rows)


def filter_detail_table(df, full_tx_list, key_prefix="filter"):
    """返回筛选后的完整DataFrame"""
    full_df = txs_to_dataframe(full_tx_list, max_rows=99999)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        months = ['全部'] + sorted(full_df['时间'].str[:7].unique().tolist())
        sel_month = st.selectbox('月份', months, key=f'{key_prefix}_month')
    with col2:
        types = ['全部'] + sorted(full_df['类型'].unique().tolist())
        sel_type = st.selectbox('类型', types, key=f'{key_prefix}_type')
    with col3:
        ie_types = ['全部'] + sorted(full_df['收支'].unique().tolist())
        sel_ie = st.selectbox('收支', ie_types, key=f'{key_prefix}_ie')
    with col4:
        sources = ['全部'] + sorted(full_df['来源'].unique().tolist())
        sel_source = st.selectbox('来源', sources, key=f'{key_prefix}_source')
    with col5:
        methods = ['全部'] + sorted(full_df['支付方式'].unique().tolist())
        sel_method = st.selectbox('支付方式', methods, key=f'{key_prefix}_method')

    result = full_df.copy()
    if sel_month != '全部':
        result = result[result['时间'].str.startswith(sel_month)]
    if sel_type != '全部':
        result = result[result['类型'] == sel_type]
    if sel_ie != '全部':
        result = result[result['收支'] == sel_ie]
    if sel_source != '全部':
        result = result[result['来源'] == sel_source]
    if sel_method != '全部':
        result = result[result['支付方式'] == sel_method]

    # 搜索框：按对方名或商品说明模糊搜索
    search = st.text_input('🔍 搜索对方名或商品说明', key=f'{key_prefix}_search')
    if search:
        mask = result['对方'].str.contains(search, na=False) | result['商品说明'].str.contains(search, na=False)
        result = result[mask]

    return result


def show_paginated_table(df, key_prefix="page"):
    """分页显示DataFrame，控件在底部"""
    total = len(df)
    per_page = PAGE_SIZE
    total_pages = max(1, (total + per_page - 1) // per_page)

    state_key = f'{key_prefix}_page'
    if state_key not in st.session_state:
        st.session_state[state_key] = 1

    page = st.session_state[state_key]
    page = min(page, total_pages)
    start = (page - 1) * per_page
    end = min(start + per_page, total)

    # 表格
    page_df = df.iloc[start:end].reset_index(drop=True)
    st.dataframe(page_df, use_container_width=True, hide_index=True,
                 column_config={'金额': st.column_config.NumberColumn(format='%.2f')})

    # 底部翻页
    cols = st.columns([1, 2, 1, 2, 1])
    with cols[0]:
        if st.button('‹ 上一页', key=f'{key_prefix}_prev', disabled=(page <= 1)):
            st.session_state[state_key] = page - 1
            st.rerun()
    with cols[1]:
        new_page = st.number_input('', min_value=1, max_value=total_pages,
                                   value=page, key=f'{key_prefix}_num',
                                   label_visibility='collapsed')
        if new_page != page:
            st.session_state[state_key] = new_page
            st.rerun()
    with cols[2]:
        st.caption(f'第 {start+1}-{end} 条')
    with cols[3]:
        st.caption(f'共 {total} 条')
    with cols[4]:
        if st.button('下一页 ›', key=f'{key_prefix}_next', disabled=(page >= total_pages)):
            st.session_state[state_key] = page + 1
            st.rerun()

    # 下载按钮（右下对齐）
    import io
    excel_buf = io.BytesIO()
    df.to_excel(excel_buf, index=False, engine='openpyxl')
    excel_buf.seek(0)
    st.download_button(
        label='⬇ 下载 Excel',
        data=excel_buf,
        file_name=f'{key_prefix}_data.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key=f'{key_prefix}_dl')
