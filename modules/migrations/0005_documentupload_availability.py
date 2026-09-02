# Generated migration for availability status and reason

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0004_documentrequirement_allow_file_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentupload',
            name='availability_status',
            field=models.CharField(
                choices=[('uploaded', 'File Caricato'), ('not_available', 'Non Disponibile')],
                default='uploaded',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='documentupload',
            name='motivazione_indisponibilita',
            field=models.TextField(
                blank=True,
                help_text='Reason why document is not available',
                null=True
            ),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='original_filename',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='stored_filename',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='relative_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='file_extension',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='mime_type_detected',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='file_size',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='documentupload',
            name='sha256_checksum',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
