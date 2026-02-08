for tab, name, df_raw in zip(tabs, periods, data_list):
        with tab:
            if df_raw.empty:
                st.warning(f"{name} 无数据")
                continue
            
            # --- 第一步：计算全量 BBIBOLL ---
            df_bb = compute_bbiboll(df_raw, n=param_n, k=param_k)
            
            if df_bb.empty:
                st.warning(f"{name} 数据量不足以计算指标")
                continue

            # 判定每一行是否收敛 (增加标志位列)
            df_bb["IS_CONVERGING"] = df_bb["WIDTH_RATIO"] <= threshold

            # --- 第二步：当前状态看板 (Top Section) ---
            current_row = df_bb.iloc[-1]
            is_conv = current_row["IS_CONVERGING"]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("最新收盘价", f"{current_row['close']:.2f}")
            c2.metric("当前带宽比", f"{current_row['WIDTH_RATIO']*100:.2f}%")
            # 使用 delta 显示与阈值的差距
            diff = current_row['WIDTH_RATIO'] - threshold
            c3.metric("状态", "✅ 已收敛" if is_conv else "❌ 波动中", 
                      delta=f"{diff*100:.2f}%", delta_color="inverse")
            c4.metric("数据总量", f"{len(df_bb)} 行")

            # --- 第三步：可视化与明细 (Bottom Section) ---
            # 展示计算后的指标数据（最近 50 条）
            st.markdown("#### 🚀 计算结果明细 (最近 50 条)")
            # 这里的 dataframe 会包含 BBI_UPPER, BBI_LOWER, WIDTH_RATIO 等所有新列
            st.dataframe(df_bb.tail(50).style.applymap(
                lambda x: 'background-color: rgba(0, 255, 0, 0.2)' if x == True else '', 
                subset=['IS_CONVERGING']
            ), use_container_width=True)

            with st.expander("查看原始数据及完整指标"):
                st.write(df_bb) # 展示全量数据

            # --- 第四步：存入汇总 ---
            results_summary.append({
                "周期": name,
                "收敛": "✅" if is_conv else "❌",
                "带宽比": f"{current_row['WIDTH_RATIO']*100:.2f}%",
                "最新时间": current_row['datetime'].strftime("%Y-%m-%d %H:%M")
            })
