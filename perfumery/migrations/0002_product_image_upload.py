from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perfumery', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='image_url',
            new_name='image',
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(
                blank=True,
                help_text='Select media from your device.',
                upload_to='products/',
            ),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Enter the price in Nigerian naira (NGN).',
                max_digits=10,
            ),
        ),
    ]