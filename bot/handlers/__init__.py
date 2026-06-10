from aiogram import Router
from .menu_router      import router as menu_router
from .auth             import router as auth_router
from .vehicles         import router as vehicles_router
from .addresses        import router as addresses_router
from .trips            import router as trips_router
from .tracking         import router as tracking_router
from .reports          import router as reports_router
from .receipts         import router as receipts_router
from .tax_handler      import router as tax_router
from .income           import router as income_router
from .export_handler   import router as export_router
from .settings         import router as settings_router
from .help             import router as help_router
from .stats            import router as stats_router
from .admin            import router as admin_router
from .audit            import router as audit_router
from .open_items       import router as open_items_router
from .dashboard        import router as dashboard_router
from .steuer_package   import router as steuer_package_router
from .team             import router as team_router


def setup_routers() -> Router:
    main_router = Router()
    main_router.include_router(menu_router)       # ПЕРШИМ
    main_router.include_router(auth_router)
    main_router.include_router(vehicles_router)
    main_router.include_router(addresses_router)
    main_router.include_router(trips_router)
    main_router.include_router(tracking_router)
    main_router.include_router(reports_router)
    main_router.include_router(receipts_router)
    main_router.include_router(tax_router)
    main_router.include_router(income_router)
    main_router.include_router(export_router)
    main_router.include_router(settings_router)
    main_router.include_router(help_router)
    main_router.include_router(stats_router)
    main_router.include_router(audit_router)
    main_router.include_router(open_items_router)
    main_router.include_router(dashboard_router)
    main_router.include_router(steuer_package_router)
    main_router.include_router(team_router)
    main_router.include_router(admin_router)
    return main_router
