from .main_menu import main_menu_kb, lang_kb, confirm_kb, cancel_kb, CANCEL_TEXTS
from .vehicles import vehicles_list_kb, vehicle_actions_kb, vehicle_select_kb
from .addresses import addresses_list_kb, address_actions_kb, address_type_kb, address_select_kb
from .trips import trips_list_kb, trip_actions_kb, purpose_kb, month_filter_kb
from .reports import report_period_kb, report_vehicle_kb

__all__ = [
    "main_menu_kb", "lang_kb", "confirm_kb", "cancel_kb",
    "vehicles_list_kb", "vehicle_actions_kb", "vehicle_select_kb",
    "addresses_list_kb", "address_actions_kb", "address_type_kb", "address_select_kb",
    "trips_list_kb", "trip_actions_kb", "purpose_kb", "month_filter_kb",
    "report_period_kb", "report_vehicle_kb",
]
