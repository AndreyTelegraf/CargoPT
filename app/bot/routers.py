from aiogram import Dispatcher

from app.bot.handlers.start import router as start_router
from app.bot.handlers.job_start import router as job_start_router
from app.bot.handlers.job_pickup import router as job_pickup_router
from app.bot.handlers.job_dropoff import router as job_dropoff_router
from app.bot.handlers.job_address_details import router as job_address_details_router
from app.bot.handlers.job_requested_datetime import router as job_requested_datetime_router
from app.bot.handlers.job_item import router as job_item_router
from app.bot.handlers.job_media import router as job_media_router
from app.bot.handlers.job_payload import router as job_payload_router
from app.bot.handlers.job_volume import router as job_volume_router
from app.bot.handlers.job_loaders import router as job_loaders_router
from app.bot.handlers.job_tail_lift import router as job_tail_lift_router
from app.bot.handlers.job_crane import router as job_crane_router
from app.bot.handlers.job_mobile_lift import router as job_mobile_lift_router
from app.bot.handlers.job_needs_assembly import router as job_needs_assembly_router
from app.bot.handlers.job_needs_packing import router as job_needs_packing_router
from app.bot.handlers.job_contact_phone import router as job_contact_phone_router
from app.bot.handlers.job_contact_whatsapp import router as job_contact_whatsapp_router
from app.bot.handlers.job_comment import router as job_comment_router
from app.bot.handlers.job_offer_response import router as job_offer_response_router
from app.bot.handlers.invite import router as invite_router
from app.bot.handlers.carrier_invite_admin import router as carrier_invite_admin_router
from app.bot.handlers.dispatcher_jobs_admin import router as dispatcher_jobs_admin_router
from app.bot.handlers.admin_controls import router as admin_controls_router
from app.bot.handlers.job_assignment_confirmation import router as job_assignment_confirmation_router
from app.bot.handlers.assembly import router as assembly_router
from app.bot.handlers.packing import router as packing_router
from app.bot.handlers.regions import router as regions_router
from app.bot.handlers.vehicle_count import router as vehicle_count_router
from app.bot.handlers.vehicle_type import router as vehicle_type_router
from app.bot.handlers.payload import router as payload_router
from app.bot.handlers.volume import router as volume_router
from app.bot.handlers.tail_lift import router as tail_lift_router
from app.bot.handlers.crane import router as crane_router
from app.bot.handlers.mobile_lift import router as mobile_lift_router
from app.bot.handlers.mobile_lift_floor import router as mobile_lift_floor_router
from app.bot.handlers.mobile_lift_weight import router as mobile_lift_weight_router
from app.bot.handlers.crane_weight import router as crane_weight_router
from app.bot.handlers.crane_reach import router as crane_reach_router
from app.bot.handlers.max_loaders import router as max_loaders_router
from app.bot.handlers.company_phone import router as company_phone_router
from app.bot.handlers.company_email import router as company_email_router
from app.bot.handlers.carrier_moderation_submit import router as carrier_moderation_submit_router
from app.bot.handlers.carrier_public_profile import router as carrier_public_profile_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(invite_router)
    dp.include_router(start_router)
    dp.include_router(carrier_invite_admin_router)
    dp.include_router(dispatcher_jobs_admin_router)
    dp.include_router(admin_controls_router)
    dp.include_router(carrier_public_profile_router)
    dp.include_router(packing_router)
    dp.include_router(regions_router)
    dp.include_router(vehicle_count_router)
    dp.include_router(vehicle_type_router)
    dp.include_router(payload_router)
    dp.include_router(volume_router)
    dp.include_router(tail_lift_router)
    dp.include_router(crane_router)
    dp.include_router(mobile_lift_router)
    dp.include_router(mobile_lift_floor_router)
    dp.include_router(mobile_lift_weight_router)
    dp.include_router(crane_weight_router)
    dp.include_router(crane_reach_router)
    dp.include_router(max_loaders_router)
    dp.include_router(company_phone_router)
    dp.include_router(company_email_router)
    dp.include_router(carrier_moderation_submit_router)
    dp.include_router(assembly_router)
    dp.include_router(job_start_router)
    dp.include_router(job_pickup_router)
    dp.include_router(job_dropoff_router)
    dp.include_router(job_address_details_router)
    dp.include_router(job_requested_datetime_router)
    dp.include_router(job_item_router)
    dp.include_router(job_media_router)
    dp.include_router(job_payload_router)
    dp.include_router(job_volume_router)
    dp.include_router(job_loaders_router)
    dp.include_router(job_tail_lift_router)
    dp.include_router(job_crane_router)
    dp.include_router(job_mobile_lift_router)
    dp.include_router(job_needs_assembly_router)
    dp.include_router(job_needs_packing_router)
    dp.include_router(job_contact_phone_router)
    dp.include_router(job_contact_whatsapp_router)
    dp.include_router(job_comment_router)
    dp.include_router(job_offer_response_router)
    dp.include_router(job_assignment_confirmation_router)
