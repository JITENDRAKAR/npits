from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_marketticker_instrument_last_price_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='date_of_birth',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='gender',
            field=models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')], null=True, blank=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='investor_type',
            field=models.CharField(max_length=20, choices=[('conservative', 'Conservative'), ('moderate', 'Moderate'), ('growth', 'Growth'), ('aggressive', 'Aggressive')], default='moderate'),
        ),
    ]
