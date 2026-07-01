"""
Platform-aware vision prompt builder.

Why this file exists
---------------------
Previously VISION_PROMPT was one giant, hard-coded string that only ever asked
for Myntra fields. Now that /analyse can be called with platforms=["myntra"],
["ajio"], or ["myntra","ajio"], we need the prompt (and therefore the tokens
we pay for and the JSON we ask Claude to produce) to scale with what was
actually requested:

  - myntra only  -> only Myntra vocab + Myntra output schema
  - ajio only    -> only Ajio vocab + Ajio output schema
  - both         -> ONE shared "look at the garment" pass, then two thin
                    mapping layers that translate that single read into each
                    platform's own controlled vocabulary.

The key optimization: Claude is told explicitly to analyse the garment once
and re-use that same read for both platforms, instead of independently
re-inspecting the image twice and duplicating reasoning tokens. Fields whose
meaning is identical across platforms (garment pieces present, gender, sleeve
style, embellishment, etc.) are described once in SHARED_ANALYSIS and then
just re-expressed in each platform's own allowed values -- Claude is told not
to re-derive them from scratch.

Note on scope: the Ajio vocabulary below is sourced from the customer's own
Ajio "Styles" template for the Women -> Ethnic Wear -> Kurta Suit Sets
category (ajio.xlsx). Ajio templates are category-specific (a different
template/sheet per category), unlike Myntra's single universal SKU sheet, so
this Ajio field set is calibrated to ethnic kurta-set-style listings. If you
sell other Ajio categories (e.g. Western Wear tops, footwear, etc.) you'll
need to swap in that category's own dropdown lists the same way -- happy to
generate those blocks too if you share the corresponding Ajio template.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────
# MYNTRA VOCAB (unchanged from the existing, working prompt)
# ─────────────────────────────────────────────────────────────────────────

MYNTRA_VOCAB = """
COLORS (map every shade to closest — "dark blue"→"Navy Blue", "off-white"→"Off White", "ivory"→"Cream"):
Assorted, Beige, Black, Blue, Bronze, Brown, Burgundy, Camel Brown, Champagne, Charcoal, Coffee Brown, Copper, Coral, Cream, Fluorescent Green, Fuchsia, Gold, Green, Grey, Grey Melange, Khaki, Lavender, Lime Green, Magenta, Maroon, Mauve, Metallic, Multi, Mustard, NA, Navy Blue, Nude, Off White, Olive, Orange, Peach, Pink, Purple, Red, Rose, Rose Gold, Rust, Sea Green, Silver, Steel, Tan, Taupe, Teal, Transparent, Turquoise Blue, Violet, White, Yellow

AGE GROUPS (MUST include gender — "Adults" alone is INVALID):
Adults-Men, Adults-Unisex, Adults-Women, Kids-Boys, Kids-Girls, Kids-Unisex

FASHION TYPES:
Core = everyday basics/solids | Fashion = seasonal/trendy/prints/embellishments/festive/ethnic sets | Core M = modern basics | SMU = special collaboration
Values: Core, Core M, Fashion, SMU

USAGE (single value — "Everyday Wear" / "Casual Wear" are INVALID):
Casual, Ethnic, Formal, Home, NA, Party, Smart Casual, Sports, Travel
→ Ethnic wear/kurtas/sarees/lehengas/co-ords = "Ethnic"
→ Party/sequin/occasion wear = "Party"
→ Office/formals = "Formal"
→ Daily western casuals = "Casual"

SEASONS ("All Season" is INVALID — always pick closest):
Spring = festive Indian ethnic (Diwali/Eid/wedding), florals, pastels, light festive fabrics
Summer = cotton/linen, bright colors, beachwear, light everyday fabrics
Fall = layering pieces, earth tones, medium-weight fabrics
Winter = heavy fabrics, woolens, jackets, darker colors
Values: Fall, Spring, Summer, Winter

ARTICLE TYPES (exact Myntra names — "Suit" / "Ethnic Suit" are INVALID):
Kurtas, Kurta Sets, Sarees, Lehengas, Dupattas, Salwar Suits, Ethnic Dresses, Ethnic Tops, Ethnic Bottoms, Blouses, Lehenga Cholis, Kurtis,
Tops, T-Shirts, Shirts, Dresses, Jeans, Trousers, Shorts, Skirts, Jumpsuits, Co-Ords, Sweatshirts, Sweaters, Jackets, Blazers, Coats, Dungarees, Playsuits,
Casual Shirts, Formal Shirts, Polos, Casual Trousers, Formal Trousers, Suits, Kurtas,
Boys T-Shirts, Girls Dresses, Girls T-Shirts, Boys Shorts, Boys Jeans,
Innerwear, Sleepwear, Swimwear, Tracksuits, Tights
→ Kurta + pajama/pant set = "Kurta Sets" | Kurta + palazzo = "Co-Ords" | Single kurta = "Kurtas" | 3-piece salwar = "Salwar Suits"

OCCASIONS (single value): Ethnic, Casual, Formal, Party, Sports, Festive, Beach, Travel, Home, Work, Daily
→ Ethnic coord/kurta sets in ethnic usage → "Ethnic" | Heavy festive pieces → "Party"

SLEEVE LENGTHS: Sleeveless, Short Sleeves, Three-Quarter Sleeves, Long Sleeves, Cap Sleeves, Regular
NECK TYPES: Round Neck, V-Neck, Square Neck, Boat Neck, Sweetheart Neck, Polo Collar, Shirt Collar, Mandarin Collar, Hooded, Cowl Neck, Off Shoulder, Halter Neck, Turtle Neck, Mock Collar
PATTERNS: Solid, Printed, Striped, Checked, Embroidered, Self Design, Woven Design, Colourblocked, Dyed, Geometric, Floral, Abstract, Camouflage, Animal Print, Paisley, Tie & Dye
→ "Embroidered Floral" is NOT valid — use "Embroidered" for kurta, "Floral" for bottom
CLOSURES: Button, Zipper, Snap Button, Hook and Eye, Drawstring, Elasticated, Pull Over, Slip-On, Velcro, None, NA
→ Pull-on palazzo/kurta with no closure = "Slip-On" or "NA" | Elastic waistband = "Elasticated" | Kurta with no buttons = "NA"
HEMLINES: Straight, Curved, High-Low, Asymmetric, Flared, Ruffled, Tiered, Slit, Regular, Cropped, Midi, Maxi, Mini
SLEEVE STYLING: Regular Sleeves, Puff Sleeves, Flared Sleeves, Bell Sleeves, Bishop Sleeves, Raglan Sleeves, Sleeveless
LININGS: Lined, Unlined, NA  →  use "NA" if not determinable
STITCHES: Ready to Wear, Semi-Stitched, Unstitched  →  "Ready to Wear" for ALL fully stitched garments. NEVER leave empty.
WASH CARE: Machine Wash, Hand Wash, Dry Clean Only
→ Embroidered/ethnic sets → "Hand Wash" | Plain cotton casuals → "Machine Wash" | Silk → "Dry Clean Only"
FABRICS: Cotton, Pure Cotton, Cotton Blend, Polyester, Viscose, Linen, Silk, Satin, Chiffon, Georgette, Crepe, Denim, Nylon, Velvet, Wool, Rayon, Spandex, Net, Lycra, Fleece, Knit, Jersey, Organza, Brocade, Art Silk, Chanderi, Khadi, Lace
→ "Pure Cotton" when appears 100% cotton | "Cotton Blend" when mixed fibers
SUSTAINABLE: Regular (default), Sustainable (only if eco/organic/recycled label is visible)
""".strip()

MYNTRA_FIELD_RULES = """
brandColourRemarks: ALL CAPS. Primary color + key design detail.
  ✓ "NAVY BLUE WITH RED EMBELLISHMENT"
  ✓ "CREAM" (solid, no notable detail)
  ✓ "NAVY BLUE KURTA WITH RED EMBROIDERED NECKLINE AND FLORAL PRINTED PAJAMAS WITH RED POM-POM DUPATTA"

ageGroup: Always include gender. Women's → "Adults-Women". Men's → "Adults-Men". Never just "Adults".

productDisplayName: [Brand if known] [Gender] [Color] [Pattern/Detail] [Fabric?] [ArticleType] [with Add-on?]
  ✓ "Khushal K Women Cotton Co-Ords Set"
  ✓ "Women Navy Blue Embroidered Kurta Pajama Set with Dupatta"
  ✗ "Women Blue Embroidered Ethnic Suit" ← wrong article type

listViewName: Shorter version, max ~50 chars.
  ✓ "Navy Blue Embroidered Kurta Pajama Set with Dupatta"

materialCareDescription: CRITICAL — use actual garment component names, NOT generic "Top/Bottom". Max 90 words:
  Kurta + Pajama set:   "Kurta fabric : Cotton Blend || Pajama Fabric : Cotton Blend"
  Kurta + Palazzo:      "Kurta fabric : Cotton || Palazzo Fabric : Cotton"
  Kurta + Salwar:       "Kurta fabric : Cotton || Salwar Fabric : Cotton"
  Choli + Lehenga:      "Choli fabric : Silk || Lehenga Fabric : Net"
  Single Shirt:         "Shirt fabric : Cotton"
  Single Dress:         "Dress fabric : Georgette"
  Single Top:           "Top fabric : Cotton"
  ✗ NEVER use "Top Fabric : Cotton || Bottom Fabric : Cotton" ← this format is WRONG

stitch: "Ready to Wear" for ALL fully stitched garments. NEVER leave empty for stitched garments.

topClosure: "NA" for pull-on kurtas (most ethnic kurtas have no buttons/zipper).
  "Button" only if buttons clearly visible. "Zipper" only if zipper visible.

bottomClosure: "Elasticated" for pajamas/palazzos/salwars with elastic waist.
  "Slip-On" for pull-on trousers with no visible mechanism. "NA" if not determinable.

addOns: What is physically included. "Dupatta" for sets with dupatta. "Belt" if included.
  Use "NA" if no add-ons — NOT empty string "".

character: "NA" unless licensed character (Disney/Marvel) is clearly visible. NOT "None".

lining: "Unlined" for regular kurtas/casual tops. "Lined" for blazers/lehengas.
  "NA" if not determinable.

packageContains: Use "||" separator with "1 - [Garment]" format:
  ✓ "1 - Kurta || 1 - Pajama || 1 - Dupatta"
  ✓ "1 - Kurta || 1 - Palazzo"
  ✓ "1 - Shirt"
  ✗ "1 Kurta, 1 Pajama, 1 Dupatta" ← WRONG format

numberOfItems: Count of pieces as string: "1", "2", "3".

numberOfPockets: String. Kurtas/ethnic sets → "0". Jeans → "4". Shirts → "1" or "2". "" if uncertain.

season: Indian festive ethnic → "Spring". Light cottons → "Summer". Never "All Season".

occasion: Single value only. Ethnic coord sets → "Ethnic". Festive heavy → "Party".

tags: 8–12 comma-separated search keywords. Return "" if not useful.

productDetails: 2–4 sentences on silhouette, design, fabric, contents. Max 90 words. Return "" if uncertain.

styleNote: 1–2 sentences styling advice. Return "" if not useful.

sizeAndFitDescription: Fit type and sizing notes. Max 90 words. Return "" if not determinable.

detectedBrand: Only if brand logo/label clearly visible. Otherwise "".

collectionName: Only if named collection visible. Otherwise "".
""".strip()

MYNTRA_OUTPUT_SCHEMA = """{
  "articleType": "",
  "prominentColour": "",
  "secondProminentColour": "",
  "thirdProminentColour": "",
  "brandColourRemarks": "",
  "topFabric": "",
  "bottomFabric": "",
  "topType": "",
  "bottomType": "",
  "topPattern": "",
  "bottomPattern": "",
  "sleeveLength": "",
  "neck": "",
  "occasion": "",
  "fashionType": "",
  "usage": "",
  "washCare": "",
  "lining": "",
  "numberOfPockets": "",
  "sleeveStyling": "",
  "topHemline": "",
  "bottomHemline": "",
  "addOns": "",
  "stitch": "",
  "character": "",
  "productDetails": "",
  "listViewName": "",
  "materialCareDescription": "",
  "sizeAndFitDescription": "",
  "productDisplayName": "",
  "packageContains": "",
  "numberOfItems": "",
  "tags": "",
  "collectionName": "",
  "ageGroup": "",
  "season": "",
  "detectedBrand": "",
  "sustainable": "",
  "bottomClosure": "",
  "topClosure": "",
  "styleNote": ""
}"""

# Only the highest-frequency mistakes are repeated here. Every other rule is
# already stated once above; repeating it in a checklist just burns tokens.
MYNTRA_FINAL_CHECKS = """
- brandColourRemarks ALL CAPS; ageGroup has gender suffix; season is Fall/Spring/Summer/Winter only.
- materialCareDescription uses real garment names ("Kurta fabric : X || Pajama Fabric : X"), never "Top/Bottom Fabric".
- stitch = "Ready to Wear" for stitched garments. character/addOns/topClosure = "NA" (never "None" or "").
- Every value comes from the allowed lists above; numberOfPockets/numberOfItems are strings.
""".strip()


# ─────────────────────────────────────────────────────────────────────────
# AJIO VOCAB
# Sourced from the customer's Ajio "Styles" template, Women -> Ethnic Wear ->
# Kurta Suit Sets category (ajio.xlsx / sheetForStoringExtraValues). Column
# letters in the comments refer to that template's "Styles" sheet so you can
# wire the JSON straight into the corresponding cells.
# ─────────────────────────────────────────────────────────────────────────

AJIO_VOCAB = """
COLOR FAMILY (col AU, *Color Family — map every shade to closest, e.g. "dark blue"→"Navy", "off-white"→"Off White"):
Aqua, Beige, Black, Blue, Bronze, Brown, Copper, Cream, Gold, Green, Grey, Khaki, Magenta, Maroon, Metallic, Multi, Mustard, Navy, Nude, Olive, Orange, Peach, Pink, Purple, Red, Rust, Silver, Tan, Teal, White, Yellow, Clear, Rose Gold, Fuchsia, Charcoal, Coffee, Grey Melange, Lime, Off White, Turquoise, Coral, Burgundy, Indigo, Ecru, Lavender, Violet, Wine, Mauve, Sea Green, Taupe
→ Note this list is close but NOT identical to Myntra's colour list (e.g. "Navy" not "Navy Blue", "Coffee" not "Coffee Brown", no "Steel"/"Transparent"/"Champagne") — map independently to THIS list, don't just copy the Myntra colour value across.

COLOR SHADE (col AV): Light, Bright, Dark

SECONDARY COLOR (col BB): same list as COLOR FAMILY above. Use "" if the garment is a single solid colour.

FABRIC TYPE (col AY, *Fabric Type — the fibre name):
Cotton, Pure Cotton is not valid here (use "Cotton"), Silk, Polyester, Viscose, Linen, Satin, Chiffon, Georgette, Crepe, Denim, Nylon, Velvet, Wool, Rayon, Net, Lace, Chanderi, Khadi, Organza, Brocade, Art Silk, Banarasi, Chikankari fabrics use "Cotton" or "Silk" as base, Modal, Muslin, Cambric

PATTERN (col AZ, *Pattern):
Solid, Printed → use "Floral"/"Geometric"/"Paisley"/"Ikat"/"Block Print"/"Abstract" as most specific fit, Embellished, Embroidery, Self-design, Colourblock, Checks, Stripes, Tie & Dye, Applique, Lace, Textured
→ Note Ajio splits "Embellished" (stones/sequins/mirror work) from "Embroidery" (thread work) — these are NOT interchangeable, pick whichever is visible.

WASH CARE (col BE, *Wash Care): Machine wash, Hand wash, Dry clean
→ Embroidered/ethnic sets → "Hand wash" | Plain cotton casuals → "Machine wash" | Silk/heavily embellished → "Dry clean"
→ Note the casing/wording differs from Myntra ("Hand wash" not "Hand Wash", "Dry clean" not "Dry Clean Only").

SLEEVE LENGTH (col BV, *Sleeve Length): Sleeveless, Short sleeve, 3/4th sleeve, Elbow-length sleeve, Full-length sleeve, Asymmetrical sleeve
→ Note wording differs from Myntra ("Short sleeve" not "Short Sleeves", "3/4th sleeve" not "Three-Quarter Sleeves").

LENGTH (col BR, *Length — garment length, use for the kurta/top piece):
Hip, Mid-thigh, Knee length, Calf, Ankle length, Floor

SET TYPE (col BU, *Set Type — what pieces are physically included):
Kurta, Bottomwear & Dupatta   (3-piece: kurta + pajama/palazzo/salwar + dupatta)
Kurta & Bottomwear            (2-piece: kurta + pajama/palazzo/salwar, no dupatta)
Kurta & Dupatta               (kurta + dupatta only, no separate bottomwear)
Bottom & Dupatta              (rare — bottomwear + dupatta only, no kurta)
→ For a single standalone kurta/top/dress with no set pieces, use "NA".

BOTTOMWEAR TYPE (col BN, *Bottomwear Type — only relevant if a bottom piece is included):
Churidar, Salwar, Patiala, Palazzo, Sharara, Dhoti Pant, Harem Pants, Jodhpuri, Pants, Skirts
→ Use "NA" if there is no bottomwear piece.

STYLE TYPE (col BX, *Style Type — silhouette of the kurta/top):
Anarkali, A-line, Straight, Flared, Angrakha

LINING (col BY): Full lining, With Slip, No lining, Partial lining
LINING FABRIC (col BZ, only if lining is not "No lining"): Cotton, Polyester, Viscose, Silk, Voile, Mesh, Cambric, Wool, Poly Knit, Acetate, Cupro
→ Use "NA" for both if lining is not determinable or garment is unlined.

ACCENT (col BF — embellishment/craft technique, "NA" if none visible):
Applique, Bead-work, Crochet, Cut-work, Embellishments, Embroidery, Mirror, Patch-work, Ruffles, Sequins, Stones, Stylised, Tassels, Zari

PRODUCT GROUPS (col I, *Product Groups — occasion/usage vibe, NOT the category):
Casual, Evening, Occasion, Work, Active, Universal
→ Ethnic festive sets → "Occasion" | Everyday cotton kurtas → "Casual" | Office-appropriate → "Work"

MOOD (col AK — style/aesthetic vibe): Bohemian, Bold, Casual, Classic, Cosmopolitan, Dapper, Dramatic, Home, Party, Playful, Preppy, Smart Casual, Sporty, Travel, Vintage, Varsity, Minimalist, Y2K
→ Ethnic embroidered sets → "Classic" or "Bold" depending on print scale | Plain cotton daily wear → "Casual"

FASHION GROUPS (col J, *Fashion Groups): Fashion, Core
→ Same logic as Myntra's fashionType: everyday basics = "Core", trend/festive/embellished = "Fashion".

SEASON CODE (col K, *Season Code): Summer, Spring, Winter, Fall, Core
→ Same seasonal logic as Myntra (festive Indian ethnic = "Spring", cottons = "Summer", woolens/jackets = "Winter", earth-tone layering = "Fall"). "Core" = evergreen basics with no strong season.

CHARACTER (col AC): "NA" unless a licensed character/franchise logo is clearly visible on the garment. Otherwise "NA" (not "None").

MULTI SEGMENT (col AN — audience): Women, Men, Girls, Boys, Infants
MULTI VERTICAL (col AO — vertical within the platform): Ethnic Wear, Western Wear, Fusion Wear, Night & Lounge Wear, Lingerie & Innerwear
→ Derive both from the same gender/category read already used for Myntra's ageGroup/articleType.

PRODUCT NAME (col BS — fixed short template name for kurta-set-style listings):
Kurta Set, Anarkali Kurta Set, A-line Kurta Set, Straight Kurta Set, Flared Kurta Set, Angrakha Kurta Set
→ For non-kurta-set garments (a single top, dress, etc.) just describe it in productTitle instead and set this to "NA".
""".strip()

AJIO_FIELD_RULES = """
fabricDetail: Free text, 1 short phrase describing the fabric composition/finish beyond the base fibre.
  ✓ "Pure Cotton" ✓ "Cotton Silk Blend with Zari Border" ✓ "Georgette with Sequin Work"

bottomwearFabric: Fabric of the bottom piece (pajama/palazzo/salwar) if the set includes one, using the same
  FABRIC TYPE list. Use "NA" if there is no bottomwear piece.

productTitle: A natural, keyword-rich Ajio-style title, similar spirit to Myntra's productDisplayName but do
  not just copy it verbatim — Ajio titles tend to lead with the silhouette/style type.
  ✓ "Women Navy Anarkali Kurta Set with Embroidered Yoke and Dupatta"

componentCount: Count of physical pieces in the package, as a string ("1", "2", "3") — same concept as
  Myntra's numberOfItems. Re-use that same count, don't recount independently.

packageContains: Free text list of what's included, comma-separated (Ajio format differs from Myntra's "||"
  format): ✓ "1 Kurta, 1 Palazzo, 1 Dupatta" ✓ "1 Kurta, 1 Salwar" ✓ "1 Kurta"
""".strip()

AJIO_OUTPUT_SCHEMA = """{
  "colorFamily": "",
  "colorShade": "",
  "secondaryColor": "",
  "fabricType": "",
  "bottomwearFabric": "",
  "fabricDetail": "",
  "pattern": "",
  "washCare": "",
  "sleeveLength": "",
  "length": "",
  "setType": "",
  "bottomwearType": "",
  "styleType": "",
  "lining": "",
  "liningFabric": "",
  "accent": "",
  "productGroups": "",
  "mood": "",
  "fashionGroups": "",
  "seasonCode": "",
  "character": "",
  "multiSegment": "",
  "multiVertical": "",
  "productName": "",
  "productTitle": "",
  "componentCount": "",
  "packageContains": ""
}"""

AJIO_FINAL_CHECKS = """
- Use Ajio's OWN vocab, not Myntra's: colours ("Navy" not "Navy Blue"), washCare ("Hand wash"), sleeveLength ("Short sleeve").
- setType/bottomwearType = "NA" for a single standalone garment; liningFabric = "NA" when unlined; character = "NA".
- componentCount matches the piece count in packageContains.
""".strip()


# ─────────────────────────────────────────────────────────────────────────
# SHARED FRAMING
# One garment "read" instruction, reused as the basis for both platforms so
# Claude doesn't re-inspect the images twice or duplicate reasoning tokens.
# ─────────────────────────────────────────────────────────────────────────

SHARED_INTRO = """You are a senior fashion catalog specialist with 10+ years of experience filling e-commerce SKU templates for Indian fashion marketplaces. Analyze all provided product images ONCE — identify the garment(s), pieces included, gender, fabric, pattern, colours, embellishment, closures, and silhouette — and return ONLY a valid JSON object built from that single read. No markdown, no backticks, no explanation."""

SHARED_REUSE_NOTE = "IMPORTANT: Do the garment analysis once. Every section below asks you to re-express that same read in a different platform's vocabulary — do not re-examine the images independently for each section, and keep facts (piece count, gender, fabric, colours, embellishment) consistent across every section of the output."

MULTI_PLATFORM_REUSE_NOTE = (
    "\nSince both Myntra and Ajio fields are requested together: derive colour, fabric, pattern, sleeve, "
    "gender/age, season, and package-contents ONCE from the images, then map that single read into each "
    "platform's own allowed values below. The underlying facts (e.g. how many pieces are in the set, whether "
    "it's a Women's or Men's garment, what embellishment is visible) must match between the myntra and ajio "
    "sections — only the vocabulary/wording should differ."
)


def _section(header: str, vocab: str, rules: str) -> str:
    return (
        f"### {header}\n\n"
        f"{vocab}\n\n"
        f"FIELD RULES\n{rules}"
    )


def build_vision_prompt(platforms: list[str]) -> str:
    """Build the system prompt for exactly the platforms that were selected.

    platforms: subset of {"myntra", "ajio"} (already validated/normalised by
    parse_platforms in the route). Only the instructions and output-schema
    keys for the requested platforms are included, which keeps the prompt
    (and therefore input tokens) proportional to what was actually asked for.
    """
    want_myntra = "myntra" in platforms
    want_ajio = "ajio" in platforms

    parts = [SHARED_INTRO]

    if want_myntra and want_ajio:
        parts.append(MULTI_PLATFORM_REUSE_NOTE)
    else:
        parts.append(SHARED_REUSE_NOTE)

    if want_myntra:
        parts.append(_section(
            "MYNTRA — use ONLY the allowed values below (anything else is REJECTED)",
            MYNTRA_VOCAB,
            MYNTRA_FIELD_RULES,
        ))

    if want_ajio:
        parts.append(_section(
            "AJIO — use ONLY the allowed values below (anything else is REJECTED)",
            AJIO_VOCAB,
            AJIO_FIELD_RULES,
        ))

    # Assemble the single combined output JSON schema.
    if want_myntra and want_ajio:
        # Myntra fields stay flat at the top level (backward compatible with
        # the existing frontend), Ajio fields nest under "ajio".
        myntra_body = MYNTRA_OUTPUT_SCHEMA.strip()[1:-1].rstrip()  # strip outer { }
        combined_schema = (
            "{\n"
            f"{myntra_body},\n"
            f'  "ajio": {AJIO_OUTPUT_SCHEMA}\n'
            "}"
        )
        final_checks = MYNTRA_FINAL_CHECKS + "\n" + AJIO_FINAL_CHECKS
    elif want_myntra:
        combined_schema = MYNTRA_OUTPUT_SCHEMA
        final_checks = MYNTRA_FINAL_CHECKS
    else:  # ajio only
        combined_schema = f'{{\n  "ajio": {AJIO_OUTPUT_SCHEMA}\n}}'
        final_checks = AJIO_FINAL_CHECKS

    parts.append(
        "### OUTPUT — return ONLY this raw JSON (no markdown, no backticks, no prose)\n\n"
        f"{combined_schema}\n\n"
        f"FINAL CHECKS:\n{final_checks}"
    )

    return "\n\n".join(parts)