from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from anthropic import Anthropic
import base64
import json
from app.config import settings
from app.services import credit_service
from datetime import datetime
import jwt

router = APIRouter()
client = Anthropic(api_key=settings.anthropic_api_key)

VISION_PROMPT = """You are a senior Myntra catalog specialist with 10+ years of experience filling the Myntra SKU template. You have catalogued thousands of real Myntra listings. Analyze all provided product images and return ONLY a valid JSON object — no markdown, no backticks, no explanation.

═══════════════════════════════════════
CRITICAL: USE ONLY ALLOWED VALUES
═══════════════════════════════════════

Any value outside these lists will cause the listing to be REJECTED.

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

═══════════════════════════════════════
KEY FIELD RULES (read every rule)
═══════════════════════════════════════

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

materialCareDescription: CRITICAL — use actual garment component names, NOT generic "Top/Bottom":
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

productDetails: 2–4 sentences on silhouette, design, fabric, contents. Return "" if uncertain.

styleNote: 1–2 sentences styling advice. Return "" if not useful.

sizeAndFitDescription: Fit type and sizing notes. Return "" if not determinable.

detectedBrand: Only if brand logo/label clearly visible. Otherwise "".

collectionName: Only if named collection visible. Otherwise "".

═══════════════════════════════════════
OUTPUT: return ONLY this raw JSON
═══════════════════════════════════════

{
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
}

FINAL CHECKS before returning:
□ brandColourRemarks in ALL CAPS
□ ageGroup has gender suffix (Adults-Women / Adults-Men, NOT just "Adults")
□ season is Fall / Spring / Summer / Winter ONLY (NOT "All Season")
□ usage is from the 9 valid options (NOT "Everyday Wear")
□ materialCareDescription uses actual garment names: "Kurta fabric : X || Pajama Fabric : X" (NOT "Top Fabric")
□ stitch = "Ready to Wear" for fully stitched garments (NOT empty, NOT "Machine Stitched")
□ numberOfPockets is a string ("0", "1"...) or ""
□ occasion is a single value
□ sustainable = "Regular" unless eco-label visible
□ packageContains uses "1 - Garment || 1 - Garment" format
□ character = "NA" not "None"
□ addOns = "NA" not "" when there are no add-ons
□ topClosure = "NA" for pull-on kurtas (NOT "None" or "Pull Over")
□ Return ONLY raw JSON — no markdown, no backticks, no explanation"""

def get_user_from_token(token: str):
    """Decode JWT token and extract user info"""
    try:
        # In production, verify the token signature
        # For now, just decode without verification
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/analyse")
async def analyse_product(
    product_name: str = Form(...),
    images: list[UploadFile] = File(...),
    authorization: str = Header(None),
):
    """
    Analyze product images and return product attributes.

    - product_name: Name of the product (required)
    - images: Up to 5 product images (required)
    - Returns: Product analysis with token usage and cost
    """

    # Validate authorization header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized - Missing JWT token")

    # Extract token
    try:
        token = authorization.split(" ")[1]
        user = get_user_from_token(token)
        user_id = user.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid token")

    # Resolve the auth uuid -> canonical users.number and hard-stop unless the
    # user has at least 15,000 credits. This blocks the Claude call entirely
    # when the balance is below the per-analysis minimum.
    user_number = await credit_service.get_user_number(user_id)
    await credit_service.require_positive_balance(user_number, minimum=15_000)

    # Validate images
    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="At least 1 image required")

    if len(images) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed per analysis")

    try:
        # Prepare message content
        message_content = []

        # Add all images
        for image_file in images:
            image_data = await image_file.read()
            image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

            # Determine media type
            media_type = image_file.content_type or "image/jpeg"
            if image_file.filename:
                if image_file.filename.lower().endswith(".png"):
                    media_type = "image/png"
                elif image_file.filename.lower().endswith(".gif"):
                    media_type = "image/gif"
                elif image_file.filename.lower().endswith(".webp"):
                    media_type = "image/webp"

            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_base64
                }
            })

        # Add per-request text (product name) — kept separate from the cached
        # system prompt so the cache prefix stays byte-identical across requests.
        message_content.append({
            "type": "text",
            "text": f"Product: {product_name}"
        })

        # Call Claude API. The large, unchanging VISION_PROMPT goes in `system`
        # with cache_control so it's cached and billed at ~0.1x on repeat calls.
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            system=[{
                "type": "text",
                "text": VISION_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{
                "role": "user",
                "content": message_content
            }]
        )

        # Extract and parse response
        response_text = response.content[0].text.strip()

        # Clean markdown formatting if present
        if response_text.startswith("```"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()

        analysis = json.loads(response_text)

        # Calculate costs
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Pricing: Input $3/1M, Output $15/1M
        input_cost = (input_tokens / 1_000_000) * 1 * settings.usd_to_inr
        output_cost = (output_tokens / 1_000_000) * 5 * settings.usd_to_inr
        total_cost_inr = round(input_cost + output_cost, 2)

        # Log usage -> DB trigger deducts credits and writes the audit row.
        await credit_service.log_usage(
            user_number,
            input_tokens,
            output_tokens,
            catalog_name=product_name,
            model_used="claude-sonnet-4-5",
            status="success",
        )

        # Charge a flat minimum of 12,000 credits per transaction, or the
        # token-based amount (input + output) * 4 if that is higher.
        credits_deducted = max(6000, (input_tokens + output_tokens) * 1)

        return {
            "analysis": analysis,
            "product_name": product_name,
            "images_analyzed": len(images),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_inr": total_cost_inr,
            "cache_read_input_tokens":response.usage.cache_read_input_tokens,
            "credits_deducted": credits_deducted,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        # Preserve intentional errors (e.g. 402 insufficient credits).
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid response format from Claude: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
