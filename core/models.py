from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class UtilisateurManager(UserManager):
    def create_user(self, login: str, email: str | None = None, password=None, **extra_fields):
        if not login:
            raise ValueError("Le champ login est obligatoire.")
        extra_fields.setdefault("username", login)  # compat AbstractUser
        if email:
            email = self.normalize_email(email)
        user = self.model(login=login, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login: str, email: str | None = None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Utilisateur.Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(login=login, email=email, password=password, **extra_fields)


class Utilisateur(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        COACH = "COACH", "Coach"
        MEMBRE = "MEMBRE", "Membre"

    # On garde AbstractUser mais on authentifie via ce champ "login"
    # (username reste présent mais optionnel)
    username = models.CharField(max_length=150, blank=True, null=True)
    login = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBRE)

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS = ["email"]
    objects = UtilisateurManager()

    def __str__(self) -> str:
        return f"{self.login} ({self.get_role_display()})"


class Membre(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membre"
    )
    numMembre = models.CharField(max_length=30, unique=True)
    dateNaissance = models.DateField()
    dateAdhesion = models.DateField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.numMembre} - {self.utilisateur.login}"


class Coach(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coach"
    )
    numCoach = models.CharField(max_length=30, unique=True)
    specialite = models.CharField(max_length=120)

    def __str__(self) -> str:
        return f"{self.numCoach} - {self.utilisateur.login}"


class Activite(models.Model):
    class TypeAcces(models.TextChoices):
        INTERNE = "INTERNE", "Interne"
        EXTERNE = "EXTERNE", "Externe"

    EXTERNAL_ACTIVITY_KEYWORDS = ("tennis", "basket", "football", "foot")

    idActivite = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    tarifMensuel = models.DecimalField(max_digits=8, decimal_places=2)
    typeAcces = models.CharField(max_length=10, choices=TypeAcces.choices, default=TypeAcces.INTERNE)
    image = models.ImageField(upload_to="activites/", blank=True, null=True)

    def _is_always_external_activity(self) -> bool:
        libelle = (self.libelle or "").strip().lower()
        return any(keyword in libelle for keyword in self.EXTERNAL_ACTIVITY_KEYWORDS)

    def save(self, *args, **kwargs):
        if self._is_always_external_activity():
            self.typeAcces = self.TypeAcces.EXTERNE
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.libelle


class Abonnement(models.Model):
    class Periodicite(models.TextChoices):
        MENSUEL = "MENSUEL", "Mensuel"
        ANNUEL = "ANNUEL", "Annuel"

    libelle = models.CharField(max_length=120)
    periodicite = models.CharField(max_length=10, choices=Periodicite.choices, default=Periodicite.MENSUEL)
    prix = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    avantages = models.TextField(blank=True, help_text="Un avantage par ligne")
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "prix", "libelle"]

    def __str__(self) -> str:
        return f"{self.libelle} - {self.prix} DHS/{self.get_periodicite_display().lower()}"

    @property
    def avantages_liste(self):
        return [ligne.strip() for ligne in self.avantages.splitlines() if ligne.strip()]


class Seance(models.Model):
    class Jour(models.TextChoices):
        LUNDI = "LUNDI", "Lundi"
        MARDI = "MARDI", "Mardi"
        MERCREDI = "MERCREDI", "Mercredi"
        JEUDI = "JEUDI", "Jeudi"
        VENDREDI = "VENDREDI", "Vendredi"
        SAMEDI = "SAMEDI", "Samedi"
        DIMANCHE = "DIMANCHE", "Dimanche"

    idSeance = models.AutoField(primary_key=True)
    dateSeance = models.DateField(blank=True, null=True)
    jour = models.CharField(max_length=10, choices=Jour.choices)
    heureDebut = models.TimeField()
    heureFin = models.TimeField()
    capaciteMax = models.PositiveIntegerField()

    activite = models.ForeignKey(Activite, on_delete=models.CASCADE, related_name="seances")
    coach = models.ForeignKey(Coach, on_delete=models.PROTECT, related_name="seances")

    def __str__(self) -> str:
        if self.dateSeance:
            return f"{self.activite.libelle} - {self.dateSeance} {self.heureDebut}-{self.heureFin}"
        return f"{self.activite.libelle} - {self.jour} {self.heureDebut}-{self.heureFin}"

    @property
    def places_restantes(self) -> int:
        inscrits = self.inscriptions.filter(statut=Inscription.Statut.VALIDEE).count()
        return max(self.capaciteMax - inscrits, 0)

    @property
    def inscriptions_valides_count(self) -> int:
        return self.inscriptions.filter(statut=Inscription.Statut.VALIDEE).count()


class Inscription(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente paiement"
        VALIDEE = "VALIDEE", "Validée"

    idInscription = models.AutoField(primary_key=True)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name="inscriptions")
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, related_name="inscriptions")
    dateInscription = models.DateTimeField(default=timezone.now)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membre", "seance"], name="uniq_membre_seance")
        ]

    def __str__(self) -> str:
        return f"{self.membre.numMembre} -> {self.seance}"


class Paiement(models.Model):
    class ModePaiement(models.TextChoices):
        ESPECES = "ESPECES", "Espèces"
        CARTE = "CARTE", "Carte"
        VIREMENT = "VIREMENT", "Virement"

    class Statut(models.TextChoices):
        VALIDE = "VALIDE", "Validé"
        EN_ATTENTE = "EN_ATTENTE", "En attente"

    idPaiment = models.AutoField(primary_key=True)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name="paiements")
    inscription = models.ForeignKey(
        Inscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="paiements"
    )
    abonnement = models.ForeignKey(
        Abonnement, on_delete=models.SET_NULL, null=True, blank=True, related_name="paiements"
    )
    montant = models.DecimalField(max_digits=8, decimal_places=2)
    datePaiement = models.DateTimeField(default=timezone.now)
    modePaiement = models.CharField(max_length=20, choices=ModePaiement.choices)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)

    def __str__(self) -> str:
        return f"{self.membre.numMembre} - {self.montant} ({self.get_statut_display()})"
