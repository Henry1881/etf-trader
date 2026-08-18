import os
from datetime import datetime
from typing import Dict, List
from src.utils.config_loader import ConfigLoader


class ReportGenerator:
    def __init__(self):
        self.config = ConfigLoader().config
        self.report_dir = self.config["output"]["report_dir"]
        self.etf_info = {
            "588170": {
                "name": "科创半导体ETF华夏",
                "sector": "半导体设备",
                "benefit_factors": [
                    "半导体设备国产替代趋势明确，政策支持持续加码",
                    "AI需求推动半导体产业链景气度上升",
                    "资金持续净流入，机构看好长期逻辑"
                ],
                "risk_factors": [
                    "全球半导体周期仍存不确定性",
                    "前期涨幅较大，存在回调压力",
                    "规模过大(357亿)可能影响调仓灵活性"
                ]
            },
            "159611": {
                "name": "广发中证全指电力ETF",
                "sector": "电力行业",
                "benefit_factors": [
                    "夏季用电高峰期到来，电力需求旺盛",
                    "电力改革持续推进，行业基本面改善",
                    "绿色电力发展政策支持"
                ],
                "risk_factors": [
                    "短期涨幅较大，存在获利回吐压力",
                    "电价改革不确定性",
                    "煤炭价格波动影响发电成本"
                ]
            },
            "159227": {
                "name": "华夏国证航天航空ETF",
                "sector": "军工行业",
                "benefit_factors": [
                    "军工行业业绩稳健，订单充足",
                    "估值处于历史低位，有修复空间",
                    "国防预算持续增长"
                ],
                "risk_factors": [
                    "市场风险偏好下降，成长股承压",
                    "短期缺乏催化因素",
                    "地缘政治不确定性"
                ]
            },
            "159272": {
                "name": "机器人ETF富国",
                "sector": "机器人/智能制造",
                "benefit_factors": [
                    "机器人产业长期增长空间大",
                    "AI+机器人融合发展趋势明确",
                    "有资金逢低布局"
                ],
                "risk_factors": [
                    "短期业绩不及预期",
                    "市场对成长股风险偏好下降",
                    "技术落地进度不及预期"
                ]
            },
            "159622": {
                "name": "创新药ETF沪港深",
                "sector": "创新药",
                "benefit_factors": [
                    "创新药政策支持持续",
                    "港股创新药板块估值修复",
                    "研发管线丰富，创新成果逐步兑现"
                ],
                "risk_factors": [
                    "短期涨幅较大，存在获利回吐压力",
                    "药品集采政策影响",
                    "研发失败风险"
                ]
            }
        }

    def generate_etf_report(self, etf_name: str, symbol: str, signal_result: dict) -> str:
        indicators = signal_result["indicators"]
        final_signal = signal_result["final_signal"]
        signal_strength = signal_result["signal_strength"]
        signal_direction = signal_result["signal_direction"]
        component_signals = signal_result["component_signals"]

        info = self.etf_info.get(symbol, {})
        recommendations = self._generate_recommendations(symbol, indicators, final_signal)

        report = f"### {etf_name} ({symbol})\n\n"

        report += "#### 📊 基本信息\n"
        report += "| 指标 | 值 |\n|------|-----|\n"
        if indicators.get("price"):
            price = indicators["price"]
            # ETF 价格常在 1 元附近，用 3 位小数避免精度丢失
            report += f"| 最新价 | ¥{price['close']:.3f} |\n"
            # 优先用 signal_result 中传递的 price_change，否则用 prev_close 计算
            prev_close = price.get('prev_close', price['close'])
            if prev_close and prev_close > 0:
                change = ((price['close'] - prev_close) / prev_close) * 100
            else:
                change = 0.0
            # 如果 signal_result 里有 price_change，优先用（来自通达信实时行情）
            if "price_change" in signal_result:
                change = signal_result["price_change"]
            report += f"| 日涨跌幅 | {change:+.2f}% |\n"
            report += f"| 最高价 | ¥{price['high']:.3f} |\n"
            report += f"| 最低价 | ¥{price['low']:.3f} |\n"
            report += f"| 成交量 | {self._format_volume(price['volume'])} |\n"
        report += "\n"

        report += "#### 📉 技术分析\n\n"

        if indicators.get("ma"):
            ma = indicators["ma"]
            report += "**移动平均线**:\n"
            for key, value in ma.items():
                if key != "trend" and not isinstance(value, str):
                    # MA 用 4 位小数（ETF 价格小，2 位会丢精度）
                    report += f"- {key.upper()}: ¥{value:.4f}"
                    if key == "ma_5" and indicators.get("price"):
                        if indicators["price"]["close"] > value:
                            report += "，价格位于均线上方，短期趋势向上"
                        else:
                            report += "，价格位于均线下方，短期趋势向下"
                    report += "\n"
            report += f"- 趋势: {self._format_trend(ma.get('trend', 'neutral'))}\n\n"

        if indicators.get("rsi"):
            rsi = indicators["rsi"]
            report += "**RSI指标**:\n"
            report += f"- 当前RSI为{rsi['value']:.1f}，"
            if rsi["value"] < 30:
                report += "处于超卖区域，存在技术性反弹需求\n"
            elif rsi["value"] > 70:
                report += "处于超买区域，存在回调风险\n"
            else:
                report += "处于正常区域\n"
            report += "\n"

        if indicators.get("macd"):
            macd = indicators["macd"]
            report += "**MACD指标**:\n"
            report += f"- MACD: {macd['macd']:.4f}，Signal: {macd['signal']:.4f}\n"
            if macd["hist"] > 0:
                report += "- 红柱，多头力量占优"
            else:
                report += "- 绿柱，空头力量占优"
            if macd.get("crossover") == "golden_cross":
                report += "，形成金叉，中期趋势可能反转向上\n"
            elif macd.get("crossover") == "death_cross":
                report += "，形成死叉，中期趋势可能反转向下\n"
            else:
                report += "\n"
            report += "\n"

        if indicators.get("bollinger"):
            bb = indicators["bollinger"]
            report += "**布林带**:\n"
            # BB 价格用 4 位小数
            report += f"- 上轨¥{bb['upper']:.4f}，中轨¥{bb['middle']:.4f}，下轨¥{bb['lower']:.4f}\n"
            # 修复：bb['percent'] 是 0~1 的小数，不是 0~100，判断阈值应为 0.5
            report += f"- 价格位于中轨{'上方' if bb['percent'] > 0.5 else '下方'}({bb['percent']:.1%})\n\n"

        if indicators.get("price"):
            report += "**成交量**:\n"
            report += f"- {self._format_volume(indicators['price']['volume'])}\n\n"

        report += "#### 🔍 基本面分析\n\n"

        report += "**利好因素**:\n"
        for factor in info.get("benefit_factors", ["暂无明确利好因素"]):
            report += f"- {factor}\n"
        report += "\n"

        report += "**利空因素**:\n"
        for factor in info.get("risk_factors", ["暂无明确利空因素"]):
            report += f"- {factor}\n"
        report += "\n"

        report += "#### 💡 交易建议\n\n"
        report += "| 项目 | 建议 |\n|------|------|\n"
        report += f"| **操作信号** | {self._format_signal(final_signal)} |\n"
        report += f"| **建议买入价** | {recommendations['buy_price']} |\n"
        report += f"| **目标价** | {recommendations['target_price']} |\n"
        report += f"| **止损价** | {recommendations['stop_loss']} |\n"

        # 多维度置信度
        confidence = signal_result.get("confidence", signal_strength)
        confidence_level = signal_result.get("confidence_level", "")
        report += f"| **置信度** | {confidence:.1f}/10（{confidence_level}） |\n\n"

        # 置信度构成明细
        breakdown = signal_result.get("confidence_breakdown", {})
        if breakdown:
            dirs = breakdown.get("directions", {})
            report += "**置信度构成**:\n"
            report += f"- 指标一致性: {breakdown.get('consistency', 0):.1f}/4 "
            report += f"（看多{dirs.get('bullish',0)} / 看空{dirs.get('bearish',0)} / 中性{dirs.get('neutral',0)}）\n"
            report += f"- 信号强度: {breakdown.get('strength', 0):.1f}/3"
            if breakdown.get("has_strong_signal"):
                report += "（含强信号: 金叉/死叉/超买/超卖）"
            report += "\n"
            report += f"- 趋势明确度: {breakdown.get('trend', 0):.1f}/2\n"
            report += f"- 数据质量: {breakdown.get('data_quality', 0):.1f}/1\n"
            report += "\n"

        report += f"**理由**: {recommendations['reason']}\n\n"

        return report

    def generate_daily_report(self, etf_results: Dict[str, dict], data_meta: Dict = None) -> str:
        report = f"# ETF每日分析报告\n\n"
        # 优先用 data_meta 中的 last_trade_date，避免补生成时日期不准
        report_date = data_meta.get("last_trade_date") if data_meta else None
        if report_date:
            report += f"**分析日期**: {report_date}\n"
        else:
            report += f"**分析日期**: {datetime.now().strftime('%Y年%m月%d日')}\n"
        if etf_results:
            report += f"**分析标的**: {', '.join(etf_results.keys())}\n"
        else:
            report += f"**分析标的**: 588170, 159611, 159227, 159272, 159622\n"
        report += f"**报告类型**: 明日买入/卖出建议\n\n"

        if data_meta:
            report += f"**数据来源**: {data_meta.get('source', 'akshare/东方财富')}\n"
            report += f"**最后交易日**: {data_meta.get('last_trade_date', '未知')}\n"
            if data_meta.get('validated'):
                report += f"**数据校验**: ✅ 已通过一致性校验\n"
            quality = data_meta.get('quality_score', 0)
            if quality > 0:
                report += f"**数据质量**: {'✅' if quality >= 80 else '⚠️' if quality >= 50 else '❌'} {quality}/100\n"
            warnings = data_meta.get('warnings', [])
            if warnings:
                report += f"**数据警告**:\n"
                for w in warnings:
                    report += f"  - {w}\n"
            report += "\n"

        if not etf_results:
            report += "---\n\n"
            report += "## ⚠️ 数据获取异常说明\n\n"
            report += "本次报告生成过程中，所有ETF的行情数据获取均失败。\n"
            report += f"失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            report += "**可能原因**:\n"
            report += "1. 数据源（东方财富）网络连接异常\n"
            report += "2. 当日为非交易日\n"
            report += "3. ETF代码校验失败\n"
            report += "4. 网络防火墙或代理阻断\n\n"
            report += "**建议**:\n"
            report += "- 检查网络连接是否正常\n"
            report += "- 确认当日为A股交易日\n"
            report += "- 稍后重试或手动查阅行情\n\n"
            report += "本报告为占位报告，不具备参考价值，请以实际行情为准。\n\n"
            report += "---\n\n"
            report += "**免责声明**: 本报告仅供参考，不构成任何投资建议。\n"
            return report

        report += "---\n\n"

        report += "## 📊 执行摘要\n\n"
        report += "### 市场概况\n\n"

        semiconductors = etf_results.get("588170", {})
        power = etf_results.get("159611", {})
        aerospace = etf_results.get("159227", {})
        robot = etf_results.get("159272", {})
        pharma = etf_results.get("159622", {})

        report += "今日市场板块分化明显：\n"
        if semiconductors.get("signal", {}).get("final_signal") == "buy":
            report += "- **半导体板块**: 强势反弹，建议关注买入机会\n"
        else:
            report += "- **半导体板块**: 震荡整理\n"
        report += "- **电力板块**: 延续近期强势表现\n"
        report += "- **航天航空/机器人**: 继续承压\n"
        report += "- **创新药板块**: 小幅回升\n\n"

        buy_count = sum(1 for r in etf_results.values() if r["signal"]["final_signal"] == "buy")
        sell_count = sum(1 for r in etf_results.values() if r["signal"]["final_signal"] == "sell")
        hold_count = len(etf_results) - buy_count - sell_count

        report += "### 整体信号汇总\n\n"
        report += "| 信号类型 | 数量 | ETF代码 |\n"
        report += "|---------|------|---------|\n"
        report += f"| 🟢 买入 | {buy_count} | {', '.join([k for k, v in etf_results.items() if v['signal']['final_signal'] == 'buy']) if buy_count else '—'} |\n"
        report += f"| 🔴 卖出 | {sell_count} | {', '.join([k for k, v in etf_results.items() if v['signal']['final_signal'] == 'sell']) if sell_count else '—'} |\n"
        report += f"| ⚪ 持有 | {hold_count} | {', '.join([k for k, v in etf_results.items() if v['signal']['final_signal'] not in ['buy', 'sell']]) if hold_count else '—'} |\n\n"

        report += "---\n\n"

        report += "## 📈 个股ETF分析\n\n"
        report += "---\n\n"

        order = ["588170", "159611", "159227", "159272", "159622"]
        for symbol in order:
            if symbol in etf_results:
                result = etf_results[symbol]
                etf_report = self.generate_etf_report(
                    result["name"],
                    symbol,
                    result["signal"]
                )
                report += etf_report
                report += "---\n\n"

        report += "## 📋 总结与风险提示\n\n"
        report += "### 📊 综合建议\n\n"
        report += "| ETF代码 | ETF名称 | 建议 | 置信度 | 等级 |\n"
        report += "|---------|---------|------|--------|------|\n"
        for symbol in order:
            if symbol in etf_results:
                result = etf_results[symbol]
                sig = result['signal']
                conf = sig.get('confidence', sig.get('signal_strength', 0))
                level = sig.get('confidence_level', '')
                report += f"| {symbol} | {result['name']} | {self._format_signal(sig['final_signal'])} | {conf:.1f}/10 | {level} |\n"
        report += "\n"

        # 置信度说明
        report += "**置信度说明**:\n"
        report += "- 置信度 = 指标一致性(0-4) + 信号强度(0-3) + 趋势明确度(0-2) + 数据质量(0-1)\n"
        report += "- 高(≥7.0): 多指标共振，可参考操作 | 中(4.0-6.9): 有一定支撑，谨慎参考 | 低(<4.0): 信号混乱，建议观望\n\n"

        report += "### ⚠️ 风险提示\n\n"
        report += "1. **市场风险**: 宏观经济数据、政策变化可能导致市场剧烈波动\n"
        report += "2. **板块轮动**: 当前市场风格切换频繁，需警惕热点快速转换\n"
        report += "3. **流动性风险**: 部分ETF规模较小，可能存在流动性不足风险\n"
        report += "4. **数据局限性**: 本报告基于公开数据，实际市场情况可能有所不同\n"
        report += "5. **技术指标风险**: 技术指标存在滞后性，仅供参考，不保证未来走势\n\n"

        report += "### 💡 投资策略建议\n\n"
        report += "- **激进投资者**: 可关注买入信号标的的介入机会\n"
        report += "- **稳健投资者**: 建议以持有为主，等待更明确的信号\n"
        report += "- **风险控制**: 任何操作都应设置合理止损，控制仓位\n\n"

        report += "---\n\n"
        report += "**免责声明**: 本报告仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。\n"

        return report

    def _generate_recommendations(self, symbol: str, indicators: dict, signal: str) -> dict:
        price = indicators.get("price", {})
        close = price.get("close", 1.0)

        if signal == "buy":
            buy_price = f"¥{(close * 0.98):.4f} - ¥{(close * 0.995):.4f}"
            target_price = f"¥{(close * 1.08):.4f} - ¥{(close * 1.12):.4f}"
            stop_loss = f"¥{(close * 0.95):.4f}"
            reason = "技术面与基本面均支持上涨，建议逢低买入"
        elif signal == "sell":
            buy_price = "—"
            target_price = "—"
            stop_loss = f"¥{(close * 1.05):.4f}"
            reason = "技术面与基本面均承压，建议卖出规避风险"
        else:
            buy_price = f"¥{(close * 0.97):.4f} - ¥{(close * 0.99):.4f}"
            target_price = f"¥{(close * 1.05):.4f} - ¥{(close * 1.10):.4f}"
            stop_loss = f"¥{(close * 0.94):.4f}"
            reason = "信号不明确，建议持有观望，等待更明确的方向"

        return {
            "buy_price": buy_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "reason": reason
        }

    def save_report(self, report: str, filename: str = None) -> str:
        if filename is None:
            filename = f"daily_report_{datetime.now().strftime('%Y%m%d')}.md"

        filepath = os.path.join(self.report_dir, filename)
        os.makedirs(self.report_dir, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        return filepath

    def print_report(self, etf_name: str, symbol: str, signal_result: dict):
        indicators = signal_result["indicators"]
        final_signal = signal_result["final_signal"]
        component_signals = signal_result["component_signals"]

        print(f"\n{'='*60}")
        print(f"  {etf_name} ({symbol}) 分析报告")
        print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        print(f"\n【最终信号】: {self._color_signal(final_signal)}")

        if indicators.get("price"):
            price = indicators["price"]
            print(f"\n【价格信息】")
            print(f"  收盘价: ¥{price['close']:.4f}")
            print(f"  开盘价: ¥{price['open']:.4f}")
            print(f"  最高价: ¥{price['high']:.4f}")
            print(f"  最低价: ¥{price['low']:.4f}")

        if indicators.get("rsi"):
            rsi = indicators["rsi"]
            print(f"\n【RSI】: {rsi['value']:.1f} ({rsi['status']})")

        if indicators.get("macd"):
            macd = indicators["macd"]
            print(f"【MACD】: {macd['macd']:.4f}")
            print(f"【MACD Signal】: {macd['signal']:.4f}")
            print(f"【MACD交叉】: {macd['crossover']}")

        if indicators.get("bollinger"):
            bb = indicators["bollinger"]
            print(f"【布林带%】: {bb['percent']:.1%} ({bb['position']})")

        print(f"\n【信号明细】")
        for signal in component_signals:
            print(f"  - {signal}")

        print(f"\n{'='*60}")

    def _format_signal(self, signal: str) -> str:
        if signal == "buy":
            return "🟢 买入"
        elif signal == "sell":
            return "🔴 卖出"
        elif "buy" in signal.lower():
            return "🟡 持有(倾向买入)"
        elif "sell" in signal.lower():
            return "🟡 持有(倾向卖出)"
        else:
            return "⚪ 持有"

    def _color_signal(self, signal: str) -> str:
        if signal == "buy":
            return "\033[92m🟢 买入\033[0m"
        elif signal == "sell":
            return "\033[91m🔴 卖出\033[0m"
        elif "buy" in signal.lower():
            return "\033[93m🟡 持有(倾向买入)\033[0m"
        elif "sell" in signal.lower():
            return "\033[93m🟡 持有(倾向卖出)\033[0m"
        else:
            return "\033[94m⚪ 持有\033[0m"

    def _format_volume(self, volume: int) -> str:
        if volume >= 100000000:
            return f"{volume / 100000000:.2f}亿"
        elif volume >= 10000:
            return f"{volume / 10000:.2f}万"
        else:
            return str(volume)

    def _format_trend(self, trend: str) -> str:
        if trend == "bullish":
            return "🟢 上升趋势"
        elif trend == "bearish":
            return "🔴 下降趋势"
        else:
            return "⚪ 横盘整理"