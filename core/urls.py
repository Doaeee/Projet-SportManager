from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.landing, name="landing"),
    path("app/", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/coach/", views.coach_dashboard, name="coach_dashboard"),
    path("dashboard/membre/", views.membre_dashboard, name="membre_dashboard"),
    # Membre
    path("membre/abonnements/", views.membre_abonnements, name="membre_abonnements"),
    path("membre/abonnements/<int:abonnement_id>/paiement/", views.membre_abonnement_paiement, name="membre_abonnement_paiement"),
    path("membre/planning/", views.membre_planning, name="membre_planning"),
    path("membre/seances/<int:seance_id>/inscription/", views.membre_inscription, name="membre_inscription"),
    path("membre/paiements/nouveau/<int:seance_id>/", views.membre_paiement_nouveau, name="membre_paiement_nouveau"),
    # Coach
    path("coach/planning/", views.coach_planning, name="coach_planning"),
    path("coach/seances/<int:seance_id>/inscrits/", views.coach_inscrits, name="coach_inscrits"),
    # Admin (app)
    path("admin-app/paiements/", views.admin_paiements, name="admin_paiements"),
    path("admin-app/paiements/<int:paiement_id>/valider/", views.admin_valider_paiement, name="admin_valider_paiement"),
    path("admin-app/abonnements/", views.admin_abonnements, name="admin_abonnements"),
    path("admin-app/abonnements/nouveau/", views.admin_abonnement_create, name="admin_abonnement_create"),
    path("admin-app/abonnements/<int:abonnement_id>/modifier/", views.admin_abonnement_edit, name="admin_abonnement_edit"),
    path("admin-app/abonnements/<int:abonnement_id>/supprimer/", views.admin_abonnement_delete, name="admin_abonnement_delete"),
    path("admin-app/activites/", views.admin_activites, name="admin_activites"),
    path("admin-app/activites/nouveau/", views.admin_activite_create, name="admin_activite_create"),
    path("admin-app/activites/<int:activite_id>/modifier/", views.admin_activite_edit, name="admin_activite_edit"),
    path("admin-app/activites/<int:activite_id>/supprimer/", views.admin_activite_delete, name="admin_activite_delete"),
    path("admin-app/seances/", views.admin_seances, name="admin_seances"),
    path("admin-app/seances/nouveau/", views.admin_seance_create, name="admin_seance_create"),
    path("admin-app/seances/<int:seance_id>/modifier/", views.admin_seance_edit, name="admin_seance_edit"),
    path("admin-app/seances/<int:seance_id>/supprimer/", views.admin_seance_delete, name="admin_seance_delete"),
    path("admin-app/comptes/", views.admin_comptes, name="admin_comptes"),
    path("admin-app/comptes/nouveau/", views.admin_compte_create, name="admin_compte_create"),
    path("admin-app/comptes/<int:user_id>/supprimer/", views.admin_compte_delete, name="admin_compte_delete"),
]

