from django.db import migrations


def force_external_sports(apps, schema_editor):
    Activite = apps.get_model("core", "Activite")
    Activite.objects.filter(libelle__iregex=r"(tennis|basket|football|foot)").update(typeAcces="EXTERNE")


def noop_reverse(apps, schema_editor):
    # We do not auto-revert, to avoid changing user-managed access types.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_activite_typeacces"),
    ]

    operations = [
        migrations.RunPython(force_external_sports, noop_reverse),
    ]
