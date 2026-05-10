from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0001_initial'),
        ('users', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='PatientTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('reason', models.TextField(blank=True, verbose_name="Sabab / izoh")),
                ('transferred_at', models.DateTimeField(auto_now_add=True, verbose_name="Ko'chirilgan vaqt")),
                ('patient_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_transfers', to='patients.patientcard', verbose_name='Bemor')),
                ('from_department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_transfers_from', to='patients.department', verbose_name="Avvalgi bo'lim")),
                ('from_doctor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_transfers_from_doctor', to='patients.doctor', verbose_name="Avvalgi shifokor")),
                ('from_dept_head', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_transfers_from_head', to='patients.doctor', verbose_name="Avvalgi bo'lim mudiri")),
                ('to_department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_transfers_to', to='patients.department', verbose_name="Yangi bo'lim")),
                ('to_doctor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_transfers_to_doctor', to='patients.doctor', verbose_name="Yangi shifokor")),
                ('to_dept_head', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_transfers_to_head', to='patients.doctor', verbose_name="Yangi bo'lim mudiri")),
                ('transferred_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.customuser', verbose_name="Kim ko'chirdi")),
            ],
            options={'verbose_name': "Ko'chirish tarixi", 'verbose_name_plural': "Ko'chirish tarixi", 'ordering': ['transferred_at']},
        ),
    ]