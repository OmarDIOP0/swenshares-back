# Generated by Django 4.2.1 on 2024-12-19 12:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('sharedapp', '0001_initial'),
        ('issuingCompany', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='announcement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='sharedapp.announcement'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='buyer_content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buyer_transactions', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='issuing_company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='issuingCompany.issuingcompany'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='seller_content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_transactions', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='validated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='validated_transactions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='sociale',
            name='issuing_company',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='sociale_details', to='issuingCompany.issuingcompany'),
        ),
        migrations.AddField(
            model_name='socialact',
            name='approved_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_approved', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='socialact',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='socialact',
            name='examined_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_examined', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='socialact',
            name='issuing_company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_company', to='issuingCompany.issuingcompany'),
        ),
        migrations.AddField(
            model_name='issuingcompany',
            name='approved_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_approved', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='issuingcompany',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='issuingcompany',
            name='examined_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_examined', to=settings.AUTH_USER_MODEL),
        ),
    ]
