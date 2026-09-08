"""
Facade module for client form views in EHModuli.
Delegates to specialized domain view modules:
- views_form_access: authentication, navigation, step traversal, summary & success
- views_upload: file uploads, absence declarations, requirement skipping
- views_submission: partial and complete submissions, PDF report receipts
- views_admin: re-exported for full backward compatibility
"""

import logging

logger = logging.getLogger('modules')

# 1. Form Access & Step Navigation
from .views_form_access import (
    published_form_access,
    get_form_by_token,
    form_step_view,
    form_summary_view,
    form_success_view,
)

# 2. Upload & Document Requirements Processing
from .views_upload import (
    published_form_upload,
    upload_document_view,
    skip_optional_document,
)

# 3. Form Submission & Receipts
from .views_submission import (
    published_form_receipt,
    assignment_receipt,
    form_submission_view,
    published_form_submit,
)

# 4. Backward Compatibility Re-exports for Administrative Views
from .views_admin import (
    admin_dashboard,
    form_template_list,
    form_template_create,
    form_template_edit,
    form_template_duplicate,
    customer_list,
    customer_create,
    customer_edit,
    customer_delete,
    customer_reset_password,
    assignment_detail,
    assign_form_to_customer,
    builder_list,
    builder_create,
    builder_edit,
    builder_preview,
    operational_guide,
    reopen_assignment_for_upload,
    assignment_delete,
    assignment_update_status,
    analytics_dashboard,
)
