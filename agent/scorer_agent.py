#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: scorer_agent.py
@Author: kkonggwu
@Date: 2026/1/31
@Version: 1.0
"""
import logging
from typing import Optional, List

logger = logging.getLogger("scorer_agent")


class ScoringRule:
    """
    评分规则配置
    可通过修改实例属性来自定义不同作业的评分策略
    """
    # 匹配度权重：high 匹配得满分，medium打折
    high_match_weight: float = 1.0
    medium_match_weight: float = 0.7

    # 无效冗余扣分（每个无效冗余扣的分数占比，相对于单个关键点分值）
    invalid_redundant_penalty_rate: float = 0.3

    # 最低分数
    min_score: float = 0.0

    # 置信度相关阈值
    high_confidence_threshold: float = 0.8  # 覆盖值高于此值 -> 高置信度
    low_confidence_threshold: float = 0.4  # 覆盖值低于此值 -> 低置信度


class ScorerAgent:

    def __init__(self, scoring_rule: Optional[ScoringRule] = None):
        """
        初始化评分 Agent
        :param scoring_rule:
        """
        self.scoring_rule = scoring_rule or ScoringRule()
        logger.info(f"ScorerAgent 初始化完成")

    async def score(
            self,
            max_score: float,
            missing_points: List,
            redundant_points: List,
            student_keypoints: List,
            standard_keypoints: List,
            matching_points: Optional[List] = None,
            strict_mode: bool = False,
            previous_scores: Optional[List[float]] = None
    ) -> dict:
        """
        主要的评分方法，供 CoordinatorAgent 调用
        :param max_score:
        :param missing_points:
        :param redundant_points:
        :param student_keypoints:
        :param standard_keypoints:
        :param matching_points:
        :param strict_mode:
        :param previous_scores:
        :return:
        """
        logger.info(f"开始评分: 满分={max_score}，标准关键点共有 {len(standard_keypoints)} 个")

        try:
            total_standard = len(standard_keypoints)

            if total_standard <= 0:
                logger.warning("标准关键点为空，暂时给满分")
                return self._build_result(max_score, max_score, 1.0, {})

            # 1. 基于关键点匹配计算基础评分
            base_score, match_details = self._calculate_base_score(
                max_score=max_score,
                total_standard=total_standard,
                matching_points=matching_points,
                missing_points=missing_points
            )

            # 2. 计算冗余扣分
            redundant_penalty, redundant_details = self._calculate_redundant_penalty(
                redundant_points=redundant_points,
                point_value=max_score / total_standard
            )

            # 3. 计算最终分数
            final_score = max(self.scoring_rule.min_score, base_score - redundant_penalty)
            final_score = round(min(final_score, max_score), 2)

            # 4. 计算置信度
            confidence = self._calculate_confidence(
                total_standard=total_standard,
                matching_points=matching_points,
                missing_points=missing_points,
                student_keypoints=student_keypoints
            )

            # 5. 对于严格模式下的调整
            if strict_mode and previous_scores:
                final_score, confidence = self._apply_strict_mode(
                    score=final_score,
                    confidence=confidence,
                    previous_scores=previous_scores
                )

            # 6. 组装评分细节
            details = self._build_scoring_details(
                base_score=base_score,
                redundant_penalty=redundant_penalty,
                final_score=final_score,
                max_score=max_score,
                confidence=confidence,
                total_standard=total_standard,
                match_details=match_details,
                redundant_details=redundant_details,
                missing_points=missing_points
            )

            logger.info(f"评分完成：{final_score} / {max_score} ，置信度为={confidence:.2f}")
            return self._build_result(final_score, max_score, confidence, details)

        except Exception as e:
            logger.error(f"评分失败")
            raise

    def _calculate_base_score(
            self,
            max_score: float,
            total_standard: int,
            matching_points: List,
            missing_points: List
    ) -> tuple:
        """
        基于关键点匹配计算基础得分
        :param max_score:
        :param total_standard:
        :param matching_points:
        :param missing_points:
        :return:
        """
        point_value = max_score / total_standard
        earned_score = 0.0
        match_details = {"high": 0, "medium": 0, "total_earned": 0.0}

        if matching_points:
            for matching_point in matching_points:
                degree = matching_point.get("match_degree", "medium") if isinstance(matching_point, dict) else "medium"
                if degree == "high":
                    # 较好匹配程度
                    earned_score += point_value * self.scoring_rule.high_match_weight
                    match_details["high"] += 1
                else:
                    # 中等匹配度
                    earned_score += point_value * self.scoring_rule.medium_match_weight
                    match_details["medium"] += 1
        else:
            # 如果没有 matching_point 数据，则使用 missing 进行反推
            matched_count = total_standard - len(missing_points)
            earned_score += matched_count * point_value
            match_details["high"] = matched_count

        match_details["total_earned"] = round(earned_score, 2)
        return round(earned_score, 2), match_details

    def _calculate_redundant_penalty(
            self,
            redundant_points: List,
            point_value: float
    ) -> tuple:
        """
        计算冗余的部分

        只有 is_valid = False 才扣分，有效冗余不会扣分
        :param redundant_points:
        :param point_value:
        :return:
        """
        penalty = 0.0
        invalid_count = 0
        valid_count = 0

        for redundant_point in redundant_points:
            if not redundant_point.get("is_valid", True):
                # 无效冗余点
                penalty += point_value * self.scoring_rule.invalid_redundant_penalty_rate
                invalid_count += 1
            else:
                valid_count += 1

        details = {
            "invalid_count": invalid_count,
            "valid_count": valid_count,
            "total_penalty": round(penalty, 2)
        }

        return round(penalty, 2), details

    def _calculate_confidence(
            self,
            total_standard: int,
            matching_points: Optional[List],
            missing_points: List,
            student_keypoints: List
    ) -> float:
        """
        计算评分置信度 （0-1之间）

        置信度受到一下几个因素影响：
        1， 覆盖率：覆盖率越极端（越高或越低） -> 置信度越高
        2. 匹配质量：high 匹配多 -> 置信度高
        3. 学生关键点数量：太少可能分析不充分 -> 置信度低
        :param total_standard:
        :param matching_points:
        :param missing_points:
        :param student_keypoints:
        :return:
        """
        if total_standard == 0:
            return 1.0

        # 1. 覆盖率
        match_count = len(matching_points) if matching_points else (total_standard - len(missing_points))
        coverage_rate = match_count / total_standard

        # 覆盖率越极端（接近 0 或 1），越确定
        # 覆盖率在 0.4-0.6 之间最不确定
        if (coverage_rate >= self.scoring_rule.high_confidence_threshold or
                coverage_rate <= (1 - self.scoring_rule.high_confidence_threshold)):
            coverage_confidence = 0.9
        elif coverage_rate <= self.scoring_rule.low_confidence_threshold or coverage_rate >= (
                1 - self.scoring_rule.low_confidence_threshold):
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.5

        # 2：匹配质量
        quality_confidence = 0.7  # 默认
        if matching_points:
            high_count = sum(
                1 for matching_point in matching_points if
                isinstance(matching_point, dict) and matching_point.get("match_degree") == "high")
            if len(matching_points) > 0:
                high_ratio = high_count / len(matching_points)
                quality_confidence = 0.6 + 0.4 * high_ratio  # high 匹配占比越高，置信度越高
        # 3：学生关键点数量
        student_count_confidence = min(len(student_keypoints) / 3, 1.0)  # 至少 3 个关键点才算充分
        # 综合置信度（加权平均）
        confidence = (
                coverage_confidence * 0.5 +
                quality_confidence * 0.3 +
                student_count_confidence * 0.2
        )
        return round(min(max(confidence, 0.0), 1.0), 2)

    def _apply_strict_mode(
            self,
            score: float,
            confidence: float,
            previous_scores: List[float]
    ) -> tuple:
        """
        严格模式调整（重评场景）
        如果多次评分波动大，取加权平均以稳定结果
        :param score:
        :param confidence:
        :param previous_scores:
        :return:
        """
        if not previous_scores:
            return score, confidence

        # 将当前分数和历史分数一起计算加权平均
        # 越新的分数权重越大
        all_scores = previous_scores + [score]
        weights = [i + 1 for i in range(len(all_scores))]  # [1, 2, 3, ...]
        total_weight = sum(weights)

        weighted_score = sum(s * w for s, w in zip(all_scores, weights)) / total_weight
        adjusted_score = round(weighted_score, 2)

        # 检查波动
        score_range = max(all_scores) - min(all_scores)
        if score_range > 15:
            # 波动大，置信度降低
            adjusted_confidence = max(confidence - 0.2, 0.3)
            logger.warning(f"重评分数波动较大({score_range:.1f})，置信度下调至 {adjusted_confidence}")
        else:
            # 波动小，置信度提升
            adjusted_confidence = min(confidence + 0.1, 0.95)

        logger.info(f"严格模式调整：{score} → {adjusted_score}，置信度={adjusted_confidence}")
        return adjusted_score, adjusted_confidence

    def _build_scoring_details(
            self,
            base_score: float,
            redundant_penalty: float,
            final_score: float,
            max_score: float,
            confidence: float,
            total_standard: int,
            match_details: dict,
            redundant_details: dict,
            missing_points: List
    ) -> dict:
        """组装详细的评分明细"""
        percentage = (final_score / max_score * 100) if max_score > 0 else 0

        return {
            "scoring_breakdown": {
                "base_score": base_score,
                "redundant_penalty": redundant_penalty,
                "final_score": final_score,
                "max_score": max_score,
                "percentage": round(percentage, 1)
            },
            "keypoint_analysis": {
                "total_standard": total_standard,
                "high_match": match_details.get("high", 0),
                "medium_match": match_details.get("medium", 0),
                "missing_count": len(missing_points),
                "point_value": round(max_score / total_standard, 2) if total_standard > 0 else 0
            },
            "redundant_analysis": redundant_details,
            "grade_level": self._get_grade_level(final_score, max_score)
        }

    @staticmethod
    def _build_result(score: float, max_score: float, confidence: float, details: dict) -> dict:
        """组装标准返回格式"""
        return {
            "score": score,
            "max_score": max_score,
            "confidence": confidence,
            "details": details,
        }

    @staticmethod
    def _get_grade_level(score: float, max_score: float) -> str:
        """根据得分率返回等级"""
        percentage = (score / max_score * 100) if max_score > 0 else 0
        if percentage >= 90:
            return "优秀"
        elif percentage >= 80:
            return "良好"
        elif percentage >= 60:
            return "及格"
        else:
            return "不及格"