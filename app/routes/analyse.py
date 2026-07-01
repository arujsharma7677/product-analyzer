from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from anthropic import Anthropic
import base64
import json
from app.config import settings
from app.services import credit_service
from app.services.vision_prompts import build_vision_prompt
from datetime import datetime
import jwt

router = APIRouter()
client = Anthropic(api_key=settings.anthropic_api_key)

# Platforms a request may target. Each selected platform is charged a flat
# CREDITS_PER_PLATFORM (6500) and logged as its own user_usage row.
ALLOWED_PLATFORMS = {"myntra", "ajio"}


def parse_platforms(raw: list[str]) -> list[str]:
    """Normalise the multipart `platforms` field into a validated, de-duped
    lowercase list. Accepts repeated form fields and/or comma-separated values."""
    parsed: list[str] = []
    for value in raw:
        for part in value.split(","):
            name = part.strip().lower()
            if name and name not in parsed:
                parsed.append(name)
    if not parsed:
        raise HTTPException(status_code=400, detail="At least one platform is required")
    invalid = [p for p in parsed if p not in ALLOWED_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform(s): {', '.join(invalid)}. "
            f"Allowed: {', '.join(sorted(ALLOWED_PLATFORMS))}",
        )
    return parsed


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
    platforms: list[str] = Form(...),
    additional_requirements: str = Form(""),
    authorization: str = Header(None),
):
    """
    Analyze product images and return product attributes.

    - product_name: Name of the product (required)
    - images: Up to 5 product images (required)
    - platforms: One or more target platforms (e.g. myntra, ajio). Charged a
      flat 6500 credits each. The Claude prompt/output scales to exactly the
      platforms requested (see app/services/vision_prompts.py) — selecting
      both myntra + ajio still costs ONE Claude call (one set of image
      tokens), not two, since the same garment read is reused for both
      platforms' output sections.
    - additional_requirements: Optional free-text instructions from the user
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

    # Validate the selected platforms up front (6500 charged per platform).
    selected_platforms = parse_platforms(platforms)
    required_credits = len(selected_platforms) * credit_service.CREDITS_PER_PLATFORM

    # Resolve the auth uuid -> canonical users.number and hard-stop unless the
    # user can cover every selected platform. This blocks the Claude call
    # entirely when the balance is below the total required for the request.
    user_number = await credit_service.get_user_number(user_id)
    await credit_service.require_positive_balance(user_number, minimum=required_credits)

    # Validate images
    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="At least 1 image required")

    try:
        # Prepare message content
        message_content = []

        # Accept any number of uploads, but only send the first 3 to Claude
        for image_file in images[:3]:
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
        # system prompt so the cache prefix stays byte-identical across
        # requests that select the same platform(s).
        text = f"Product: {product_name}"
        if additional_requirements.strip():
            text += (
                "\n\nADDITIONAL REQUIREMENT (from the user): "
                f"{additional_requirements.strip()}\n"
                "Treat the above as an extra requirement that MUST be analysed and "
                "properly articulated into the output. Incorporate it into the "
                "`tags` field (add relevant search keywords reflecting it) and into "
                "the `productDetails` field (describe how it applies to this product). "
                "Do not let it override any of the allowed-value rules above."
            )
        message_content.append({
            "type": "text",
            "text": text
        })

        # Build a prompt scoped to exactly the platforms that were selected.
        # This keeps the (cached) system prompt proportional to what's being
        # asked for: myntra-only and ajio-only requests don't pay for the
        # other platform's vocabulary, while a combined request still makes
        # a single Claude call that reuses one garment read for both.
        vision_prompt = build_vision_prompt(selected_platforms)

        # Call Claude API. The large, unchanging per-platform-combo prompt
        # goes in `system` with cache_control so it's cached and billed at
        # ~0.1x on repeat calls with the same platform selection.
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000 if len(selected_platforms) == 1 else 3200,
            system=[{
                "type": "text",
                "text": vision_prompt,
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

        # Calculate costs.
        # Haiku 4.5 pricing: input $1 / 1M, output $5 / 1M.
        # Cached input is billed at ~0.1x, so split input tokens into
        # cache-read vs fresh and price them separately — otherwise the
        # reported INR overstates the true cost on every cache hit (which is
        # most requests, since the per-platform prompt is cached).
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        fresh_input = max(input_tokens - cache_read, 0)

        input_cost = (
            (fresh_input / 1_000_000) * 1
            + (cache_read / 1_000_000) * 0.1
        ) * settings.usd_to_inr
        output_cost = (output_tokens / 1_000_000) * 5 * settings.usd_to_inr
        total_cost_inr = round(input_cost + output_cost, 2)

        # One 6500 charge per selected platform, all in a single atomic batch.
        # The DB trigger deducts each row and writes its audit line; the real
        # amounts are read back so the response can't drift from what was
        # actually charged.
        credits_deducted, credits_breakdown = await credit_service.log_usage_batch(
            user_number,
            selected_platforms,
            input_tokens,
            output_tokens,
            catalog_name=product_name,
            model_used="claude-haiku-4-5",
            status="success",
        )

        return {
            "analysis": analysis,
            "product_name": product_name,
            "platforms": selected_platforms,
            "images_analyzed": len(images),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_inr": total_cost_inr,
            "cache_read_input_tokens": cache_read,
            "credits_deducted": credits_deducted,
            "credits_breakdown": credits_breakdown,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        # Preserve intentional errors (e.g. 402 insufficient credits).
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid response format from Claude: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")