from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Abonnement, Activite, Coach, Inscription, Membre, Paiement, Seance, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("SportManager", {"fields": ("login", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("login", "email", "role")}),
    )
    list_display = ("login", "email", "role", "is_staff", "is_active")
    search_fields = ("login", "email")
    ordering = ("login",)


@admin.register(Membre)
class MembreAdmin(admin.ModelAdmin):
    list_display = ("numMembre", "utilisateur", "dateNaissance", "dateAdhesion")
    search_fields = ("numMembre", "utilisateur__login", "utilisateur__email")


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ("numCoach", "utilisateur", "specialite")
    search_fields = ("numCoach", "utilisateur__login", "specialite")


@admin.register(Activite)
class ActiviteAdmin(admin.ModelAdmin):
    list_display = ("idActivite", "libelle", "tarifMensuel")
    search_fields = ("libelle",)


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("libelle", "periodicite", "prix", "actif", "ordre")
    list_filter = ("periodicite", "actif")
    search_fields = ("libelle",)


@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = ("idSeance", "activite", "dateSeance", "jour", "heureDebut", "heureFin", "capaciteMax", "coach")
    list_filter = ("dateSeance", "jour", "activite")
    search_fields = ("activite__libelle", "coach__utilisateur__login")


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ("idInscription", "membre", "seance", "statut", "dateInscription")
    list_filter = ("seance__activite", "seance__jour")
    search_fields = ("membre__numMembre", "membre__utilisateur__login", "seance__activite__libelle")


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("idPaiment", "membre", "inscription", "montant", "modePaiement", "statut", "datePaiement")
    list_filter = ("statut", "modePaiement")
    search_fields = ("membre__numMembre", "membre__utilisateur__login")
