from typing import Dict, List, Tuple
from src.utils.config_loader import ConfigLoader


class SignalGenerator:
    """
    信号生成器 + 多维度置信度计算

    置信度构成（0-10分）：
      - 指标一致性 (0-4分)：4个指标方向越一致，分数越高
      - 信号强度   (0-3分)：绝对强度归一化 + 强信号加成
      - 趋势明确度 (0-2分)：MA趋势明确(bullish/bearish)=2，横盘=0.5
      - 数据质量   (0-1分)：数据完整性评分

    置信度等级：
      - 高置信 (≥7.0)：多指标共振，建议参考操作
      - 中置信 (4.0-6.9)：有一定支撑，谨慎参考
      - 低置信 (<4.0)：信号混乱，建议观望
    """
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

    # 置信度等级阈值
    CONFIDENCE_HIGH = 7.0
    CONFIDENCE_MID = 4.0

    def __init__(self):
        self.config = ConfigLoader().config

    def generate_signal(self, indicators: dict, data_quality: int = 100) -> Dict[str, any]:
        signals = []
        signal_strength = 0
        # 记录每个指标的方向：bullish / bearish / neutral
        directions = []
        # 记录是否有强信号（金叉/死叉/超卖/超买/触及布林带极值）
        has_strong_signal = False

        if self.config["trading_rules"]["ma_crossover"]["enabled"]:
            ma_signal, ma_strength, ma_dir = self._evaluate_ma_signal(indicators)
            if ma_signal:
                signals.append(ma_signal)
                signal_strength += ma_strength
                directions.append(ma_dir)

        if self.config["trading_rules"]["macd_signal"]["enabled"]:
            macd_signal, macd_strength, macd_dir = self._evaluate_macd_signal(indicators)
            if macd_signal:
                signals.append(macd_signal)
                signal_strength += macd_strength
                directions.append(macd_dir)
                if macd_strength >= 3:  # 金叉/死叉
                    has_strong_signal = True

        if self.config["trading_rules"]["rsi_signal"]["enabled"]:
            rsi_signal, rsi_strength, rsi_dir = self._evaluate_rsi_signal(indicators)
            if rsi_signal:
                signals.append(rsi_signal)
                signal_strength += rsi_strength
                directions.append(rsi_dir)
                if abs(rsi_strength) >= 2:  # 超卖/超买
                    has_strong_signal = True

        if self.config["trading_rules"]["bollinger_signal"]["enabled"]:
            bb_signal, bb_strength, bb_dir = self._evaluate_bollinger_signal(indicators)
            if bb_signal:
                signals.append(bb_signal)
                signal_strength += bb_strength
                directions.append(bb_dir)
                if abs(bb_strength) >= 2:  # 触及上下轨
                    has_strong_signal = True

        final_signal = self._determine_final_signal(signals, signal_strength)

        # ===== 多维度置信度计算 =====
        confidence, confidence_breakdown = self._calculate_confidence(
            directions, signal_strength, indicators, has_strong_signal, data_quality
        )

        return {
            "final_signal": final_signal,
            "signal_strength": abs(signal_strength),
            "signal_direction": "positive" if signal_strength > 0 else "negative" if signal_strength < 0 else "neutral",
            "component_signals": signals,
            "indicators": indicators,
            "confidence": confidence,
            "confidence_breakdown": confidence_breakdown,
            "confidence_level": self._confidence_level(confidence),
        }

    def _calculate_confidence(
        self, directions: List[str], signal_strength: int,
        indicators: dict, has_strong: bool, data_quality: int
    ) -> Tuple[float, Dict]:
        """
        计算多维度置信度（0-10分）

        维度1：指标一致性 (0-4分)
          - 4个指标同向 = 4分，3个 = 3分，2个 = 2分，1个 = 1分，0个 = 0.5分
          - 中性也算一种"方向"，全中性 = 3分（持有建议本身是明确的）

        维度2：信号强度 (0-3分)
          - abs(signal_strength) / 9 * 2.5（基础分，最高2.5）
          - 有强信号(金叉/死叉/超卖/超买) 额外 +0.5

        维度3：趋势明确度 (0-2分)
          - MA趋势 bullish/bearish = 2分（趋势明确）
          - MA横盘 = 0.5分（无趋势）

        维度4：数据质量 (0-1分)
          - data_quality / 100
        """
        # ---- 维度1：指标一致性 ----
        total = len(directions)
        if total == 0:
            # 无任何信号触发，说明所有指标中性 → "持有"是明确建议
            consistency = 3.0
        else:
            bullish = directions.count("bullish")
            bearish = directions.count("bearish")
            neutral = directions.count("neutral")
            max_dir = max(bullish, bearish, neutral)
            # 同向占比 × 4，但纯中性（neutral主导）上限3分
            if max_dir == neutral and bullish == 0 and bearish == 0:
                consistency = 3.0  # 全中性，持有建议明确
            else:
                ratio = max_dir / total
                consistency = round(ratio * 4.0, 1)

        # ---- 维度2：信号强度 ----
        abs_strength = abs(signal_strength)
        strength_score = round(abs_strength / 9.0 * 2.5, 1)
        if has_strong:
            strength_score = round(strength_score + 0.5, 1)
        strength_score = min(strength_score, 3.0)

        # ---- 维度3：趋势明确度 ----
        ma = indicators.get("ma", {})
        trend = ma.get("trend", "neutral")
        if trend in ("bullish", "bearish"):
            trend_score = 2.0
        else:
            trend_score = 0.5

        # ---- 维度4：数据质量 ----
        quality_score = round(data_quality / 100.0, 1)

        total_confidence = round(
            min(consistency + strength_score + trend_score + quality_score, 10.0), 1
        )

        breakdown = {
            "consistency": consistency,       # 0-4
            "strength": strength_score,       # 0-3
            "trend": trend_score,             # 0-2
            "data_quality": quality_score,    # 0-1
            "total": total_confidence,        # 0-10
            "directions": {
                "bullish": directions.count("bullish") if directions else 0,
                "bearish": directions.count("bearish") if directions else 0,
                "neutral": directions.count("neutral") if directions else 0,
            },
            "has_strong_signal": has_strong,
        }

        return total_confidence, breakdown

    def _confidence_level(self, confidence: float) -> str:
        """置信度等级"""
        if confidence >= self.CONFIDENCE_HIGH:
            return "高"
        elif confidence >= self.CONFIDENCE_MID:
            return "中"
        else:
            return "低"

    def _evaluate_ma_signal(self, indicators: dict) -> Tuple[str, int, str]:
        """返回 (信号文本, 强度, 方向)"""
        if "ma" not in indicators:
            return "", 0, "neutral"

        ma = indicators["ma"]
        trend = ma["trend"]

        if trend == "bullish":
            return "MA趋势向上，建议关注买入机会", 2, "bullish"
        elif trend == "bearish":
            return "MA趋势向下，建议关注卖出机会", -2, "bearish"
        else:
            return "", 0, "neutral"

    def _evaluate_macd_signal(self, indicators: dict) -> Tuple[str, int, str]:
        """返回 (信号文本, 强度, 方向)"""
        if "macd" not in indicators:
            return "", 0, "neutral"

        macd = indicators["macd"]
        crossover = macd["crossover"]
        hist = macd["hist"]
        prev_hist = macd.get("prev_hist", 0)

        if crossover == "golden_cross":
            return "MACD金叉，买入信号", 3, "bullish"
        elif crossover == "death_cross":
            return "MACD死叉，卖出信号", -3, "bearish"
        elif hist > prev_hist and hist > 0:
            return "MACD红柱放大，多头力量增强", 1, "bullish"
        elif hist < prev_hist and hist < 0:
            return "MACD绿柱放大，空头力量增强", -1, "bearish"
        else:
            return "", 0, "neutral"

    def _evaluate_rsi_signal(self, indicators: dict) -> Tuple[str, int, str]:
        """返回 (信号文本, 强度, 方向)"""
        if "rsi" not in indicators:
            return "", 0, "neutral"

        rsi = indicators["rsi"]
        value = rsi["value"]
        status = rsi["status"]

        if status == "oversold":
            return f"RSI({value:.1f})超卖，可能反弹，买入信号", 2, "bullish"
        elif status == "overbought":
            return f"RSI({value:.1f})超买，可能回调，卖出信号", -2, "bearish"
        elif value < 50:
            return f"RSI({value:.1f})偏空", -1, "bearish"
        elif value > 50:
            return f"RSI({value:.1f})偏多", 1, "bullish"
        else:
            return "", 0, "neutral"

    def _evaluate_bollinger_signal(self, indicators: dict) -> Tuple[str, int, str]:
        """返回 (信号文本, 强度, 方向)"""
        if "bollinger" not in indicators:
            return "", 0, "neutral"

        bb = indicators["bollinger"]
        position = bb["position"]
        percent = bb["percent"]

        if position == "below_lower":
            return f"价格触及布林带下轨({percent:.1%})，超卖区域，买入信号", 2, "bullish"
        elif position == "above_upper":
            return f"价格触及布林带上轨({percent:.1%})，超买区域，卖出信号", -2, "bearish"
        elif position == "above_middle":
            return f"价格在布林带中轨上方({percent:.1%})，偏多", 1, "bullish"
        else:
            return f"价格在布林带中轨下方({percent:.1%})，偏空", -1, "bearish"

    def _determine_final_signal(self, signals: List[str], strength: int) -> str:
        if strength >= 4:
            return self.BUY
        elif strength <= -4:
            return self.SELL
        elif strength > 0:
            return f"{self.HOLD} (倾向买入)"
        elif strength < 0:
            return f"{self.HOLD} (倾向卖出)"
        else:
            return self.HOLD
