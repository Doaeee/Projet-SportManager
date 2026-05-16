from django.db import migrations, models


def mark_existing_inscriptions_validated(apps, schema_editor):
    Inscription = apps.get_model("core", "Inscription")
    Inscription.objects.filter(statut__isnull=True).update(statut="VALIDEE")
    Inscription.objects.all().update(statut="VALIDEE")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_seance_dateseance"),
    ]

    operations = [
        migrations.AddField(
            model_name="inscription",
            name="statut",
            field=models.CharField(
                choices=[("EN_ATTENTE", "En attente paiement"), ("VALIDEE", "Validée")],
                default="EN_ATTENTE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="paiement",
            name="inscription",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="paiements",
                to="core.inscription",
            ),
        ),
        migrations.RunPython(mark_existing_inscriptions_validated, noop_reverse),
    ]
