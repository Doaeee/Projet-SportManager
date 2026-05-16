from decimal import Decimal

from django.test import TestCase

from .models import Activite


class ActiviteTypeAccesRulesTests(TestCase):
    def test_tennis_is_forced_to_external(self):
        activite = Activite.objects.create(
            libelle="Tennis",
            description="Cours de tennis",
            tarifMensuel=Decimal("200.00"),
            typeAcces=Activite.TypeAcces.INTERNE,
        )
        self.assertEqual(activite.typeAcces, Activite.TypeAcces.EXTERNE)

    def test_non_external_activity_keeps_selected_access_type(self):
        activite = Activite.objects.create(
            libelle="Yoga",
            description="Cours de yoga",
            tarifMensuel=Decimal("150.00"),
            typeAcces=Activite.TypeAcces.INTERNE,
        )
        self.assertEqual(activite.typeAcces, Activite.TypeAcces.INTERNE)
