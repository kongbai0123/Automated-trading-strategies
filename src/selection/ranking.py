from src.selection.scoring import CandidateScore


class RankingEngine:
    def rank(self, candidates: list[CandidateScore]) -> list[CandidateScore]:
        filtered = [candidate for candidate in candidates if candidate.setup_score > 0]
        return sorted(
            filtered, key=lambda candidate: candidate.setup_score, reverse=True
        )
