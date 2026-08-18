"""Generate the printable Kitchen Chemistry: Bread family workbook."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "adeline-ui" / "public" / "workbooks" / "kitchen-chemistry-bread.pdf"

FOREST = colors.HexColor("#2F4731")
GOLD = colors.HexColor("#BD6809")
CREAM = colors.HexColor("#FDF6E9")
LEAF = colors.HexColor("#E3ECDD")
INK = colors.HexColor("#303734")
MUTED = colors.HexColor("#68726C")
CORAL = colors.HexColor("#9A3F4A")


class WritingLines(Flowable):
    def __init__(self, count: int = 5, width: float = 6.6 * inch, gap: float = 0.28 * inch):
        super().__init__()
        self.count = count
        self.width = width
        self.gap = gap
        self.height = count * gap

    def draw(self):
        self.canv.setStrokeColor(colors.HexColor("#CFC6B7"))
        self.canv.setLineWidth(0.6)
        for index in range(self.count):
            y = self.height - ((index + 1) * self.gap) + 4
            self.canv.line(0, y, self.width, y)


class FermentationDiagram(Flowable):
    def __init__(self, width: float = 6.6 * inch, height: float = 1.55 * inch):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        boxes = [
            ("Flour sugars", 0.05),
            ("Living yeast", 1.75),
            ("CO2 + ethanol", 3.45),
            ("Expanded dough", 5.15),
        ]
        canvas.setFont("Helvetica-Bold", 9)
        for label, x_inches in boxes:
            x = x_inches * inch
            canvas.setFillColor(LEAF if label != "CO2 + ethanol" else CREAM)
            canvas.setStrokeColor(FOREST)
            canvas.roundRect(x, 0.52 * inch, 1.35 * inch, 0.55 * inch, 8, fill=1)
            canvas.setFillColor(FOREST)
            canvas.drawCentredString(x + 0.675 * inch, 0.75 * inch, label)
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        for x_inches in (1.43, 3.13, 4.83):
            x = x_inches * inch
            canvas.line(x, 0.8 * inch, x + 0.28 * inch, 0.8 * inch)
            canvas.line(x + 0.22 * inch, 0.86 * inch, x + 0.28 * inch, 0.8 * inch)
            canvas.line(x + 0.22 * inch, 0.74 * inch, x + 0.28 * inch, 0.8 * inch)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(self.width / 2, 0.2 * inch, "Matter moves and changes form; the gas is trapped by the gluten network.")


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def checkbox_list(items: list[str], style: ParagraphStyle) -> Table:
    rows = [["[  ]", p(item, style)] for item in items]
    table = Table(rows, colWidths=[0.32 * inch, 6.1 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (0, -1), FOREST),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def section_card(title: str, text: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[p(title, styles["h3"]), p(text, styles["body"]) ]], colWidths=[1.62 * inch, 4.82 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CREAM),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#D9CFBC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    return table


def page_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9CFBC"))
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.68 * inch, 0.35 * inch, "Dear Adeline | Kitchen Chemistry: Bread")
    canvas.drawRightString(7.82 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_workbook(output_path: Path = OUTPUT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stylesheet = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("Title", parent=stylesheet["Title"], fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=FOREST, alignment=TA_CENTER, spaceAfter=16),
        "subtitle": ParagraphStyle("Subtitle", parent=stylesheet["Normal"], fontName="Helvetica", fontSize=12, leading=18, textColor=MUTED, alignment=TA_CENTER),
        "eyebrow": ParagraphStyle("Eyebrow", parent=stylesheet["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=GOLD, alignment=TA_CENTER, tracking=2, spaceAfter=8),
        "h1": ParagraphStyle("H1", parent=stylesheet["Heading1"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=FOREST, spaceAfter=12),
        "h2": ParagraphStyle("H2", parent=stylesheet["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=FOREST, spaceBefore=10, spaceAfter=8),
        "h3": ParagraphStyle("H3", parent=stylesheet["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=FOREST),
        "body": ParagraphStyle("Body", parent=stylesheet["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK, spaceAfter=7),
        "small": ParagraphStyle("Small", parent=stylesheet["BodyText"], fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED),
        "callout": ParagraphStyle("Callout", parent=stylesheet["BodyText"], fontName="Helvetica-Bold", fontSize=11, leading=16, textColor=FOREST, alignment=TA_CENTER),
        "question": ParagraphStyle("Question", parent=stylesheet["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=FOREST, spaceBefore=6, spaceAfter=4),
    }

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.72 * inch,
        title="Kitchen Chemistry: Bread - Family Workbook",
        author="Dear Adeline",
        subject="Family-style bread fermentation investigation",
    )
    story = []

    # Page 1 - cover
    story.extend([
        Spacer(1, 0.55 * inch),
        p("ONE SHARED FAMILY LESSON", styles["eyebrow"]),
        p("Kitchen Chemistry:<br/>Bread", styles["title"]),
        p("A printable investigation of living yeast, fermentation, gas bubbles, gluten structure, ingredient ratios, temperature, and oven transformations.", styles["subtitle"]),
        Spacer(1, 0.35 * inch),
        FermentationDiagram(),
        Spacer(1, 0.25 * inch),
        Table([[p("The family question", styles["h3"]), p("How can something too small to see fill a bowl with bubbles - and why do those bubbles stay?", styles["callout"]) ]], colWidths=[1.5 * inch, 4.9 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LEAF),
            ("BOX", (0, 0), (-1, -1), 1, FOREST),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ])),
        Spacer(1, 0.35 * inch),
        p("Family name: ____________________________________________", styles["body"]),
        p("Date baked: ____________________   Flour used: ____________________", styles["body"]),
        Spacer(1, 0.2 * inch),
        p("Print one workbook for the family. Younger learners can draw and dictate; middle learners can measure and explain; older learners can calculate and model.", styles["small"]),
        PageBreak(),
    ])

    # Page 2 - roles and materials
    story.extend([
        p("1. Gather the family around the bowl", styles["h1"]),
        p("This is one investigation with different ways to contribute. Choose roles by readiness, not by rigid grade boundaries.", styles["body"]),
        section_card("Younger learners", "Touch flour and dough, notice bubbles and smells, draw the before-and-after loaf, and tell the change story aloud.", styles),
        Spacer(1, 8),
        section_card("Middle learners", "Use the scale, mark dough height, compare conditions, make a data table, and explain cause and effect.", styles),
        Spacer(1, 8),
        section_card("Older learners", "Calculate baker's percentages, model anaerobic fermentation, analyze variables, and explain heat-driven changes.", styles),
        p("Materials", styles["h2"]),
        checkbox_list(["500 g flour", "350 g lukewarm water", "10 g salt", "5-7 g yeast", "Mixing bowl and spoon", "Kitchen scale", "Towel or lid", "Loaf pan or baking sheet", "Marker or tape for dough height", "Optional thermometer"], styles["body"]),
        p("Adult safety checkpoint", styles["h2"]),
        p("An adult handles the hot oven, hot pan, and sharp tools. Check allergies before tasting. Lukewarm water should feel comfortable, not hot: excessive heat can kill yeast.", styles["body"]),
        PageBreak(),
    ])

    # Page 3 - recipe math
    story.extend([
        p("2. Measure a proportional system", styles["h1"]),
        p("Bread is not a random pile of ingredients. It is a system of ratios. Flour is the reference amount in baker's percentage.", styles["body"]),
        Table([
            [p("Ingredient", styles["h3"]), p("One loaf", styles["h3"]), p("Baker's %", styles["h3"]), p("Two loaves", styles["h3"])],
            ["Flour", "500 g", "100%", "________ g"],
            ["Water", "350 g", "70%", "________ g"],
            ["Salt", "10 g", "2%", "________ g"],
            ["Yeast", "5-7 g", "1-1.4%", "________ g"],
        ], colWidths=[1.75 * inch, 1.35 * inch, 1.35 * inch, 1.55 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FOREST),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#CFC6B7")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ])),
        p("Hydration calculation", styles["h2"]),
        p("Water mass / flour mass x 100 = hydration percentage", styles["callout"]),
        Spacer(1, 8),
        p("Our calculation: ______________________________________________________________", styles["body"]),
        p("Prediction before mixing", styles["h2"]),
        p("What will change after 60 minutes? Describe expected height, bubbles, smell, and texture.", styles["question"]),
        WritingLines(6),
        p("Fair-test thinking", styles["h2"]),
        p("If you split the dough, choose one variable to change. Keep every other condition as similar as possible.", styles["body"]),
        checkbox_list(["Temperature", "Hydration", "Proofing time", "Flour type", "Kneading method"], styles["body"]),
        PageBreak(),
    ])

    # Page 4 - fermentation
    story.extend([
        p("3. Watch living yeast change the dough", styles["h1"]),
        FermentationDiagram(),
        p("Fermentation in plain language", styles["h2"]),
        p("Baker's yeast is a living fungus. Without enough oxygen, it can obtain energy from sugars through fermentation. Carbon dioxide gas and a small amount of ethanol are produced. Much of the ethanol evaporates during baking; the carbon dioxide inflates the dough.", styles["body"]),
        p("Observation table", styles["h2"]),
        Table([
            [p("Time", styles["h3"]), p("Dough height", styles["h3"]), p("Bubbles / texture", styles["h3"]), p("Smell", styles["h3"])],
            ["Start", "", "", ""],
            ["20 min", "", "", ""],
            ["40 min", "", "", ""],
            ["60 min", "", "", ""],
        ], colWidths=[0.8 * inch, 1.25 * inch, 2.45 * inch, 1.65 * inch], rowHeights=[0.35 * inch, 0.6 * inch, 0.6 * inch, 0.6 * inch, 0.6 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LEAF),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#BFB5A3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ])),
        p("Evidence statement", styles["h2"]),
        p("I think fermentation occurred because I observed...", styles["question"]),
        WritingLines(5),
        PageBreak(),
    ])

    # Page 5 - gluten and temperature
    story.extend([
        p("4. Find the invisible scaffold", styles["h1"]),
        p("Mixing and folding align flour proteins into a stretchy gluten network. Carbon dioxide does not make a loaf tall by itself: the dough also needs a structure that can stretch and hold the gas.", styles["body"]),
        p("Windowpane test", styles["h2"]),
        p("Stretch a small piece of dough gently. Can it become thin enough for light to pass through before tearing? Draw or describe what you notice.", styles["body"]),
        WritingLines(5),
        p("Temperature comparison", styles["h2"]),
        Table([
            [p("Condition", styles["h3"]), p("Starting temp", styles["h3"]), p("Rise after ___ min", styles["h3"]), p("What stayed the same?", styles["h3"])],
            ["Warmer sample", "", "", ""],
            ["Cooler sample", "", "", ""],
        ], colWidths=[1.35 * inch, 1.25 * inch, 1.6 * inch, 2.15 * inch], rowHeights=[0.4 * inch, 0.8 * inch, 0.8 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LEAF),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#BFB5A3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ])),
        p("Cause-and-effect claim", styles["h2"]),
        p("The evidence suggests temperature __________________ yeast activity because ________________________________.", styles["body"]),
        WritingLines(3),
        PageBreak(),
    ])

    # Page 6 - oven
    story.extend([
        p("5. Follow the loaf through the oven", styles["h1"]),
        p("The oven begins a second wave of transformations. Watch for evidence that heat is moving into the dough and changing matter.", styles["body"]),
        checkbox_list([
            "Gas expands and creates oven spring.",
            "Yeast activity stops as temperature rises beyond its survival range.",
            "Starch absorbs water and gelatinizes, helping set the crumb.",
            "Proteins firm and the loaf's structure becomes stable.",
            "Water evaporates from the surface.",
            "Browning reactions create new colors, aromas, and flavors in the crust.",
        ], styles["body"]),
        p("Before and after", styles["h2"]),
        Table([
            [p("Before baking", styles["h3"]), p("After cooling", styles["h3"])],
            ["Shape: __________________________", "Shape: __________________________"],
            ["Surface: ________________________", "Crust: __________________________"],
            ["Inside: __________________________", "Crumb: __________________________"],
            ["Smell: __________________________", "Smell: __________________________"],
        ], colWidths=[3.2 * inch, 3.2 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FOREST),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#CFC6B7")),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ])),
        p("Explain one oven change", styles["h2"]),
        WritingLines(6),
        PageBreak(),
    ])

    # Page 7 - review
    story.extend([
        p("6. Review the concepts together", styles["h1"]),
        p("Circle one answer for each question. Complete the interactive version online to have the registrar verify and seal the portfolio entry.", styles["body"]),
    ])
    review_items = [
        ("1. What is baker's yeast?", "A. A living fungus   B. A nonliving chemical powder   C. A grain"),
        ("2. Which gas expands the dough?", "A. Oxygen   B. Carbon dioxide   C. Nitrogen"),
        ("3. What does the gluten network do?", "A. Traps gas   B. Feeds yeast   C. Produces heat"),
        ("4. Why does warm dough usually rise faster?", "A. Warmth speeds yeast activity   B. Warmth adds gas   C. Warmth makes flour"),
        ("5. What does oven heat do?", "A. Sets structure and browns crust   B. Keeps yeast alive forever   C. Removes gluten"),
        ("6. How do you double a recipe?", "A. Multiply every ingredient by two   B. Double only flour   C. Guess"),
    ]
    for question, options in review_items:
        story.append(KeepTogether([p(question, styles["question"]), p(options, styles["body"]), Spacer(1, 5)]))
    story.extend([
        p("Family explanation", styles["h2"]),
        p("Use the words yeast, sugar, carbon dioxide, gluten, ratio, temperature, and heat to explain how ingredients became bread.", styles["question"]),
        WritingLines(7),
        PageBreak(),
    ])

    # Page 8 - portfolio/rubric
    story.extend([
        p("7. Prepare the portfolio story", styles["h1"]),
        p("The registrar recognizes demonstrated understanding, careful observation, and a real artifact. Clock time is optional metadata; it is not the point of the lesson.", styles["body"]),
        p("Concepts reviewed for credit", styles["h2"]),
        checkbox_list([
            "Creation Science: yeast as a living organism and fermentation as a chemical process",
            "Creation Science: carbon dioxide production, gluten structure, and evidence of change",
            "Creation Science: temperature, heat transfer, starch/protein changes, and browning",
            "Applied Mathematics: mass, ratios, hydration percentage, and proportional scaling",
            "Scientific communication: observation, cause-and-effect explanation, and a next-test prediction",
        ], styles["body"]),
        p("What did your family actually observe?", styles["h2"]),
        WritingLines(4),
        p("What single variable would you change next time, and what do you predict?", styles["h2"]),
        WritingLines(2),
        p("Portfolio evidence", styles["h2"]),
        checkbox_list(["Photo of the finished loaf", "Photo of the crumb", "Observation table", "Calculation or scaled recipe", "One-sentence explanation from each learner"], styles["body"]),
        Spacer(1, 2),
        Table([[p("Finish online", styles["h3"]), p("Open Dear Adeline > Today > Kitchen Chemistry: Bread. Complete the six-question review, add your observations and next test, then select 'Review concepts & create portfolio entry.'", styles["body"]) ]], colWidths=[1.25 * inch, 5.15 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LEAF),
            ("BOX", (0, 0), (-1, -1), 1, FOREST),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])),
    ])

    doc.build(story, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    return output_path


if __name__ == "__main__":
    print(build_workbook())
