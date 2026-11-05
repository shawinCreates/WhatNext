# Generated migration for embeddings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_movie_director'),
    ]

    operations = [
        migrations.AddField(
            model_name='movie',
            name='embedding',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='movie',
            name='embedding_model',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='movie',
            name='embedding_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='show',
            name='embedding',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='show',
            name='embedding_model',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='show',
            name='embedding_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
