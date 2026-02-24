from django.utils import timezone
from cloudinary.uploader import upload
from templated_mail.mail import BaseEmailMessage

class ContractService:

    @staticmethod
    def send_to_employee(contract):
        if contract.status != 'draft':
            raise ValueError("Contract already sent")

        contract.status = 'sent_to_employee'
        contract.save(update_fields=["status"])

        profile = getattr(contract.employee.user, "profile", None)
        name = profile.get_full_name() if profile else contract.employee.user.email

        BaseEmailMessage(
            template_name='email/contract_sent.html',
            context={'name': name, 'pdf_url': contract.draft_document_url}
        ).send(to=[contract.employee.user.email])

        return contract.draft_document_url

    @staticmethod
    def upload_signed(contract, file):
        if contract.status != 'sent_to_employee':
            raise ValueError("Contract not yet sent to employee")

        result = upload(
            file.read(),
            folder="contracts/drafts/",
            resource_type="raw",
            format="pdf",
            type="upload",
            access_mode="public",
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )

        contract.employee_signed_document_url = result['secure_url']
        contract.employee_signed_at = timezone.now()
        contract.status = 'signed_by_employee'
        contract.save()

        return contract.employee_signed_document_url

    @staticmethod
    def finalize(contract, file, finalized_by):
        if contract.status != 'signed_by_employee':
            raise ValueError("Employee must sign first")

        result = upload(
            file.read(),
            folder="contracts/final/",
            resource_type="raw",
            format="pdf",
            type="upload",
            access_mode="public",
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )

        contract.final_document_url = result['secure_url']
        contract.finalized_by = finalized_by
        contract.finalized_at = timezone.now()
        contract.status = 'active'
        contract.save()

        profile = getattr(contract.employee.user, "profile", None)
        name = profile.get_full_name() if profile else contract.employee.user.email

        BaseEmailMessage(
            template_name='email/contract_active.html',
            context={'name': name, 'pdf_url': contract.final_document_url}
        ).send(to=[contract.employee.user.email])

        return contract.final_document_url
