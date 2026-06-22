-- =====================================================================
--  CATALOG PLANNER — PREPAID CREDIT SYSTEM
--  Single clean migration. Supabase-compatible PostgreSQL.
--
--  ALL foreign keys point to users.number (integer business key),
--  NOT users.id (uuid). users.number is the canonical identifier.
--
--  Run this whole file in the Supabase SQL Editor.
--  It is idempotent for a CLEAN setup: it drops the old credit
--  objects first, then rebuilds everything from scratch.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. PRE-REQUISITE: make sure users.number exists & is unique
--    (FKs require a UNIQUE/PK target). No-ops if already correct.
-- ---------------------------------------------------------------------
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS number integer GENERATED ALWAYS AS IDENTITY;

-- Guarantee uniqueness so it can be a FK target.
CREATE UNIQUE INDEX IF NOT EXISTS users_number_key ON public.users (number);


-- ---------------------------------------------------------------------
-- 1. CLEAN SLATE — drop old / previous credit objects
-- ---------------------------------------------------------------------
DROP VIEW  IF EXISTS public.user_credit_dashboard      CASCADE;
DROP VIEW  IF EXISTS public.admin_business_summary     CASCADE;

DROP TABLE IF EXISTS public.credit_transactions        CASCADE;
DROP TABLE IF EXISTS public.user_usage                 CASCADE;
DROP TABLE IF EXISTS public.admin_recharge_log         CASCADE;
DROP TABLE IF EXISTS public.user_credits               CASCADE;

-- Legacy tables from the first prototype (keyed on auth uuid) — removed.
DROP TABLE IF EXISTS public.usage_log                  CASCADE;

DROP FUNCTION IF EXISTS public.fn_after_recharge()         CASCADE;
DROP FUNCTION IF EXISTS public.fn_after_usage()            CASCADE;
DROP FUNCTION IF EXISTS public.fn_user_create_credits()    CASCADE;
DROP FUNCTION IF EXISTS public.current_user_number()       CASCADE;


-- =====================================================================
-- 2. TABLES
-- =====================================================================

-- 2.1 USER_CREDITS — one row per user, the live balance ledger -------
CREATE TABLE public.user_credits (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_number              integer NOT NULL UNIQUE
                             REFERENCES public.users (number) ON DELETE CASCADE,
  total_credits_purchased  numeric(12,2) DEFAULT 0,
  credits_used             numeric(12,2) DEFAULT 0,
  credits_balance          numeric(12,2) DEFAULT 0,
  last_recharged_at        timestamptz,
  created_at               timestamptz DEFAULT now(),
  updated_at               timestamptz DEFAULT now(),
  CONSTRAINT user_credits_balance_nonneg CHECK (credits_balance >= 0)
);


-- 2.2 ADMIN_RECHARGE_LOG — immutable record of admin top-ups --------
CREATE TABLE public.admin_recharge_log (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_number        integer NOT NULL
                       REFERENCES public.users (number) ON DELETE CASCADE,
  recharge_amount    numeric(12,2) NOT NULL,
  credits_granted    numeric(12,2) NOT NULL,
  payment_reference  text,
  note               text,
  recharged_by       text DEFAULT 'admin',
  created_at         timestamptz DEFAULT now()
);

COMMENT ON TABLE public.admin_recharge_log IS
  'Immutable log of all admin recharges. Do not delete rows.';


-- 2.3 USER_USAGE — every billable action (catalog analyse) ----------
CREATE TABLE public.user_usage (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_number       integer NOT NULL
                      REFERENCES public.users (number) ON DELETE CASCADE,
  type              text NOT NULL CHECK (type IN ('catalog_analyse')),
  input_tokens      integer NOT NULL,
  output_tokens     integer NOT NULL,
  total_tokens      integer GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
  -- credits_deducted is ALWAYS max(6500, input_tokens + output_tokens).
  -- Made a generated column so the rule can never be violated by callers.
  credits_deducted  numeric(12,2)
                      GENERATED ALWAYS AS (GREATEST(6500, (input_tokens + output_tokens))) STORED,
  catalog_id        uuid,
  catalog_name      text,
  model_used        text DEFAULT 'claude-sonnet-4-6',
  status            text DEFAULT 'success'
                      CHECK (status IN ('success', 'failed', 'partial')),
  created_at        timestamptz DEFAULT now()
);


-- 2.4 CREDIT_TRANSACTIONS — append-only audit of every balance move -
CREATE TABLE public.credit_transactions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_number       integer NOT NULL
                      REFERENCES public.users (number) ON DELETE CASCADE,
  transaction_type  text NOT NULL
                      CHECK (transaction_type IN ('recharge','deduction','adjustment','refund')),
  amount            numeric(12,2) NOT NULL,
  balance_before    numeric(12,2) NOT NULL,
  balance_after     numeric(12,2) NOT NULL,
  reference_id      uuid,
  reference_type    text,   -- 'admin_recharge' | 'catalog_analyse' | 'manual_adjustment'
  description       text,
  created_at        timestamptz DEFAULT now()
);


-- =====================================================================
-- 3. INDEXES
-- =====================================================================
CREATE INDEX idx_user_credits_user_number          ON public.user_credits (user_number);

CREATE INDEX idx_recharge_user_number              ON public.admin_recharge_log (user_number);
CREATE INDEX idx_recharge_created_at               ON public.admin_recharge_log (created_at DESC);

CREATE INDEX idx_usage_user_number                 ON public.user_usage (user_number);
CREATE INDEX idx_usage_created_at                  ON public.user_usage (created_at DESC);
CREATE INDEX idx_usage_type                        ON public.user_usage (type);

CREATE INDEX idx_txn_user_number                   ON public.credit_transactions (user_number);
CREATE INDEX idx_txn_created_at                    ON public.credit_transactions (created_at DESC);
CREATE INDEX idx_txn_reference_id                  ON public.credit_transactions (reference_id);


-- =====================================================================
-- 4. AUTO-PROVISION a credits row for every new user
-- =====================================================================
CREATE OR REPLACE FUNCTION public.fn_user_create_credits()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.user_credits (user_number)
  VALUES (NEW.number)
  ON CONFLICT (user_number) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_user_create_credits
  AFTER INSERT ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.fn_user_create_credits();


-- =====================================================================
-- 5. TRIGGER: after a recharge is logged -> grow balance + audit row
-- =====================================================================
CREATE OR REPLACE FUNCTION public.fn_after_recharge()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_before numeric(12,2);
  v_after  numeric(12,2);
BEGIN
  -- Make sure a credits row exists, then capture the pre-balance.
  INSERT INTO public.user_credits (user_number)
  VALUES (NEW.user_number)
  ON CONFLICT (user_number) DO NOTHING;

  SELECT credits_balance INTO v_before
  FROM public.user_credits
  WHERE user_number = NEW.user_number
  FOR UPDATE;

  v_after := v_before + NEW.credits_granted;

  UPDATE public.user_credits
  SET credits_balance         = v_after,
      total_credits_purchased = total_credits_purchased + NEW.credits_granted,
      last_recharged_at       = now(),
      updated_at              = now()
  WHERE user_number = NEW.user_number;

  INSERT INTO public.credit_transactions (
    user_number, transaction_type, amount,
    balance_before, balance_after,
    reference_id, reference_type, description
  ) VALUES (
    NEW.user_number, 'recharge', NEW.credits_granted,
    v_before, v_after,
    NEW.id, 'admin_recharge',
    COALESCE(NEW.note, 'Admin recharge')
  );

  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_after_recharge
  AFTER INSERT ON public.admin_recharge_log
  FOR EACH ROW EXECUTE FUNCTION public.fn_after_recharge();


-- =====================================================================
-- 6. TRIGGER: after usage is logged -> shrink balance + audit row
--    Hard-stops if the user does not have enough credits.
-- =====================================================================
CREATE OR REPLACE FUNCTION public.fn_after_usage()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_before numeric(12,2);
  v_after  numeric(12,2);
BEGIN
  SELECT credits_balance INTO v_before
  FROM public.user_credits
  WHERE user_number = NEW.user_number
  FOR UPDATE;

  IF v_before IS NULL THEN
    RAISE EXCEPTION 'No credit account for user_number %', NEW.user_number
      USING ERRCODE = 'check_violation';
  END IF;

  -- Zero / insufficient balance guard (defense in depth; API checks too).
  IF v_before < NEW.credits_deducted THEN
    RAISE EXCEPTION 'Insufficient credits: balance % < required %',
      v_before, NEW.credits_deducted
      USING ERRCODE = 'check_violation';
  END IF;

  v_after := v_before - NEW.credits_deducted;

  UPDATE public.user_credits
  SET credits_balance = v_after,
      credits_used    = credits_used + NEW.credits_deducted,
      updated_at      = now()
  WHERE user_number = NEW.user_number;

  INSERT INTO public.credit_transactions (
    user_number, transaction_type, amount,
    balance_before, balance_after,
    reference_id, reference_type, description
  ) VALUES (
    NEW.user_number, 'deduction', -NEW.credits_deducted,
    v_before, v_after,
    NEW.id, 'catalog_analyse',
    COALESCE(NEW.catalog_name, NEW.type)
  );

  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_after_usage
  AFTER INSERT ON public.user_usage
  FOR EACH ROW EXECUTE FUNCTION public.fn_after_usage();


-- =====================================================================
-- 7. VIEWS
-- =====================================================================

-- 7.1 admin_business_summary — monthly recharge roll-up (admin only)
CREATE VIEW public.admin_business_summary AS
SELECT
  date_trunc('month', created_at)        AS month,
  count(*)                               AS recharge_count,
  sum(recharge_amount)                   AS total_recharge_amount,
  sum(credits_granted)                   AS total_credits_granted
FROM public.admin_recharge_log
GROUP BY date_trunc('month', created_at)
ORDER BY month DESC;


-- 7.2 user_credit_dashboard — one consolidated row per user.
--     security_invoker=true so the SELECT RLS on user_credits applies,
--     i.e. a logged-in user only sees their own dashboard row.
CREATE VIEW public.user_credit_dashboard
WITH (security_invoker = true) AS
SELECT
  u.number                       AS user_number,
  u.seller_name,
  u.email,
  c.credits_balance,
  c.total_credits_purchased,
  c.credits_used,
  COALESCE(c.last_recharged_at, lr.created_at) AS last_recharged_at
FROM public.users u
JOIN public.user_credits c ON c.user_number = u.number
LEFT JOIN LATERAL (
  SELECT created_at
  FROM public.admin_recharge_log r
  WHERE r.user_number = u.number
  ORDER BY r.created_at DESC
  LIMIT 1
) lr ON true;


-- =====================================================================
-- 8. ROW LEVEL SECURITY
--    - service_role (backend / admin) BYPASSES RLS automatically.
--    - logged-in users may only SELECT their own rows.
--    - NO user INSERT/UPDATE on admin_recharge_log or credit_transactions
--      (no write policies => writes are blocked for non-service roles;
--       rows are produced exclusively by triggers / admin).
-- =====================================================================

-- Maps the current Supabase auth user -> their users.number.
CREATE OR REPLACE FUNCTION public.current_user_number()
RETURNS integer
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT number FROM public.users WHERE auth_id = auth.uid();
$$;

ALTER TABLE public.user_credits        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_recharge_log  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_usage          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

-- SELECT-own policies (one per table) --------------------------------
CREATE POLICY user_credits_select_own ON public.user_credits
  FOR SELECT TO authenticated
  USING (user_number = public.current_user_number());

CREATE POLICY recharge_select_own ON public.admin_recharge_log
  FOR SELECT TO authenticated
  USING (user_number = public.current_user_number());

CREATE POLICY usage_select_own ON public.user_usage
  FOR SELECT TO authenticated
  USING (user_number = public.current_user_number());

CREATE POLICY txn_select_own ON public.credit_transactions
  FOR SELECT TO authenticated
  USING (user_number = public.current_user_number());

-- Note: deliberately NO insert/update/delete policies for authenticated.
-- admin_recharge_log & credit_transactions are trigger/admin-managed only.
-- user_usage & user_credits are written by the backend via service_role,
-- which bypasses RLS.


-- =====================================================================
-- DONE.
-- =====================================================================
