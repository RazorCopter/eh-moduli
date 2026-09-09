from django.db import migrations
from modules.validators import get_mimes_for_extensions


def sync_existing_mime_types(apps, schema_editor):
    DocumentRequirement = apps.get_model('modules', 'DocumentRequirement')
    for doc in DocumentRequirement.objects.all():
        if not doc.allowed_extensions:
            continue
        derived = get_mimes_for_extensions(doc.allowed_extensions)
        current = [m.strip() for m in (doc.mime_types or '').split(',') if m.strip()]
        combined = []
        for m in current + derived:
            if m not in combined:
                combined.append(m)
        if combined:
            doc.mime_types = ','.join(combined)
            doc.save(update_fields=['mime_types'])


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0012_alter_documentrequirement_max_file_size'),
    ]

    operations = [
        migrations.RunPython(sync_existing_mime_types, reverse_code=migrations.RunPython.noop),
    ]
