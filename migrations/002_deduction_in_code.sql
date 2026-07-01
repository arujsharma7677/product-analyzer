-- 002_deduction_in_code.sql
--
-- Move ALL credit balance math OUT of the database and into application code.
--
-- Previously two triggers mutated user_credits:
--   * fn_after_usage()    — on user_usage insert: checked balance, deducted
--     credits_deducted (a GENERATED column), wrote a credit_transactions row.
--   * fn_after_recharge() — on admin_recharge_log insert: grew the balance and
--     total_credits_purchased, wrote a credit_transactions row.
--
-- Now the application service (app/services/credit_service.py) owns both. Each
-- locks the user_credits row (SELECT ... FOR UPDATE), does the math, writes the
-- audit rows, and — for usage — sets credits_deducted explicitly. So we:
--   1. remove BOTH triggers + their functions (else the math would run twice), and
--   2. turn credits_deducted into a plain column the app writes (default 6500).
--
-- Left in place on purpose:
--   * total_tokens                — generated column, not money-related.
--   * fn_user_create_credits()    — just auto-provisions an empty credits row
--                                    on user creation; no balance math.

-- 1. Stop the DB from auto-deducting on usage insert.
DROP TRIGGER IF EXISTS trg_after_usage ON public.user_usage;
DROP FUNCTION IF EXISTS public.fn_after_usage();

-- 2. Stop the DB from auto-growing the balance on recharge insert.
DROP TRIGGER IF EXISTS trg_after_recharge ON public.admin_recharge_log;
DROP FUNCTION IF EXISTS public.fn_after_recharge();

-- 3. Make credits_deducted a normal, app-writable column (keeps existing data).
ALTER TABLE public.user_usage ALTER COLUMN credits_deducted DROP EXPRESSION;
ALTER TABLE public.user_usage ALTER COLUMN credits_deducted SET DEFAULT 6500;
