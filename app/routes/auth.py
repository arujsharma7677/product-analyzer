from fastapi import APIRouter, HTTPException
from supabase import create_client
from app.config import settings
from app.models.user import UserSignup, UserLogin

router = APIRouter()
supabase = create_client(settings.supabase_url, settings.supabase_service_key)

@router.post("/signup")
async def signup(body: UserSignup):
    try:
        # Create user with email + password (no verification needed).
        try:
            res = supabase.auth.sign_up({
                "email": body.email,
                "password": body.password,
            })
        except Exception as signup_err:
            # The auth user may already exist (e.g. a previous signup created
            # the auth.users row but the public.users profile upsert never
            # completed). Prove ownership with the supplied password and then
            # repair the profile, instead of dead-ending on "already registered".
            if "already registered" not in str(signup_err).lower():
                raise
            try:
                res = supabase.auth.sign_in_with_password({
                    "email": body.email,
                    "password": body.password,
                })
            except Exception:
                raise HTTPException(
                    status_code=409,
                    detail="Email already registered. Please login instead.",
                )

        # Prepare seller details with all fields. Include auth_id + email so
        # this works whether or not a DB trigger pre-created the row.
        user_data = {
            "auth_id": str(res.user.id),
            "email": body.email,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "seller_name": body.seller_name,
            "country": body.country,
            "address": body.address,
            "pincode": body.pincode,
            "state": body.state,
            "gst": body.gst,
            "updated_at": "now()",
        }

        # Upsert the public.users row. A plain UPDATE silently no-ops when the
        # trigger-created row is missing, which is how auth users ended up with
        # no profile row. Upserting on auth_id guarantees the row exists.
        result = (
            supabase.table("users")
            .upsert(user_data, on_conflict="auth_id")
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Could not create user profile. Please try again.",
            )

        return {
            "message": "Signup successful! You can now login.",
            "user_id": str(res.user.id),
            "email": body.email,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "seller_name": body.seller_name,
            "country": body.country,
            "address": body.address,
            "pincode": body.pincode,
            "state": body.state,
            "gst": body.gst,
            "success": True
        }
    except HTTPException:
        # Already a clean, intentional HTTP error — don't re-wrap as a 400.
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(body: UserLogin):
    # Step 1: authenticate against Supabase Auth (auth.users).
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Step 2: require an application profile row in public.users. Supabase Auth
    # validates credentials against auth.users only and never looks at our
    # users table, so without this check login succeeds for accounts that have
    # no profile row (e.g. when the signup upsert never ran).
    profile = (
        supabase.table("users")
        .select("*")
        .eq("auth_id", str(res.user.id))
        .execute()
    )
    if not profile.data:
        raise HTTPException(
            status_code=403,
            detail="No user profile found. Please complete signup.",
        )

    user = profile.data[0]
    return {
        "access_token": res.session.access_token,
        "token_type": "bearer",
        "user_id": res.user.id,
        "email": res.user.email,
        "user": user,
    }
