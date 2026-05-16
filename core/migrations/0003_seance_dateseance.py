from django.db import migrations, models
from django.utils import timezone


def fill_date_seance_from_jour(apps, schema_editor):
    Seance = apps.get_model("core", "Seance")
    today = timezone.localdate()
    week_start = today - timezone.timedelta(days=today.weekday())

    weekday_map = {
        "LUNDI": 0,
        "MARDI": 1,
        "MERCREDI": 2,
        "JEUDI": 3,
        "VENDREDI": 4,
        "SAMEDI": 5,
        "DIMANCHE": 6,
    }

    seances = Seance.objects.filter(dateSeance__isnull=True)
    for seance in seances:
        day_offset = weekday_map.get(seance.jour)
        if day_offset is None:
            continue
        seance.dateSeance = week_start + timezone.timedelta(days=day_offset)
        seance.save(update_fields=["dateSeance"])


def reverse_fill_date_seance_from_jour(apps, schema_editor):
    # No destructive rollback: keep any assigned dates.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_activite_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="seance",
            name="dateSeance",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(fill_date_seance_from_jour, reverse_fill_date_seance_from_jour),
    ]
