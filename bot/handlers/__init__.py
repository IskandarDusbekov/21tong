from . import admin, onboarding, proofs

# admin birinchi: /ulash va qo'mondonlik tugmalari FSM holatlaridan qat'i nazar ishlasin
routers = [admin.router, onboarding.router, proofs.router]
