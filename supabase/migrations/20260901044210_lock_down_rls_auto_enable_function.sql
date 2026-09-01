REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO postgres, service_role;
