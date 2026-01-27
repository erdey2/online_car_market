from django.db import models

class InvoiceDeclarationMixin(models.Model):
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        # null=True,
        # blank=True,

        db_index=True
    )
    declaration_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        abstract = True
