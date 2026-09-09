"""
Facade module for administrative and backoffice views in EHModuli.
Delegates specialized sub-domains to dedicated view modules:
- views_dashboard: admin dashboard, operational guide, KPI analytics
- views_customers: customer registry, inline editing, password reset, deletion
- views_assignments: customer assignment, status state machine, reopen, deletion
- views_builder: form templates CRUD and drag-and-drop form builder
- views_users_api: backoffice user management endpoints
"""

import logging
from .upload_security import safe_join_paths, save_manifest_atomic

logger = logging.getLogger('modules')

# Permission helpers
def is_admin_user(user):
    """Strictly administrators and superusers (for user management)"""
    return bool(user and user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')))

def is_backoffice_user(user):
    """Backoffice operators and administrators (for operational dashboards and management)"""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role in ('admin', 'operator'))))

# Backward compatibility alias
is_admin = is_backoffice_user

# 1. Dashboard & Operational Views
from .views_dashboard import (
    admin_dashboard,
    operational_guide,
    analytics_dashboard,
)

# 2. Customer Management Views
from .views_customers import (
    customer_list,
    customer_create,
    customer_edit,
    customer_delete,
    customer_reset_password,
)

# 3. Assignment & Practice Management Views
from .views_assignments import (
    assignment_detail,
    assign_form_to_customer,
    reopen_assignment_for_upload,
    assignment_delete,
    assignment_update_status,
)

# 4. Form Template & Builder Views
from .views_builder import (
    form_template_list,
    form_template_create,
    form_template_edit,
    form_template_duplicate,
    builder_list,
    builder_create,
    builder_edit,
    builder_preview,
)

# 5. Backoffice User Management API Endpoints
from .views_users_api import (
    admin_user_list,
    admin_user_create,
    admin_user_update,
    admin_user_delete,
    admin_user_password_generate,
)

# 6. System Maintenance & Database Backup/Restore Views
from .views_maintenance import (
    admin_maintenance,
    admin_reset_statistics,
    admin_backup_create,
    admin_backup_download,
    admin_backup_restore,
    admin_backup_delete,
    admin_update_settings,
)
