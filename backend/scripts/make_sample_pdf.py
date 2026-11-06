"""Generate the bundled sample PDF used for demos and evaluation.

The document describes a *fictional* company ("Ravinala Numerique"). All text was
written for this project and is released under CC0 1.0 (public domain), so the
PDF can be redistributed freely. One topic per page keeps page-level ground
truth unambiguous for retrieval evaluation (see eval/questions.json).

Usage:  python scripts/make_sample_pdf.py   (requires fpdf2, see requirements-dev.txt)
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parents[1] / "samples" / "guide-employe-ravinala.pdf"

PAGES: list[tuple[str, list[str]]] = [
    (
        "Guide de l'employé - Ravinala Numérique",
        [
            "Ravinala Numérique est une société fictive de services numériques créée pour "
            "illustrer ce guide. Elle a été fondée en 2019 à Antananarivo et compte 48 salariés "
            "répartis en trois pôles : développement logiciel, données et intelligence "
            "artificielle, et support client.",
            "Ce guide rassemble les règles internes applicables à tous les salariés, stagiaires "
            "et prestataires. Il est mis à jour chaque année par le service des ressources "
            "humaines. En cas de contradiction avec le contrat de travail, le contrat prévaut.",
            "Licence : texte et document publiés sous CC0 1.0 (domaine public). "
            "Toute ressemblance avec une entreprise existante serait fortuite.",
        ],
    ),
    (
        "1. Horaires et temps de travail",
        [
            "La durée hebdomadaire de travail est de 40 heures, réparties du lundi au vendredi.",
            "Les horaires sont flexibles autour d'une plage fixe obligatoire de 9h30 à 15h30, "
            "pendant laquelle chaque salarié doit être joignable. L'arrivée est possible dès "
            "7h30 et le départ au plus tard à 19h00.",
            "Les heures supplémentaires doivent être validées à l'avance par le manager. Elles "
            "sont récupérées en temps dans un délai de deux mois.",
            "La pause déjeuner dure au minimum 45 minutes et n'est pas comptée comme temps de travail.",
        ],
    ),
    (
        "2. Congés payés",
        [
            "Chaque salarié bénéficie de 30 jours ouvrables de congés payés par an, acquis à "
            "raison de 2,5 jours par mois de travail effectif.",
            "Toute demande de congé doit être déposée au moins 15 jours à l'avance dans le "
            "portail RH interne, appelé Kolo. Le manager répond sous 5 jours ouvrés.",
            "Les congés non pris peuvent être reportés dans la limite de 10 jours, à utiliser "
            "avant le 31 mars de l'année suivante. Au-delà, ils sont perdus.",
            "Les congés exceptionnels (mariage, naissance, décès d'un proche) sont accordés "
            "selon la grille annexée au contrat de travail.",
        ],
    ),
    (
        "3. Télétravail",
        [
            "Le télétravail est ouvert à tous les salariés ayant terminé leur période d'essai, "
            "dans la limite de 3 jours par semaine.",
            "Les jours de télétravail sont déclarés le vendredi pour la semaine suivante dans "
            "le portail Kolo. Le mardi est un jour de présence commun pour toutes les équipes.",
            "Une indemnité forfaitaire de 40 000 Ariary par mois couvre les frais de connexion "
            "et d'électricité des salariés en télétravail régulier.",
            "La connexion au réseau de l'entreprise se fait obligatoirement via le VPN fourni. "
            "L'usage d'un réseau Wi-Fi public sans VPN est interdit.",
        ],
    ),
    (
        "4. Sécurité informatique",
        [
            "Les mots de passe doivent comporter au moins 14 caractères et ne jamais être "
            "réutilisés entre plusieurs services. Un gestionnaire de mots de passe est fourni.",
            "L'authentification multifacteur (MFA) est obligatoire pour la messagerie, le "
            "dépôt de code et les consoles cloud.",
            "L'écran doit être verrouillé dès que le poste est laissé sans surveillance ; un "
            "verrouillage automatique s'applique après 5 minutes d'inactivité.",
            "Tout incident de sécurité (perte de matériel, courriel suspect, fuite de données) "
            "doit être signalé en moins d'une heure à l'adresse securite@ravinala.example.",
        ],
    ),
    (
        "5. Notes de frais",
        [
            "Les notes de frais sont soumises dans le portail Kolo dans un délai de 30 jours "
            "après la dépense, accompagnées d'un justificatif lisible.",
            "Le plafond de remboursement d'un repas d'affaires est de 60 000 Ariary par personne. "
            "Les déplacements en taxi sont remboursés uniquement après 21h00 ou pour un client.",
            "Les notes validées sont remboursées sous 10 jours ouvrés par virement bancaire.",
            "Les dépenses supérieures à 500 000 Ariary nécessitent l'accord préalable du "
            "directeur financier.",
        ],
    ),
    (
        "6. Formation et développement",
        [
            "Chaque salarié dispose d'un budget formation de 1 200 000 Ariary par an.",
            "Les demandes de formation sont présentées au manager lors de l'entretien annuel "
            "ou au fil de l'eau, puis validées par les ressources humaines.",
            "Les certifications cloud et data (par exemple AWS, Azure ou Google Cloud) sont "
            "prises en charge, examen compris, dans la limite de deux tentatives.",
            "Un vendredi après-midi par mois est réservé à la veille technologique et aux "
            "présentations internes, appelées Lightning Talks.",
        ],
    ),
    (
        "7. Intégration des nouveaux arrivants",
        [
            "Chaque nouvel arrivant est accompagné par un parrain ou une marraine pendant ses "
            "trois premiers mois.",
            "Le premier jour, le salarié reçoit son ordinateur portable, son badge d'accès et "
            "ses identifiants. Une session de présentation de l'entreprise a lieu à 10h00.",
            "La période d'essai est de 3 mois, renouvelable une fois après accord écrit des "
            "deux parties.",
            "Un point d'étape formel avec le manager est organisé à la fin du premier mois.",
        ],
    ),
    (
        "8. Santé et sécurité au travail",
        [
            "Une visite médicale auprès du médecin du travail est organisée à l'embauche puis "
            "tous les deux ans.",
            "En cas d'urgence dans les locaux, composer le poste interne 4400, joignable 24 h/24.",
            "En cas d'évacuation, le point de rassemblement est situé sur le parking nord du "
            "bâtiment. Un exercice d'évacuation a lieu deux fois par an.",
            "Une trousse de premiers secours est disponible à chaque étage, près des ascenseurs.",
        ],
    ),
    (
        "9. Données personnelles et outils d'IA générative",
        [
            "Il est interdit de copier des données clients, des données personnelles ou du code "
            "source confidentiel dans un outil d'IA générative non approuvé.",
            "La liste des outils d'IA approuvés est publiée sur l'intranet et revue chaque "
            "trimestre par le comité sécurité.",
            "Les contenus produits par une IA doivent être relus par un humain avant toute "
            "diffusion à un client.",
            "Le délégué à la protection des données (DPO) est joignable à l'adresse "
            "dpo@ravinala.example pour toute question sur les données personnelles.",
        ],
    ),
]


def build(out: Path = OUT) -> Path:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_title("Guide de l'employe - Ravinala Numerique (fictif, CC0)")
    pdf.set_author("ai-knowledge-agent sample")
    for title, paragraphs in PAGES:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 9, title)
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)
        for p in paragraphs:
            pdf.multi_cell(0, 6, p)
            pdf.ln(3)
        pdf.set_auto_page_break(auto=False)
        pdf.set_y(-15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 10, f"Page {pdf.page_no()} - document fictif, CC0", align="C")
        pdf.set_auto_page_break(auto=True, margin=20)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    print(f"Wrote {build()}")
