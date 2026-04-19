class DecisionService:
    @staticmethod
    def make_decision(risk_score: float, rule_flags: list[str]) -> str:
        if "high_amount" in rule_flags and risk_score >= 0.8:
            return "decline"
        if risk_score >= 0.55 or len(rule_flags) > 0:
            return "review"
        return "approve"
