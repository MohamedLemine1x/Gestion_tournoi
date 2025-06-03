from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from organisateurs.utils.decorators import organisateur_required
from organisateurs.forms import TournoiForm
from tournois.models import Tournoi
import logging

logger = logging.getLogger(__name__)

@login_required
@organisateur_required
def tournoi_create(request):
    """
    Vue pour créer un nouveau tournoi.
    """
    try:
        logger.info("=== Début de la vue tournoi_create ===")
        logger.info(f"Méthode HTTP: {request.method}")
        logger.info(f"Utilisateur: {request.user}")
        logger.info(f"Est authentifié: {request.user.is_authenticated}")
        logger.info(f"Est organisateur: {hasattr(request.user, 'organisateur')}")
        logger.info(f"Session: {request.session.session_key}")
        logger.info(f"Headers: {request.headers}")

        if request.method == 'POST':
            logger.info("Traitement d'une requête POST")
            form = TournoiForm(request.POST)
            logger.info(f"Données du formulaire: {request.POST}")
            if form.is_valid():
                logger.info("Formulaire valide")
                tournoi = form.save(commit=False)
                tournoi.organisateur = request.user.organisateur
                tournoi.save()
                logger.info(f"Tournoi créé: {tournoi}")
                messages.success(request, _("Le tournoi a été créé avec succès."))
                return redirect('organisateurs:tournoi_detail', pk=tournoi.pk)
            else:
                logger.warning(f"Formulaire invalide: {form.errors}")
        else:
            logger.info("Affichage du formulaire vide")
            form = TournoiForm()

        logger.info("=== Fin de la vue tournoi_create ===")
        return render(request, 'organisateurs/tournoi_form.html', {
            'form': form,
            'action': _("Créer")
        })

    except Exception as e:
        logger.error(f"Erreur lors de la création du tournoi: {str(e)}", exc_info=True)
        messages.error(request, _("Une erreur est survenue lors de la création du tournoi."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def tournoi_edit(request, pk):
    """
    Vue pour modifier un tournoi existant.
    """
    try:
        tournoi = get_object_or_404(Tournoi, pk=pk, organisateur=request.user.organisateur)
        
        if request.method == 'POST':
            form = TournoiForm(request.POST, instance=tournoi)
            if form.is_valid():
                form.save()
                logger.info(f"Tournoi modifié: {tournoi}")
                messages.success(request, _("Le tournoi a été modifié avec succès."))
                return redirect('organisateurs:tournoi_detail', pk=tournoi.pk)
        else:
            form = TournoiForm(instance=tournoi)

        return render(request, 'organisateurs/tournoi_form.html', {
            'form': form,
            'tournoi': tournoi,
            'action': _("Modifier")
        })

    except Exception as e:
        logger.error(f"Erreur lors de la modification du tournoi: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de la modification du tournoi."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def tournoi_detail(request, pk):
    """
    Vue pour afficher les détails d'un tournoi.
    """
    try:
        tournoi = get_object_or_404(Tournoi, pk=pk, organisateur=request.user.organisateur)
        matchs = tournoi.matchs.all().order_by('date_match')
        equipes = tournoi.equipes.all()

        context = {
            'tournoi': tournoi,
            'matchs': matchs,
            'equipes': equipes,
        }
        return render(request, 'organisateurs/tournoi_detail.html', context)

    except Exception as e:
        logger.error(f"Erreur lors de l'affichage du tournoi: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de l'affichage du tournoi."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def tournoi_delete(request, pk):
    """
    Vue pour supprimer un tournoi.
    """
    try:
        tournoi = get_object_or_404(Tournoi, pk=pk, organisateur=request.user.organisateur)
        
        if request.method == 'POST':
            nom_tournoi = tournoi.nom
            tournoi.delete()
            logger.info(f"Tournoi supprimé: {nom_tournoi}")
            messages.success(request, _("Le tournoi a été supprimé avec succès."))
            return redirect('organisateurs:dashboard')

        return render(request, 'organisateurs/tournoi_confirm_delete.html', {
            'tournoi': tournoi
        })

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du tournoi: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de la suppression du tournoi."))
        return redirect('organisateurs:dashboard') 