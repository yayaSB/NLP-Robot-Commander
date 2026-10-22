#!/usr/bin/env python3
"""Génère le rapport final PDF à partir des résultats réellement mesurés."""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "rapport_final_nlp_robot_commander.pdf"
NAVY = colors.HexColor("#002060")
ORANGE = colors.HexColor("#ED7D31")
GREEN = colors.HexColor("#385723")
RED = colors.HexColor("#C00000")
PALE = colors.HexColor("#F0F3F8")
INK = colors.HexColor("#19232E")
MUTED = colors.HexColor("#606B78")


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("ProjectSans", regular))
        pdfmetrics.registerFont(TTFont("ProjectSans-Bold", bold))
        return "ProjectSans", "ProjectSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            fontName=FONT_BOLD,
            fontSize=34,
            leading=40,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            "CoverSub",
            fontName=FONT,
            fontSize=17,
            leading=23,
            textColor=INK,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "H1Project",
            fontName=FONT_BOLD,
            fontSize=21,
            leading=25,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "H2Project",
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyProject",
            fontName=FONT,
            fontSize=10.2,
            leading=15,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "BulletProject",
            parent=styles["BodyProject"],
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=2,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            "Callout",
            fontName=FONT_BOLD,
            fontSize=11,
            leading=15,
            textColor=RED,
            borderColor=colors.HexColor("#E8B4B4"),
            borderWidth=0.8,
            borderPadding=8,
            backColor=colors.HexColor("#FFF6F6"),
            spaceBefore=6,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "CaptionProject",
            fontName=FONT,
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=9,
        )
    )
    return styles


STYLES = make_styles()


def p(text: str, style: str = "BodyProject") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", STYLES["BulletProject"])


def project_table(data, widths=None, font_size=9.2, align="LEFT") -> Table:
    header_style = ParagraphStyle(
        f"TableHeader{font_size}",
        fontName=FONT_BOLD,
        fontSize=font_size,
        leading=font_size + 3,
        textColor=colors.white,
    )
    body_style = ParagraphStyle(
        f"TableBody{font_size}",
        fontName=FONT,
        fontSize=font_size,
        leading=font_size + 3,
        textColor=INK,
    )
    converted = []
    for row_index, row in enumerate(data):
        row_style = header_style if row_index == 0 else body_style
        converted.append(
            [
                cell if isinstance(cell, Paragraph) else Paragraph(str(cell), row_style)
                for cell in row
            ]
        )
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign=align)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def later_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8DEE9"))
    canvas.line(1.6 * cm, A4[1] - 1.35 * cm, A4[0] - 1.6 * cm, A4[1] - 1.35 * cm)
    canvas.setFont(FONT_BOLD, 8.5)
    canvas.setFillColor(NAVY)
    canvas.drawString(1.6 * cm, A4[1] - 1.05 * cm, "NLP Robot Commander — HESTIM")
    canvas.setFont(FONT, 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(A4[0] - 1.6 * cm, 0.9 * cm, f"Page {doc.page}")
    canvas.restoreState()


def first_page(canvas, _doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, 0.35 * cm, A4[1], fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.rect(0.35 * cm, 0, 0.08 * cm, A4[1], fill=1, stroke=0)
    canvas.restoreState()


def build_story():
    val = load_json("artifacts/training_3intents/validation_metrics.json")
    test = load_json("artifacts/test_campaign_3intents/metrics.json")
    safety = load_json("artifacts/safety_campaign_transformers/metrics.json")
    audit = load_json("artifacts/dataset_audit.json")
    story = []

    logo = ROOT / "docs" / "assets" / "hestim_logo.png"
    if logo.exists():
        story.extend([Image(str(logo), width=7.2 * cm, height=2.0 * cm), Spacer(1, 2.1 * cm)])
    story.extend(
        [
            p("NLP Robot Commander", "CoverTitle"),
            p("Commande sûre d’un robot mobile par langage naturel en français", "CoverSub"),
            Spacer(1, 1.3 * cm),
            project_table(
                [
                    ["Document", "Rapport technique final"],
                    ["Établissement", "HESTIM Engineering & Business School"],
                    ["Version", "Auditée — 22 octobre 2026"],
                    ["Taxonomie", "navigate · stop · report"],
                ],
                widths=[4.2 * cm, 10.5 * cm],
            ),
            Spacer(1, 2.5 * cm),
            p(
                "Résultats locaux : 97,22 % sur validation, 100 % sur le test indépendant "
                "et 15/15 scénarios de sûreté conformes.",
                "CoverSub",
            ),
            p(
                "La validation Gazebo/Nav2 est explicitement séparée et reste à exécuter sous Ubuntu 22.04.",
                "Callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("Résumé exécutif", "H1Project"),
            p(
                "Le projet transforme une phrase française en une décision robotique contrôlée. "
                "Le domaine est volontairement fermé à trois intentions : rejoindre un waypoint connu, "
                "interrompre une navigation et rapporter la pose actuelle. Classification, extraction, "
                "validation, routage et interfaces ROS 2 sont séparés afin que chaque erreur soit localisable."
            ),
            p(
                "L’audit a supprimé l’ancienne taxonomie incohérente, reconstruit les jeux de données, "
                "durci le chargement du modèle, ajouté des garde-fous pour les négations et commandes composées, "
                "et remplacé la fausse confirmation d’arrêt par une machine d’état suivant réellement Nav2."
            ),
            project_table(
                [
                    ["Indicateur", "Résultat mesuré", "Portée"],
                    ["Validation", "97,22 % accuracy / F1 macro", "36 phrases"],
                    ["Test indépendant", "100 % accuracy / F1 macro", "45 phrases"],
                    ["Sûreté", "15/15 décisions conformes", "cas adversariaux"],
                    ["Tests logiciels", "34 réussis", "sans ROS 2 réel"],
                ],
                widths=[4.0 * cm, 5.2 * cm, 5.5 * cm],
            ),
            Spacer(1, 0.3 * cm),
            p(
                "Aucune conclusion de réussite robotique n’est tirée de ces chiffres. Les waypoints, Gazebo, "
                "Nav2, TF et l’immobilisation réelle doivent être vérifiés sur la plateforme cible.",
                "Callout",
            ),
            p("Table des matières", "H2Project"),
            p(
                "1. Périmètre et audit · 2. Architecture · 3. Données · 4. Entraînement · "
                "5. Résultats · 6. Sûreté · 7. ROS 2/Nav2 · 8. Tests · 9. Limites et actions manuelles · 10. Conclusion"
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("1. Périmètre et conclusions de l’audit", "H1Project"),
            p("Objectifs", "H2Project"),
            bullet("Reconnaître exactement navigate, stop et report."),
            bullet("Autoriser une navigation uniquement vers un waypoint configuré."),
            bullet("Donner la priorité à un arrêt explicite non nié."),
            bullet("Ne jamais inventer une position ou confirmer trop tôt une annulation."),
            p("Constats initiaux", "H2Project"),
            bullet("Les données, résultats et documents utilisaient une taxonomie devenue obsolète."),
            bullet("Les 14 tests initiaux ne couvraient ni la machine d’état Nav2 ni les refus avancés."),
            bullet("Le repli lexical silencieux pouvait masquer un checkpoint absent ou corrompu."),
            bullet("La pose TF était publiée sans contrôle de fraîcheur."),
            bullet("Le chemin relatif du modèle dépendait du répertoire courant."),
            p("Corrections", "H2Project"),
            p(
                "La taxonomie a été figée dans le code et le checkpoint, les métriques historiques ont été "
                "retirées, le corpus a été reconstruit, le chemin du modèle est explicite et le repli lexical "
                "est désactivé par défaut. Les erreurs d’entrée et de modèle sont désormais visibles."
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("2. Architecture logicielle", "H1Project"),
            project_table(
                [
                    ["Composant", "Rôle", "Invariant"],
                    ["CommandProcessor", "Validation et politique de sûreté", "Aucune action avant acceptation"],
                    ["IntentClassifier", "Inférence DistilBERT", "Trois labels exacts"],
                    ["EntityExtractor", "Destination et YAML", "Une destination unique et finie"],
                    ["CommandRouter", "Dispatch testable", "Une seule opération robot"],
                    ["NavigationState", "Suivi du but et de l’arrêt", "Demande ≠ confirmation"],
                    ["NlpCommanderNode", "ROS 2, Nav2 et TF", "Statuts JSON traçables"],
                ],
                widths=[3.8 * cm, 5.7 * cm, 5.2 * cm],
            ),
            Spacer(1, 0.4 * cm),
            p("Flux", "H2Project"),
            p(
                "Texte → contrôles déterministes → DistilBERT → contrôle confiance/ambiguïté → extraction "
                "du waypoint → routeur → ActionClient Nav2 ou lecture TF → statut JSON."
            ),
            p("Interfaces ROS 2", "H2Project"),
            project_table(
                [
                    ["Nom", "Type", "Usage"],
                    ["/nlp_command", "std_msgs/String", "entrée texte"],
                    ["/nlp_commander/status", "std_msgs/String JSON", "événements"],
                    ["/navigate_to_pose", "nav2_msgs/NavigateToPose", "but et résultat"],
                    ["map → base_link", "TF2", "pose réelle"],
                    ["/cmd_vel", "geometry_msgs/Twist", "optionnel, désactivé"],
                ],
                widths=[4.7 * cm, 5.0 * cm, 5.0 * cm],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("3. Données et indépendance des jeux", "H1Project"),
            project_table(
                [
                    ["Ensemble", "Taille", "Par intention", "Usage"],
                    ["Entraînement", "126", "42", "ajustement des poids"],
                    ["Validation", "36", "12", "sélection du checkpoint"],
                    ["Test indépendant", "45", "15", "mesure finale"],
                    ["Sûreté", "15", "mixte", "acceptation/refus"],
                ],
                widths=[4.0 * cm, 2.2 * cm, 3.0 * cm, 5.5 * cm],
            ),
            Spacer(1, 0.4 * cm),
            p(
                f"L’audit automatique rapporte {audit['training_rows']} phrases de développement, "
                f"{audit['test_rows']} phrases de test, aucun doublon exact et aucun quasi-doublon "
                f"inter-splits au seuil {audit['similarity_threshold']:.2f}."
            ),
            p("Diversité couverte", "H2Project"),
            bullet("Impératifs, questions, politesse, formulations nominales et vocabulaire ROS."),
            bullet("Alias de cuisine, salon, bureau et chargeur."),
            bullet("Phrases longues, courtes, techniques et familières."),
            p("Limite", "H2Project"),
            p(
                "Le corpus reste petit et construit dans un domaine fermé. Le test indépendant est utile, "
                "mais son score ne garantit pas la généralisation à toutes les variantes du français."
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("4. Entraînement et chargement du modèle", "H1Project"),
            project_table(
                [
                    ["Paramètre", "Valeur"],
                    ["Modèle de base", val["model_name"]],
                    ["Époques maximales", val["epochs"]],
                    ["Batch", val["batch_size"]],
                    ["Learning rate", val["learning_rate"]],
                    ["Graine", val["seed"]],
                    ["Critère de sélection", "F1 macro de validation"],
                    ["Longueur maximale", "128 tokens"],
                ],
                widths=[6.0 * cm, 8.7 * cm],
            ),
            Spacer(1, 0.4 * cm),
            p(
                "Les splits sont figés dans le CSV. Le script configure les graines Python, NumPy et Torch. "
                "Le meilleur checkpoint est chargé à la fin de l’entraînement. Seuls les poids sont conservés "
                "dans les checkpoints intermédiaires afin d’éviter plusieurs gigaoctets d’états d’optimiseur."
            ),
            p("Chargement défensif", "H2Project"),
            bullet("Répertoire local obligatoire et lisible."),
            bullet("Tokenizer et poids chargés en mode local pour le runtime robot."),
            bullet("Ensemble des labels strictement égal aux trois intentions attendues."),
            bullet("Erreur explicite en cas de dépendance absente ou checkpoint invalide."),
            p(
                "Le checkpoint local dépasse la limite de taille standard de GitHub. Il est reproductible par "
                "script mais n’est pas inclus dans le dépôt Git classique.",
                "Callout",
            ),
            PageBreak(),
        ]
    )

    val_image = ROOT / "artifacts" / "training_3intents" / "confusion_matrix.png"
    test_image = ROOT / "artifacts" / "test_campaign_3intents" / "confusion_matrix.png"
    story.extend([p("5. Résultats mesurés", "H1Project")])
    story.append(
        project_table(
            [
                ["Jeu", "Accuracy", "F1 macro", "Effectif"],
                ["Validation", f"{val['accuracy']*100:.2f} %", f"{val['classification_report']['macro avg']['f1-score']*100:.2f} %", val["validation_size"]],
                ["Test indépendant", f"{test['accuracy']*100:.2f} %", f"{test['classification_report']['macro avg']['f1-score']*100:.2f} %", test["sample_count"]],
                ["Sûreté", f"{safety['pass_rate']*100:.2f} %", "—", safety["sample_count"]],
            ],
            widths=[4.2 * cm, 3.3 * cm, 3.3 * cm, 3.9 * cm],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    if val_image.exists() and test_image.exists():
        story.append(
            Table(
                [[Image(str(val_image), width=7.0 * cm, height=6.0 * cm), Image(str(test_image), width=7.0 * cm, height=6.0 * cm)]],
                colWidths=[7.35 * cm, 7.35 * cm],
            )
        )
        story.append(p("Matrices de confusion : validation (gauche) et test indépendant (droite).", "CaptionProject"))
    story.extend(
        [
            p(
                "Le test indépendant produit 45 classifications correctes, avec précision, rappel et F1 égaux "
                "à 1,00 pour chaque classe. Les 45 commandes valides sont également acceptées par la politique "
                "finale. Ce résultat doit être rapporté avec son effectif et les limites du domaine fermé."
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("6. Sûreté et modes d’échec", "H1Project"),
            project_table(
                [
                    ["Exemple", "Résultat"],
                    ["Ne va pas dans la cuisine", "NEGATED_COMMAND"],
                    ["Va dans la cuisine pas dans le salon", "MULTIPLE_DESTINATIONS"],
                    ["Va dans la cuisine puis dans le laboratoire", "SEQUENTIAL_COMMAND"],
                    ["Arrête-toi immédiatement", "arrêt prioritaire accepté"],
                    ["Va dans la chambre", "UNKNOWN_DESTINATION"],
                    ["Bonjour robot", "UNKNOWN_INTENT"],
                    ["Commande avec contrôle Unicode", "CONTROL_CHARACTER"],
                ],
                widths=[9.0 * cm, 5.7 * cm],
            ),
            Spacer(1, 0.35 * cm),
            p(
                "Les 15 scénarios adversariaux produisent la décision attendue avec le checkpoint. Un score de "
                "réseau élevé n’est toutefois jamais utilisé seul : les preuves lexicales et les entités doivent "
                "rester compatibles avec l’action."
            ),
            p("Catalogue opérationnel", "H2Project"),
            bullet("LOW_CONFIDENCE et AMBIGUOUS_INTENT : refus sans routage."),
            bullet("navigation_rejected : serveur absent, but refusé ou erreur d’envoi."),
            bullet("stop_unconfirmed : annulation refusée, expirée ou résultat incompatible."),
            bullet("position_unavailable / position_stale : aucune pose présentée comme actuelle."),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("7. Intégration ROS 2, Nav2 et TF", "H1Project"),
            p("Navigation", "H2Project"),
            p(
                "Le nœud attend `/navigate_to_pose` avec timeout, construit une pose dans `map`, envoie le but "
                "asynchrone puis publie séparément demande, acceptation et résultat. Un second but est refusé "
                "tant que la machine d’état n’est pas revenue à idle."
            ),
            p("Arrêt", "H2Project"),
            project_table(
                [
                    ["Étape", "Événement", "Signification"],
                    ["1", "stop_received", "demande reçue"],
                    ["2", "cancellation_requested", "requête envoyée à Nav2"],
                    ["3", "cancellation_accepted", "Nav2 traite la requête"],
                    ["4a", "stop_confirmed", "résultat canceled ou aucun but actif"],
                    ["4b", "stop_unconfirmed", "refus, erreur, timeout ou résultat incompatible"],
                ],
                widths=[1.7 * cm, 5.2 * cm, 7.8 * cm],
            ),
            Spacer(1, 0.3 * cm),
            p(
                "L’envoi optionnel d’une vitesse nulle est désactivé par défaut et ne vaut jamais confirmation. "
                "Il doit être coordonné avec le multiplexeur de vitesse du robot."
            ),
            p("Rapport", "H2Project"),
            p(
                "La transformation `map → base_link` est lue avec timeout. Son timestamp est comparé à "
                "`max_tf_age_sec`. Une transformation nulle, future ou trop ancienne est refusée."
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("8. Tests exécutés et non exécutés", "H1Project"),
            p("Exécutés", "H2Project"),
            bullet("34 tests unitaires réussis."),
            bullet("Compilation Python de scripts, sources et tests réussie."),
            bullet("Audit des datasets : ok, sans fuite détectée au seuil configuré."),
            bullet("Entraînement DistilBERT et sélection du meilleur checkpoint."),
            bullet("Évaluation indépendante 45/45 et sûreté 15/15."),
            bullet("Validation structurelle de la présentation et rendu page par page du PDF."),
            p("Non exécutés", "H2Project"),
            bullet("Construction `colcon` sur Ubuntu 22.04."),
            bullet("Gazebo, RViz2 et lifecycle Nav2."),
            bullet("Navigation réelle vers les quatre waypoints."),
            bullet("Annulation d’un but actif et immobilisation observée."),
            bullet("TF absente, trop ancienne et comparaison de pose avec RViz2."),
            bullet("Entrée microphone dans un environnement bruité."),
            p(
                "Ces éléments figurent dans ACTIONS_MANUELLES.md et checklist_demo.md. Ils ne doivent pas être "
                "présentés comme validés avant collecte des preuves.",
                "Callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("9. Limites, recommandations et remise", "H1Project"),
            p("Limites", "H2Project"),
            bullet("Petit corpus et domaine fermé malgré l’indépendance du test."),
            bullet("Waypoints d’exemple non liés à une carte validée."),
            bullet("Absence de mesure de latence et de calibration probabiliste."),
            bullet("Poids DistilBERT non stockés dans Git."),
            bullet("Audio non évalué dans la campagne actuelle."),
            p("Recommandations", "H2Project"),
            bullet("Exécuter plusieurs graines et publier moyenne et dispersion."),
            bullet("Ajouter un jeu de test collecté auprès d’utilisateurs externes."),
            bullet("Mesurer la latence CPU du robot et la fraîcheur TF en situation réelle."),
            bullet("Archiver les journaux d’action Nav2 avec chaque vidéo de démonstration."),
            bullet("Utiliser Git LFS ou un registre de modèles si les poids doivent être distribués."),
            p("Commandes principales", "H2Project"),
            p(
                "`python -m pytest` · `python scripts/audit_dataset.py` · "
                "`python scripts/train_intent_classifier.py ...` · "
                "`ros2 launch nlp_robot_commander simulation.launch.py model_path:=... map:=...`"
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("10. Conclusion", "H1Project"),
            p(
                "La version auditée atteint l’objectif NLP sur les jeux fournis et renforce les interfaces "
                "robotique critiques. La taxonomie est cohérente, les données sont auditées, le checkpoint est "
                "reproductible, les refus sont explicites et la sémantique de l’arrêt ne confond plus demande "
                "et confirmation."
            ),
            p(
                "Le projet est prêt pour sa dernière phase : recalibrer les waypoints, construire sous ROS 2 "
                "Humble, exécuter la campagne Gazebo/Nav2 et intégrer uniquement les preuves observées."
            ),
            Spacer(1, 1.0 * cm),
            KeepTogether(
                [
                    p("Livrables de référence", "H2Project"),
                    bullet("README.md — reproduction et lancement."),
                    bullet("docs/rapport_final.md — source du présent rapport."),
                    bullet("docs/guide_utilisateur.md — prise en main."),
                    bullet("docs/checklist_demo.md — déroulé de soutenance."),
                    bullet("docs/ACTIONS_MANUELLES.md — validations restantes."),
                    bullet("artifacts/ — métriques, prédictions et matrices."),
                ]
            ),
        ]
    )
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.5 * cm,
        title="Rapport final — NLP Robot Commander",
        author="Projet HESTIM",
        subject="Audit, NLP et intégration ROS 2/Nav2",
    )
    document.build(build_story(), onFirstPage=first_page, onLaterPages=later_page)
    print(OUTPUT)


if __name__ == "__main__":
    main()
