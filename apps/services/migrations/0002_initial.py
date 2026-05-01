from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
        ('patients', '0015_patientcard_visit_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Medicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nomi')),
                ('unit', models.CharField(
                    choices=[('dona','dona'),('ml','ml'),('mg','mg'),('g','g'),
                             ('l','l'),('ampula','ampula'),('kapsula','kapsula'),
                             ('tabletka','tabletka'),('paket','paket'),
                             ('shisha','shisha'),('tuba','tuba')],
                    default='dona', max_length=20, verbose_name='Birlik'
                )),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'verbose_name':'Dori-darmon','verbose_name_plural':'Dori-darmonlar','ordering':['name']},
        ),
        migrations.CreateModel(
            name='PatientMedicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=10, verbose_name='Miqdori')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Narxi (so'm)")),
                ('ordered_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, verbose_name='Izoh')),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='services.medicine', verbose_name='Dori')),
                ('patient_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_medicines', to='patients.patientcard', verbose_name='Bemor kartasi')),
                ('ordered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordered_medicines', to='patients.doctor', verbose_name='Buyurtma bergan shifokor')),
            ],
            options={'verbose_name':'Bemor dorisi','verbose_name_plural':'Bemor dorilari','ordering':['-ordered_at']},
        ),
    ]
