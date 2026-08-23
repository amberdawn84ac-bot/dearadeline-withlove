-- adeline-world's legacy invite RPC is not used by adeline-ui/adeline-brain.
-- Keep the historical function in place, but prevent browser roles from
-- invoking a SECURITY DEFINER path outside the current family-linking API.
REVOKE EXECUTE ON FUNCTION public.redeem_invite_code(TEXT, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.redeem_invite_code(TEXT, TEXT) FROM anon, authenticated;
