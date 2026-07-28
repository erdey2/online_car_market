from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from ..models import Car, CarMake, CarModel, CarMakeRequest, CarModelRequest
from .car_request_notification_service import CarRequestNotificationService


class CarTaxonomyService:

    CAR_MAKES_CACHE_KEY = "car_makes_list"
    CAR_MODELS_CACHE_KEY = "car_models_list"

    @staticmethod
    def _clear_taxonomy_cache():
        cache.delete(
            CarTaxonomyService.CAR_MAKES_CACHE_KEY
        )
        cache.delete(
            CarTaxonomyService.CAR_MODELS_CACHE_KEY
        )

    @staticmethod
    def _validate_pending(request_obj):
        if request_obj.status != request_obj.Status.PENDING:
            raise ValidationError(
                "Request has already been processed."
            )

    # MAKE REQUESTS
    @staticmethod
    @transaction.atomic
    def approve_make_request(request_obj, reviewer):

        request_obj = (
            CarMakeRequest.objects
            .select_for_update()
            .select_related(
                "requested_by"
            )
            .get(pk=request_obj.pk)
        )

        CarTaxonomyService._validate_pending(
            request_obj
        )

        make_name = request_obj.requested_name.strip()

        if not make_name:
            raise ValidationError(
                "Make name cannot be empty."
            )

        make, _ = CarMake.objects.get_or_create(
            name=make_name
        )

        request_obj.status = (
            CarMakeRequest.Status.APPROVED
        )
        request_obj.reviewed_by = reviewer
        request_obj.reviewed_at = timezone.now()

        request_obj.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
            ]
        )

        # Attach waiting cars
        Car.objects.filter(
            pending_make_request=request_obj
        ).update(
            make_ref=make,
            make=make.name,
            pending_make_request=None,
        )

        CarTaxonomyService._clear_taxonomy_cache()

        transaction.on_commit(
            lambda: (
                CarRequestNotificationService
                .notify_request_approved(
                    request_obj,
                    "make",
                )
            )
        )

        return make

    @staticmethod
    @transaction.atomic
    def reject_make_request(
        request_obj,
        reviewer,
        reason="",
    ):

        request_obj = (
            CarMakeRequest.objects
            .select_for_update()
            .select_related(
                "requested_by"
            )
            .get(pk=request_obj.pk)
        )

        CarTaxonomyService._validate_pending(
            request_obj
        )

        request_obj.status = (
            CarMakeRequest.Status.REJECTED
        )
        request_obj.reviewed_by = reviewer
        request_obj.reviewed_at = timezone.now()
        request_obj.rejection_reason = reason

        request_obj.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        # Remove pending relation
        Car.objects.filter(
            pending_make_request=request_obj
        ).update(
            pending_make_request=None
        )

        transaction.on_commit(
            lambda: (
                CarRequestNotificationService
                .notify_request_rejected(
                    request_obj,
                    "make",
                )
            )
        )

        return request_obj


    # MODEL REQUESTS
    @staticmethod
    @transaction.atomic
    def approve_model_request(
        request_obj,
        reviewer,
    ):

        request_obj = (
            CarModelRequest.objects
            .select_for_update()
            .select_related(
                "requested_by",
                "make",
            )
            .get(pk=request_obj.pk)
        )

        CarTaxonomyService._validate_pending(
            request_obj
        )

        model_name = request_obj.requested_name.strip()

        if not model_name:
            raise ValidationError(
                "Model name cannot be empty."
            )

        model, _ = CarModel.objects.get_or_create(
            make=request_obj.make,
            name=model_name,
        )

        request_obj.status = (
            CarModelRequest.Status.APPROVED
        )
        request_obj.reviewed_by = reviewer
        request_obj.reviewed_at = timezone.now()

        request_obj.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
            ]
        )

        # Attach waiting cars
        Car.objects.filter(
            pending_model_request=request_obj
        ).update(
            model_ref=model,
            model=model.name,
            pending_model_request=None,
        )

        CarTaxonomyService._clear_taxonomy_cache()

        transaction.on_commit(
            lambda: (
                CarRequestNotificationService
                .notify_request_approved(
                    request_obj,
                    "model",
                )
            )
        )

        return model


    @staticmethod
    @transaction.atomic
    def reject_model_request(
        request_obj,
        reviewer,
        reason="",
    ):

        request_obj = (
            CarModelRequest.objects
            .select_for_update()
            .select_related(
                "requested_by"
            )
            .get(pk=request_obj.pk)
        )

        CarTaxonomyService._validate_pending(
            request_obj
        )

        request_obj.status = (
            CarModelRequest.Status.REJECTED
        )
        request_obj.reviewed_by = reviewer
        request_obj.reviewed_at = timezone.now()
        request_obj.rejection_reason = reason

        request_obj.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        # Remove pending relation
        Car.objects.filter(
            pending_model_request=request_obj
        ).update(
            pending_model_request=None
        )

        transaction.on_commit(
            lambda: (
                CarRequestNotificationService
                .notify_request_rejected(
                    request_obj,
                    "model",
                )
            )
        )

        return request_obj
