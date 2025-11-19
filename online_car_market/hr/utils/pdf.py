from weasyprint import HTML
from django.template.loader import render_to_string
from cloudinary.uploader import upload

def generate_and_upload_pdf(contract):
    html_string = render_to_string('hr/contract_template.html', {'contract': contract})
    pdf_bytes = HTML(string=html_string).write_pdf()

    public_id = f"contract_{contract.employee.user.email}_{contract.start_date.strftime('%Y%m%d')}"

    result = upload(
        pdf_bytes,
        folder="contracts/drafts/",
        public_id=public_id,
        resource_type="raw",
        format="pdf",
        overwrite=True,
        type="upload",
        access_mode="public",
        use_filename=True,
        unique_filename=False
    )
    return result['secure_url']
