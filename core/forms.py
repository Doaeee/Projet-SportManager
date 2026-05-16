from django import forms

from django.utils import timezone
from django.db import transaction

from .models import Abonnement, Activite, Coach, Membre, Paiement, Seance, Utilisateur


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ["modePaiement"]
        widgets = {
            "modePaiement": forms.Select(attrs={"class": "form-select"}),
        }


class ActiviteForm(forms.ModelForm):
    class Meta:
        model = Activite
        fields = ["libelle", "description", "typeAcces", "tarifMensuel", "image"]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "typeAcces": forms.Select(attrs={"class": "form-select"}),
            "tarifMensuel": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class SeanceForm(forms.ModelForm):
    class Meta:
        model = Seance
        fields = ["activite", "coach", "dateSeance", "heureDebut", "heureFin", "capaciteMax"]
        widgets = {
            "activite": forms.Select(attrs={"class": "form-select"}),
            "coach": forms.Select(attrs={"class": "form-select"}),
            "dateSeance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "heureDebut": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "heureFin": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "capaciteMax": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def clean(self):
        cleaned = super().clean()
        date_seance = cleaned.get("dateSeance")
        if not date_seance:
            self.add_error("dateSeance", "La date de la séance est obligatoire.")
            return cleaned

        # Maintient la compatibilite avec le champ historique "jour".
        jours = [
            Seance.Jour.LUNDI,
            Seance.Jour.MARDI,
            Seance.Jour.MERCREDI,
            Seance.Jour.JEUDI,
            Seance.Jour.VENDREDI,
            Seance.Jour.SAMEDI,
            Seance.Jour.DIMANCHE,
        ]
        cleaned["jour"] = jours[date_seance.weekday()]
        return cleaned

    def save(self, commit=True):
        instance: Seance = super().save(commit=False)
        instance.jour = self.cleaned_data["jour"]
        if commit:
            instance.save()
        return instance


class AbonnementForm(forms.ModelForm):
    class Meta:
        model = Abonnement
        fields = ["libelle", "periodicite", "prix", "description", "avantages", "actif", "ordre"]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "periodicite": forms.Select(attrs={"class": "form-select"}),
            "prix": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "avantages": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Acces 6h-23h\nCours collectifs"}
            ),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ordre": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class UtilisateurCreateForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Mot de passe")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Confirmer")

    # champs profil (selon rôle)
    numMembre = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    dateNaissance = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    dateAdhesion = forms.DateField(
        required=False,
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    numCoach = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    specialite = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = Utilisateur
        fields = ["login", "email", "role"]
        widgets = {
            "login": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Les mots de passe ne correspondent pas.")

        role = cleaned.get("role")
        if role == Utilisateur.Role.MEMBRE:
            if not cleaned.get("numMembre"):
                self.add_error("numMembre", "Obligatoire pour un membre.")
            if not cleaned.get("dateNaissance"):
                self.add_error("dateNaissance", "Obligatoire pour un membre.")
        if role == Utilisateur.Role.COACH:
            if not cleaned.get("numCoach"):
                self.add_error("numCoach", "Obligatoire pour un coach.")
            if not cleaned.get("specialite"):
                self.add_error("specialite", "Obligatoire pour un coach.")
        return cleaned

    def save(self, commit=True):
        user: Utilisateur = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if self.cleaned_data["role"] == Utilisateur.Role.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
            role = self.cleaned_data["role"]
            if role == Utilisateur.Role.MEMBRE:
                Membre.objects.create(
                    utilisateur=user,
                    numMembre=self.cleaned_data["numMembre"],
                    dateNaissance=self.cleaned_data["dateNaissance"],
                    dateAdhesion=self.cleaned_data.get("dateAdhesion") or timezone.now().date(),
                )
            elif role == Utilisateur.Role.COACH:
                Coach.objects.create(
                    utilisateur=user,
                    numCoach=self.cleaned_data["numCoach"],
                    specialite=self.cleaned_data["specialite"],
                )
        return user


class PublicMembreSignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Mot de passe")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Confirmer le mot de passe")
    dateNaissance = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))

    class Meta:
        model = Utilisateur
        fields = ["login", "email"]
        widgets = {
            "login": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        return cleaned

    def _generate_num_membre(self) -> str:
        base = timezone.now().strftime("MBR%Y%m%d%H%M%S")
        numero = base
        suffix = 1
        while Membre.objects.filter(numMembre=numero).exists():
            numero = f"{base}{suffix}"
            suffix += 1
        return numero

    def save(self, commit=True):
        with transaction.atomic():
            user: Utilisateur = super().save(commit=False)
            user.role = Utilisateur.Role.MEMBRE
            user.set_password(self.cleaned_data["password1"])
            if commit:
                user.save()
                Membre.objects.create(
                    utilisateur=user,
                    numMembre=self._generate_num_membre(),
                    dateNaissance=self.cleaned_data["dateNaissance"],
                    dateAdhesion=timezone.now().date(),
                )
        return user
