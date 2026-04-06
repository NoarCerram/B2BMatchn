def generate_hypothesis(matched_repetitive: list, matched_structured: list,
                        matched_output: list, title: str, company: str) -> str:
    parts = []

    if matched_repetitive:
        parts.append(
            f"Ce poste implique des tâches récurrentes : {', '.join(matched_repetitive[:3])}."
        )
    if matched_structured:
        parts.append(
            f"L'environnement de travail repose sur des outils structurés : {', '.join(matched_structured[:3])}."
        )
    if matched_output:
        parts.append(
            f"Des livrables mesurables sont attendus ({', '.join(matched_output[:2])})."
        )

    hypothesis = " ".join(parts)
    hypothesis += (
        f" {company} recrute probablement pour absorber un volume de travail manuel "
        f"qui pourrait être partiellement automatisé."
    )
    return hypothesis


def generate_offer_angle(score: int, matched_repetitive: list, matched_structured: list) -> str:
    if score >= 80:
        return "Proposition : audit de workflow + pilote d'automatisation (reporting, saisie, relances)."
    elif score >= 60:
        return "Proposition : diagnostic rapide pour identifier les tâches à fort ROI d'automatisation."
    else:
        return "Potentiel limité — à évaluer manuellement."
