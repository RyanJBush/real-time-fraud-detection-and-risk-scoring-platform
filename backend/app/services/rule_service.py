from app.models.transaction import Transaction


class RuleService:
    @staticmethod
    def evaluate(transaction: Transaction, risk_score: float) -> list[str]:
        flags: list[str] = []

        if transaction.amount >= 3000:
            flags.append("high_amount")
        if transaction.channel == "wire":
            flags.append("wire_transfer")
        if risk_score >= 0.8:
            flags.append("high_model_risk")

        return flags
