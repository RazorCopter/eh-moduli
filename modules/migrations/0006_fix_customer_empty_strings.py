from django.db import migrations

def convert_empty_strings_to_null(apps, schema_editor):
    Customer = apps.get_model('modules', 'Customer')
    Customer.objects.filter(fiscal_code='').update(fiscal_code=None)
    Customer.objects.filter(vat_number='').update(vat_number=None)
    Customer.objects.filter(phone='').update(phone=None)

class Migration(migrations.Migration):
    dependencies = [
        ('modules', '0005_documentupload_availability'),
    ]

    operations = [
        migrations.RunPython(convert_empty_strings_to_null, reverse_code=migrations.RunPython.noop),
    ]
