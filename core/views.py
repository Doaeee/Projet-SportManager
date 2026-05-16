from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import AbonnementForm, ActiviteForm, PaiementForm, PublicMembreSignupForm, SeanceForm, UtilisateurCreateForm
from .models import Abonnement, Activite, Coach, Inscription, Membre, Paiement, Seance, Utilisateur


def _role_required(*roles: str):
    def decorator(view_func):
        @login_required
        def _wrapped(request: HttpRequest, *args, **kwargs):
            user: Utilisateur = request.user  # type: ignore[assignment]
            if user.role not in roles:
                messages.error(request, "Accès refusé.")
                return redirect("home")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def _jours_ordonnes():
    return [
        (Seance.Jour.LUNDI, "Lundi"),
        (Seance.Jour.MARDI, "Mardi"),
        (Seance.Jour.MERCREDI, "Mercredi"),
        (Seance.Jour.JEUDI, "Jeudi"),
        (Seance.Jour.VENDREDI, "Vendredi"),
        (Seance.Jour.SAMEDI, "Samedi"),
        (Seance.Jour.DIMANCHE, "Dimanche"),
    ]


def _resolve_week(week_param: str | None = None):
    aujourd_hui = timezone.localdate()
    focus_day = aujourd_hui
    if week_param:
        try:
            parsed_day = date.fromisoformat(week_param)
            focus_day = parsed_day
        except ValueError:
            focus_day = aujourd_hui

    debut_semaine = focus_day - timedelta(days=focus_day.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    return focus_day, debut_semaine, fin_semaine


def _build_week_calendar(seances, week_param: str | None = None):
    aujourd_hui = timezone.localdate()
    focus_day, debut_semaine, _ = _resolve_week(week_param)
    jours_ordonnes = _jours_ordonnes()
    codes_par_index = [code for code, _ in jours_ordonnes]

    dates_par_jour = {
        code: debut_semaine + timedelta(days=index)
        for index, (code, _) in enumerate(jours_ordonnes)
    }
    seances_par_jour = {code: [] for code, _ in jours_ordonnes}
    for seance in seances:
        if not seance.dateSeance:
            continue
        day_code = codes_par_index[seance.dateSeance.weekday()]
        seances_par_jour.setdefault(day_code, []).append(seance)

    calendar_days = []
    for code, label in jours_ordonnes:
        date_jour = dates_par_jour[code]
        calendar_days.append(
            {
                "code": code,
                "label": label,
                "date": date_jour,
                "is_today": date_jour == aujourd_hui,
                "seances": seances_par_jour.get(code, []),
            }
        )

    return {
        "calendar_days": calendar_days,
        "current_month_year": focus_day,
        "week_start": debut_semaine,
        "week_end": debut_semaine + timedelta(days=6),
        "prev_week_iso": (debut_semaine - timedelta(days=7)).isoformat(),
        "next_week_iso": (debut_semaine + timedelta(days=7)).isoformat(),
    }


def _is_seance_passee(seance: Seance) -> bool:
    if not seance.dateSeance:
        return True
    # Règle métier: une séance est "passée" seulement si son JOUR est passé.
    # Le jour courant reste accessible, quelle que soit l'heure.
    return seance.dateSeance < timezone.localdate()


def _abonnement_actif_pour_membre(membre: Membre):
    maintenant = timezone.now()
    paiements = (
        Paiement.objects.select_related("abonnement")
        .filter(membre=membre, abonnement__isnull=False, statut=Paiement.Statut.VALIDE)
        .order_by("-datePaiement")
    )
    for paiement in paiements:
        if not paiement.abonnement:
            continue
        duree_jours = 365 if paiement.abonnement.periodicite == Abonnement.Periodicite.ANNUEL else 30
        date_fin = paiement.datePaiement + timedelta(days=duree_jours)
        if date_fin >= maintenant:
            return paiement, date_fin
    return None, None


def _abonnement_couvre_seance(membre: Membre, seance: Seance):
    paiement_abonnement, date_fin = _abonnement_actif_pour_membre(membre)
    if not paiement_abonnement or not paiement_abonnement.abonnement:
        return False, paiement_abonnement, date_fin

    # Annuel: toutes les activités. Mensuel: uniquement activités internes.
    if paiement_abonnement.abonnement.periodicite == Abonnement.Periodicite.ANNUEL:
        return True, paiement_abonnement, date_fin
    if seance.activite.typeAcces == Activite.TypeAcces.INTERNE:
        return True, paiement_abonnement, date_fin
    return False, paiement_abonnement, date_fin


@require_http_methods(["GET", "POST"])
def landing(request: HttpRequest) -> HttpResponse:
    activites = Activite.objects.all().order_by("libelle")[:6]
    abonnements = Abonnement.objects.filter(actif=True).order_by("ordre", "prix", "libelle")
    espaces = [
        {
            "nom": "Zone cardio training",
            "description": "Tapis, velos et rameurs pour travail d'endurance et perte de poids.",
            "icone": "bi-heart-pulse",
        },
        {
            "nom": "Piscine de natation",
            "description": "Bassin dedie a la natation pour entrainement, endurance et remise en forme.",
            "icone": "bi-water",
        },
        {
            "nom": "Plateau musculation",
            "description": "Machines guidees et charges libres pour tous les niveaux.",
            "icone": "bi-lightning-charge",
        },
        {
            "nom": "Studio cours collectifs",
            "description": "Espace dedie au fitness, HIIT, stretching et coaching de groupe.",
            "icone": "bi-people",
        },
    ]
    terrains = [
        {
            "nom": "Terrain de football",
            "description": "Surface adaptee pour matchs amicaux, entrainements et tournois.",
            "icone": "bi-dribbble",
        },
        {
            "nom": "Terrain de basketball",
            "description": "Paniers reglables et marquage complet pour seances competitives.",
            "icone": "bi-trophy",
        },
        {
            "nom": "Court de tennis",
            "description": "Court entretenu pour pratique loisir ou entrainement technique.",
            "icone": "bi-bullseye",
        },
    ]
    materiels = [
        {
            "nom": "Halteres et kettlebells",
            "description": "Large gamme de charges pour renforcement global et travail fonctionnel.",
            "icone": "bi-box2",
        },
        {
            "nom": "Materiel de boxe",
            "description": "Sacs, pattes d'ours, gants et protections pour entrainements intensifs.",
            "icone": "bi-shield-check",
        },
        {
            "nom": "Accessoires recuperation",
            "description": "Tapis, rouleaux, elastiques et materiel mobilite post-seance.",
            "icone": "bi-stars",
        },
    ]

    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()
        objectifs = request.POST.get("objectifs", "").strip()

        if not nom or not email or not telephone or not objectifs:
            messages.error(request, "Merci de remplir tous les champs du formulaire de rendez-vous.")
        else:
            messages.success(
                request,
                "Votre demande de rendez-vous a bien ete envoyee. Notre equipe vous contactera rapidement.",
            )
            return redirect("landing")

    return render(
        request,
        "landing.html",
        {
            "activites": activites,
            "abonnements": abonnements,
            "espaces": espaces,
            "terrains": terrains,
            "materiels": materiels,
        },
    )


@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = PublicMembreSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Compte cree avec succes. Bienvenue sur SportManager.")
            return redirect("home")
    else:
        form = PublicMembreSignupForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def home(request: HttpRequest) -> HttpResponse:
    user: Utilisateur = request.user  # type: ignore[assignment]
    if user.role == Utilisateur.Role.ADMIN:
        return redirect("admin_dashboard")
    if user.role == Utilisateur.Role.COACH:
        return redirect("coach_dashboard")
    return redirect("membre_dashboard")


@_role_required(Utilisateur.Role.ADMIN)
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    stats = {
        "membres": Membre.objects.count(),
        "coachs": Coach.objects.count(),
        "activites": Activite.objects.count(),
        "seances": Seance.objects.count(),
        "abonnements": Abonnement.objects.filter(actif=True).count(),
        "paiements_attente": Paiement.objects.filter(statut=Paiement.Statut.EN_ATTENTE).count(),
    }
    return render(request, "core/dashboard_admin.html", {"stats": stats})


@_role_required(Utilisateur.Role.COACH)
def coach_dashboard(request: HttpRequest) -> HttpResponse:
    coach = request.user.coach  # type: ignore[attr-defined]
    seances = (
        Seance.objects.select_related("activite")
        .filter(coach=coach)
        .order_by("dateSeance", "heureDebut")[:5]
    )
    return render(request, "core/dashboard_coach.html", {"seances": seances})


@_role_required(Utilisateur.Role.MEMBRE)
def membre_dashboard(request: HttpRequest) -> HttpResponse:
    membre = request.user.membre  # type: ignore[attr-defined]
    inscriptions = (
        Inscription.objects.select_related("seance", "seance__activite")
        .filter(membre=membre)
        .order_by("-dateInscription")[:5]
    )
    paiements = (
        Paiement.objects.filter(membre=membre)
        .order_by("-datePaiement")[:5]
    )
    return render(
        request,
        "core/dashboard_membre.html",
        {"inscriptions": inscriptions, "paiements": paiements},
    )


@_role_required(Utilisateur.Role.MEMBRE)
def membre_abonnements(request: HttpRequest) -> HttpResponse:
    membre = request.user.membre  # type: ignore[attr-defined]
    paiements = Paiement.objects.filter(membre=membre).order_by("-datePaiement")[:10]
    abonnements = Abonnement.objects.filter(actif=True).order_by("ordre", "prix", "libelle")
    paiements_en_attente = set(
        Paiement.objects.filter(membre=membre, abonnement__isnull=False, statut=Paiement.Statut.EN_ATTENTE).values_list(
            "abonnement_id", flat=True
        )
    )
    paiement_abonnement_actif, date_fin_abonnement = _abonnement_actif_pour_membre(membre)
    return render(
        request,
        "core/membre_abonnements.html",
        {
            "paiements": paiements,
            "abonnements": abonnements,
            "paiements_en_attente": paiements_en_attente,
            "abonnement_actif_id": paiement_abonnement_actif.abonnement_id if paiement_abonnement_actif else None,
            "abonnement_actif_fin": date_fin_abonnement,
        },
    )


@_role_required(Utilisateur.Role.MEMBRE)
@require_http_methods(["GET", "POST"])
def membre_abonnement_paiement(request: HttpRequest, abonnement_id: int) -> HttpResponse:
    membre = request.user.membre  # type: ignore[attr-defined]
    abonnement = get_object_or_404(Abonnement, pk=abonnement_id, actif=True)
    paiement_abonnement_actif, date_fin_abonnement = _abonnement_actif_pour_membre(membre)
    if paiement_abonnement_actif:
        messages.info(
            request,
            f"Vous avez déjà un abonnement actif jusqu'au {timezone.localtime(date_fin_abonnement).date():%d/%m/%Y}.",
        )
        return redirect("membre_abonnements")

    paiement_en_attente = (
        Paiement.objects.filter(membre=membre, abonnement=abonnement, statut=Paiement.Statut.EN_ATTENTE)
        .order_by("-datePaiement")
        .first()
    )

    if request.method == "POST":
        if paiement_en_attente:
            messages.info(request, "Un paiement est déjà en attente pour cet abonnement.")
            return redirect("membre_abonnements")
        form = PaiementForm(request.POST)
        if form.is_valid():
            Paiement.objects.create(
                membre=membre,
                abonnement=abonnement,
                montant=abonnement.prix,
                modePaiement=form.cleaned_data["modePaiement"],
                statut=Paiement.Statut.EN_ATTENTE,
            )
            messages.success(request, "Paiement d'abonnement initié (en attente de validation).")
            return redirect("membre_abonnements")
    else:
        form = PaiementForm()

    return render(
        request,
        "core/membre_abonnement_paiement.html",
        {"abonnement": abonnement, "form": form, "paiement_en_attente": paiement_en_attente},
    )


@_role_required(Utilisateur.Role.MEMBRE)
def membre_planning(request: HttpRequest) -> HttpResponse:
    _, week_start, week_end = _resolve_week(request.GET.get("week"))
    today = timezone.localdate()
    semaine_courante_start = today - timedelta(days=today.weekday())
    if week_start < semaine_courante_start:
        messages.info(request, "Vous ne pouvez pas consulter les inscriptions des semaines passées.")
        return redirect(f"{request.path}?week={semaine_courante_start.isoformat()}")
    seances = (
        Seance.objects.select_related("activite", "coach", "coach__utilisateur")
        .filter(dateSeance__range=(week_start, week_end))
        .order_by("dateSeance", "heureDebut")
    )
    membre = request.user.membre  # type: ignore[attr-defined]
    paiement_abonnement_actif, date_fin_abonnement = _abonnement_actif_pour_membre(membre)
    seances_couvertes = set()
    seances_non_couvertes = set()
    for s in seances:
        couverte, _, _ = _abonnement_couvre_seance(membre, s)
        if couverte:
            seances_couvertes.add(s.idSeance)
        else:
            seances_non_couvertes.add(s.idSeance)
    inscriptions_membre = Inscription.objects.filter(membre=membre)
    inscriptions_validees = set(
        inscriptions_membre.filter(statut=Inscription.Statut.VALIDEE).values_list("seance_id", flat=True)
    )
    inscriptions_en_attente = set(
        inscriptions_membre.filter(statut=Inscription.Statut.EN_ATTENTE).values_list("seance_id", flat=True)
    )
    seances_passees = {s.idSeance for s in seances if _is_seance_passee(s)}
    calendar_context = _build_week_calendar(seances, request.GET.get("week"))
    week_start_prec = max(week_start - timedelta(days=7), semaine_courante_start)
    return render(
        request,
        "core/membre_planning.html",
        {
            "seances": seances,
            "inscriptions_validees": inscriptions_validees,
            "inscriptions_en_attente": inscriptions_en_attente,
            "seances_passees": seances_passees,
            "can_go_prev": week_start > semaine_courante_start,
            "prev_week_iso": week_start_prec.isoformat(),
            "abonnement_actif": bool(paiement_abonnement_actif),
            "abonnement_actif_fin": date_fin_abonnement,
            "abonnement_periodicite": (
                paiement_abonnement_actif.abonnement.periodicite
                if paiement_abonnement_actif and paiement_abonnement_actif.abonnement
                else None
            ),
            "seances_couvertes": seances_couvertes,
            "seances_non_couvertes": seances_non_couvertes,
            **calendar_context,
        },
    )


@_role_required(Utilisateur.Role.MEMBRE)
@require_http_methods(["POST"])
def membre_inscription(request: HttpRequest, seance_id: int) -> HttpResponse:
    """
    Séquence métier:
    - authentifié (decorator)
    - vérifier capacité
    - créer inscription
    - redirection paiement
    """
    seance = get_object_or_404(Seance.objects.select_related("activite"), pk=seance_id)
    if _is_seance_passee(seance):
        messages.error(request, "Impossible de s'inscrire à une séance déjà passée.")
        return redirect("membre_planning")
    if seance.places_restantes <= 0:
        messages.error(request, "Plus de places disponibles pour cette séance.")
        return redirect("membre_planning")

    membre = request.user.membre  # type: ignore[attr-defined]
    couverte_abonnement, paiement_abonnement_actif, _ = _abonnement_couvre_seance(membre, seance)
    statut_initial = Inscription.Statut.VALIDEE if couverte_abonnement else Inscription.Statut.EN_ATTENTE
    try:
        with transaction.atomic():
            Inscription.objects.create(
                membre=membre,
                seance=seance,
                statut=statut_initial,
            )
    except IntegrityError:
        inscription_existante = Inscription.objects.filter(membre=membre, seance=seance).first()
        if inscription_existante and inscription_existante.statut == Inscription.Statut.VALIDEE:
            messages.info(request, "Vous êtes déjà inscrit à cette séance.")
            return redirect("membre_planning")
        if inscription_existante:
            if couverte_abonnement:
                inscription_existante.statut = Inscription.Statut.VALIDEE
                inscription_existante.save(update_fields=["statut"])
                messages.success(request, "Inscription confirmée grâce à votre abonnement actif.")
                return redirect("membre_planning")
            messages.info(request, "Votre inscription est en attente de validation du paiement.")
            return redirect("membre_paiement_nouveau", seance_id=seance.idSeance)
        messages.info(request, "Vous êtes déjà inscrit à cette séance.")
        return redirect("membre_planning")

    if couverte_abonnement:
        messages.success(request, "Inscription confirmée. Votre abonnement couvre cette séance.")
        return redirect("membre_planning")
    if paiement_abonnement_actif:
        messages.info(
            request,
            "Cette séance n'est pas couverte par votre abonnement mensuel (activité externe). Paiement à la séance requis.",
        )
    else:
        messages.success(request, "Pré-inscription enregistrée. Veuillez initier le paiement pour validation.")
    return redirect("membre_paiement_nouveau", seance_id=seance.idSeance)


@_role_required(Utilisateur.Role.MEMBRE)
@require_http_methods(["GET", "POST"])
def membre_paiement_nouveau(request: HttpRequest, seance_id: int) -> HttpResponse:
    seance = get_object_or_404(Seance.objects.select_related("activite"), pk=seance_id)
    if _is_seance_passee(seance):
        messages.error(request, "Cette séance est passée. Le paiement n'est plus accessible.")
        return redirect("membre_planning")
    membre = request.user.membre  # type: ignore[attr-defined]
    couverte_abonnement, paiement_abonnement_actif, date_fin_abonnement = _abonnement_couvre_seance(membre, seance)
    if couverte_abonnement:
        inscription_abonnement = Inscription.objects.filter(membre=membre, seance=seance).first()
        if inscription_abonnement and inscription_abonnement.statut != Inscription.Statut.VALIDEE:
            inscription_abonnement.statut = Inscription.Statut.VALIDEE
            inscription_abonnement.save(update_fields=["statut"])
        messages.info(
            request,
            f"Paiement de séance inutile: abonnement actif jusqu'au {timezone.localtime(date_fin_abonnement).date():%d/%m/%Y}.",
        )
        return redirect("membre_planning")

    # on force l'existence d'une inscription avant paiement
    inscription = Inscription.objects.filter(membre=membre, seance=seance).first()
    if not inscription:
        messages.error(request, "Vous devez d'abord vous inscrire à la séance.")
        return redirect("membre_planning")
    if inscription.statut == Inscription.Statut.VALIDEE:
        messages.info(request, "Cette inscription est déjà validée.")
        return redirect("membre_planning")
    paiement_en_attente = (
        Paiement.objects.filter(inscription=inscription, statut=Paiement.Statut.EN_ATTENTE)
        .order_by("-datePaiement")
        .first()
    )

    if request.method == "POST":
        if paiement_en_attente:
            messages.info(request, "Un paiement est déjà en attente de validation pour cette inscription.")
            return redirect("membre_paiement_nouveau", seance_id=seance.idSeance)
        form = PaiementForm(request.POST)
        if form.is_valid():
            Paiement.objects.create(
                membre=membre,
                inscription=inscription,
                montant=seance.activite.tarifMensuel,
                modePaiement=form.cleaned_data["modePaiement"],
                statut=Paiement.Statut.EN_ATTENTE,
            )
            messages.success(request, "Paiement initié (en attente de validation).")
            return redirect("membre_planning")
    else:
        form = PaiementForm()

    return render(
        request,
        "core/membre_paiement_nouveau.html",
        {"seance": seance, "form": form, "paiement_en_attente": paiement_en_attente},
    )


@_role_required(Utilisateur.Role.COACH)
def coach_planning(request: HttpRequest) -> HttpResponse:
    coach = request.user.coach  # type: ignore[attr-defined]
    _, week_start, week_end = _resolve_week(request.GET.get("week"))
    seances = (
        Seance.objects.select_related("activite")
        .filter(coach=coach)
        .filter(dateSeance__range=(week_start, week_end))
        .order_by("dateSeance", "heureDebut")
    )
    calendar_context = _build_week_calendar(seances, request.GET.get("week"))
    return render(
        request,
        "core/coach_planning.html",
        {"seances": seances, **calendar_context},
    )


@_role_required(Utilisateur.Role.COACH)
def coach_inscrits(request: HttpRequest, seance_id: int) -> HttpResponse:
    coach = request.user.coach  # type: ignore[attr-defined]
    seance = get_object_or_404(
        Seance.objects.select_related("activite").prefetch_related(
            "inscriptions__membre__utilisateur"
        ),
        pk=seance_id,
        coach=coach,
    )
    inscriptions = seance.inscriptions.filter(statut=Inscription.Statut.VALIDEE).order_by("-dateInscription")
    return render(
        request,
        "core/coach_inscrits.html",
        {"seance": seance, "inscriptions": inscriptions},
    )


@_role_required(Utilisateur.Role.ADMIN)
def admin_paiements(request: HttpRequest) -> HttpResponse:
    paiements = (
        Paiement.objects.select_related(
            "membre",
            "membre__utilisateur",
            "inscription",
            "inscription__seance",
            "inscription__seance__activite",
            "abonnement",
        )
        .all()
        .order_by("-datePaiement")
    )
    return render(request, "core/admin_paiements.html", {"paiements": paiements})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["POST"])
def admin_valider_paiement(request: HttpRequest, paiement_id: int) -> HttpResponse:
    paiement = get_object_or_404(Paiement.objects.select_related("inscription"), pk=paiement_id)
    with transaction.atomic():
        paiement.statut = Paiement.Statut.VALIDE
        paiement.save(update_fields=["statut"])
        if paiement.inscription:
            paiement.inscription.statut = Inscription.Statut.VALIDEE
            paiement.inscription.save(update_fields=["statut"])
    messages.success(request, "Paiement validé. Inscription confirmée.")
    return redirect("admin_paiements")


# -------------------
# Admin App: CRUD
# -------------------


@_role_required(Utilisateur.Role.ADMIN)
def admin_activites(request: HttpRequest) -> HttpResponse:
    activites = Activite.objects.all().order_by("libelle")
    return render(request, "core/admin_activites_list.html", {"activites": activites})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_activite_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ActiviteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Activité créée.")
            return redirect("admin_activites")
    else:
        form = ActiviteForm()
    return render(request, "core/admin_activite_form.html", {"form": form, "mode": "create"})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_activite_edit(request: HttpRequest, activite_id: int) -> HttpResponse:
    activite = get_object_or_404(Activite, pk=activite_id)
    if request.method == "POST":
        form = ActiviteForm(request.POST, request.FILES, instance=activite)
        if form.is_valid():
            form.save()
            messages.success(request, "Activité mise à jour.")
            return redirect("admin_activites")
    else:
        form = ActiviteForm(instance=activite)
    return render(
        request,
        "core/admin_activite_form.html",
        {"form": form, "mode": "edit", "activite": activite},
    )


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["POST"])
def admin_activite_delete(request: HttpRequest, activite_id: int) -> HttpResponse:
    activite = get_object_or_404(Activite, pk=activite_id)
    activite.delete()
    messages.success(request, "Activité supprimée.")
    return redirect("admin_activites")


@_role_required(Utilisateur.Role.ADMIN)
def admin_seances(request: HttpRequest) -> HttpResponse:
    seances = (
        Seance.objects.select_related("activite", "coach", "coach__utilisateur")
        .all()
        .order_by("dateSeance", "heureDebut")
    )
    return render(request, "core/admin_seances_list.html", {"seances": seances})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_seance_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SeanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Séance créée.")
            return redirect("admin_seances")
    else:
        form = SeanceForm()
    return render(request, "core/admin_seance_form.html", {"form": form, "mode": "create"})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_seance_edit(request: HttpRequest, seance_id: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=seance_id)
    if request.method == "POST":
        form = SeanceForm(request.POST, instance=seance)
        if form.is_valid():
            form.save()
            messages.success(request, "Séance mise à jour.")
            return redirect("admin_seances")
    else:
        form = SeanceForm(instance=seance)
    return render(
        request,
        "core/admin_seance_form.html",
        {"form": form, "mode": "edit", "seance": seance},
    )


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["POST"])
def admin_seance_delete(request: HttpRequest, seance_id: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=seance_id)
    seance.delete()
    messages.success(request, "Séance supprimée.")
    return redirect("admin_seances")


@_role_required(Utilisateur.Role.ADMIN)
def admin_comptes(request: HttpRequest) -> HttpResponse:
    users = Utilisateur.objects.all().order_by("login")
    return render(request, "core/admin_comptes_list.html", {"users": users})


@_role_required(Utilisateur.Role.ADMIN)
def admin_abonnements(request: HttpRequest) -> HttpResponse:
    abonnements = Abonnement.objects.all().order_by("ordre", "prix", "libelle")
    return render(request, "core/admin_abonnements_list.html", {"abonnements": abonnements})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_abonnement_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AbonnementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Abonnement créé.")
            return redirect("admin_abonnements")
    else:
        form = AbonnementForm()
    return render(request, "core/admin_abonnement_form.html", {"form": form, "mode": "create"})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_abonnement_edit(request: HttpRequest, abonnement_id: int) -> HttpResponse:
    abonnement = get_object_or_404(Abonnement, pk=abonnement_id)
    if request.method == "POST":
        form = AbonnementForm(request.POST, instance=abonnement)
        if form.is_valid():
            form.save()
            messages.success(request, "Abonnement mis à jour.")
            return redirect("admin_abonnements")
    else:
        form = AbonnementForm(instance=abonnement)
    return render(
        request,
        "core/admin_abonnement_form.html",
        {"form": form, "mode": "edit", "abonnement": abonnement},
    )


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["POST"])
def admin_abonnement_delete(request: HttpRequest, abonnement_id: int) -> HttpResponse:
    abonnement = get_object_or_404(Abonnement, pk=abonnement_id)
    abonnement.delete()
    messages.success(request, "Abonnement supprimé.")
    return redirect("admin_abonnements")


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["GET", "POST"])
def admin_compte_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UtilisateurCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compte créé.")
            return redirect("admin_comptes")
    else:
        form = UtilisateurCreateForm()
    return render(request, "core/admin_compte_form.html", {"form": form})


@_role_required(Utilisateur.Role.ADMIN)
@require_http_methods(["POST"])
def admin_compte_delete(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(Utilisateur, pk=user_id)
    if user.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect("admin_comptes")
    user.delete()
    messages.success(request, "Compte supprimé.")
    return redirect("admin_comptes")
